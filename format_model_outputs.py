import arcpy.management
from collections import defaultdict
from utility_functions_py3 import *

arcpy.CheckOutExtension('Spatial')

#Inputs
eu_net_dir = os.path.join(resdir, 'eu_nets')

eu_net = os.path.join(eu_net_dir, '01_dryver_net_eu.shp')
modres_csv = os.path.join(eu_net_dir, 'output_eu_rivers.csv')

#Hydrobasins level 3
hybas3 = os.path.join(datdir, 'hybas_lake_eu_lev01-12_v1c', 'hybas_lake_eu_lev03_v1c.shp')

#Outputs
eu_net_gdb = os.path.join(eu_net_dir, 'dryver_net_eu.gdb')
eu_net_ingdb = os.path.join(eu_net_gdb, 'dryver_net_eu')
eu_net_modjoin = os.path.join(eu_net_gdb, 'dryver_net_eu_irclass')
eu_net_modjoin_gpkg = os.path.join(eu_net_dir, 'dryver_net_eu_irclass.gpkg')

eu_net_bas_gdb = os.path.join(eu_net_dir, 'dryver_net_eu_bybas.gdb')

eu_net_drn_gdb = os.path.join(eu_net_dir, 'dryver_net_drns.gdb')
eu_net_drnpts = os.path.join(eu_net_drn_gdb, 'dryver_net_drns_prpoints')

#Export as shp for hydrobasins level 3
if not arcpy.Exists(eu_net_ingdb):
    arcpy.analysis.SpatialJoin(eu_net, hybas3, eu_net_ingdb)

#------------------- Join network to model outputs and export to file geodatabase ---------------------------------------
if not arcpy.Exists(eu_net_gdb):
    arcpy.management.CreateFileGDB(os.path.split(eu_net_gdb)[0],
                                   os.path.split(eu_net_gdb)[1])

if not arcpy.Exists(eu_net_modjoin):
    arcpy.management.MakeFeatureLayer(eu_net_ingdb, 'eu_net_lyr')
    arcpy.management.AddJoin(in_layer_or_view='eu_net_lyr',
                             in_field='DRYVER_RIV',
                             join_table=modres_csv,
                             join_field='DRYVER_RIV')
    arcpy.management.CopyFeatures('eu_net_lyr',
                                  eu_net_modjoin)
    arcpy.management.Delete(eu_net_ingdb)

if not arcpy.Exists(eu_net_modjoin_gpkg):
    arcpy.management.CreateSQLiteDatabase(out_database_name=eu_net_modjoin_gpkg,
                                          spatial_type='GEOPACKAGE')
    arcpy.management.Copy(eu_net_modjoin,
                          os.path.join(eu_net_modjoin_gpkg, os.path.splitext(os.path.split(eu_net_modjoin_gpkg)[1])[0]
                                       )
                          )

#Takes too long to use joinfield
# fast_joinfield(in_data=eu_net_ingdb,
#                in_field='DRYVER_RIV',
#                join_table=modres_csv,
#                join_field='DRYVER_RIV',
#                fields=[[f.name, f.name] for f in arcpy.ListFields(modres_csv) if f.name != 'DRYVER_RIV'],
#                round=True)

#------------------- Export by basins ----------------------------------------------------------------------------------
if not arcpy.Exists(eu_net_bas_gdb):
    arcpy.management.CreateFileGDB(os.path.split(eu_net_bas_gdb)[0],
                                   os.path.split(eu_net_bas_gdb)[1])
arcpy.analysis.SplitByAttributes(Input_Table=eu_net_modjoin,
                                 Target_Workspace=eu_net_bas_gdb,
                                 Split_Fields=['PFAF_ID'])
#Rename layers
baslist = {lyr: re.sub('T', 'eu_net_irclass_bas', lyr) for lyr in
           getfilelist(eu_net_bas_gdb, repattern="T[0-9]{3}")}
for bas in baslist:
    arcpy.management.Rename(in_data=bas,
                            out_data=baslist[bas])

#Export to shapefiles
eu_net_bas_dir = os.path.splitext(eu_net_bas_gdb)[0]
if not os.path.exists(eu_net_bas_dir):
    os.mkdir(eu_net_bas_dir)
for lyr in getfilelist(eu_net_bas_gdb):
    out_lyr = f'{os.path.split(lyr)[1]}.shp'
    out_path = os.path.join(eu_net_bas_dir, out_lyr)
    if not arcpy.Exists(out_path):
        print(f"Copying {f'{out_lyr}'}...")
        arcpy.management.CopyFeatures(lyr, out_path)

#------------------- Export for DRNs -----------------------------------------------------------------------------------
if not arcpy.Exists(eu_net_drn_gdb):
    arcpy.management.CreateFileGDB(os.path.split(eu_net_drn_gdb)[0],
                                   os.path.split(eu_net_drn_gdb)[1])

#Create starting points to trace upstream - NAME: DRYVER_RIV, to_node
DRN_DRYVER_RIVdict = {'Vantaanjoki': [1329901, 2579023],
                      'Morava': [5135971, 5082714],
                      'Krka': [5310519, 6390481],
                      'Guadiaro': [5106459,	8162297],
                      'Fekete_viz': [5252426, 5912663],
                      'Ain': [4922854, 5885532]}

#Trace upstream
up_down_dict = {row[0]: row[1] for row in arcpy.da.SearchCursor(eu_net_modjoin, ['from_node', 'to_node'])}
down_up_dict = defaultdict(set)
for key, value in up_down_dict.items():
    down_up_dict[value].add(key)

#Select and export
DRN_DRYVER_trace = defaultdict(set)
for drn in DRN_DRYVER_RIVdict:
    out_drn = os.path.join(eu_net_drn_gdb,
                           f'dryver_net_{drn}_irclass')
    if not arcpy.Exists(out_drn):
        print(f"Trace upstream for {drn}...")
        DRN_DRYVER_trace[drn].add(DRN_DRYVER_RIVdict[drn][1])
        last_to_node = {DRN_DRYVER_RIVdict[drn][1]}
        while len(last_to_node) > 0:
            #print(len(last_to_node))
            from_to_nodes = set()
            for to_node in last_to_node:
                from_to_nodes.update(down_up_dict[to_node])
            DRN_DRYVER_trace[drn].update(from_to_nodes)
            last_to_node = from_to_nodes

        print(f'Selecting and exporting DRN for {drn}...')
        arcpy.management.MakeFeatureLayer(
            eu_net_modjoin, 'eu_net_drn_lyr',
            where_clause = f'"from_node" IN ({", ".join([str(v) for v in DRN_DRYVER_trace[drn]])})')
        arcpy.management.CopyFeatures('eu_net_drn_lyr', out_drn)
        arcpy.management.Delete('eu_net_drn_lyr')
    else:
        print(f"Subset network for {drn} already exists. skipping...")

#Export to shapefiles
eu_net_drn_dir = os.path.splitext(eu_net_drn_gdb)[0]
if not os.path.exists(eu_net_drn_dir):
    os.mkdir(eu_net_drn_dir)
for lyr in getfilelist(eu_net_drn_gdb):
    out_lyr = f'{os.path.split(lyr)[1]}.shp'
    out_path = os.path.join(eu_net_drn_dir, out_lyr)
    if not arcpy.Exists(out_path):
        print(f"Copying {f'{out_lyr}'}...")
        arcpy.management.CopyFeatures(lyr, out_path)
