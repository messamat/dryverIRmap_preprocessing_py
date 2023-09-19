import arcpy.management

from utility_functions_py3 import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True
arcpy.env.qualifiedFieldNames = False
overwrite_all = False

#Define paths
#Folder structure
rootdir = get_root_fromsrcdir()
datdir = os.path.join(rootdir, 'data')
resdir = os.path.join(rootdir, 'results')

raw_net_gdb = os.path.join(resdir, 'DRYVERnet.gdb')
process_gdb = os.path.join(resdir, 'extend_HydroRIVERS_process.gdb')

#Input
dryver_netline = os.path.join(raw_net_gdb, 'dryvernet')
dryver_link_ras = os.path.join(raw_net_gdb, 'dryvernet_link_ras')

hydrorivers = os.path.join(datdir, 'HydroATLAS', 'HydroRIVERS_v10_final_data', 'geodatabases',
                           'HydroRIVERS_v10.gdb', 'HydroRIVERS_v10')

globalIRmap_onde_gdb = os.path.join(os.path.split(rootdir)[0], 'globalIRmap', 'results', 'Insitu_databases', 'ondeeau.gdb')

#Outputs
hydrorivers_ras = os.path.join(process_gdb, 'hyriv_id_ras')
hyriv_dryver_match = os.path.join(process_gdb, 'hyriv_dryver_match')

onde_processing_gdb = os.path.join(resdir, 'onde_process.gdb')
onde_nodupli = os.path.join(onde_processing_gdb, 'obsnodupli')
onde_inihyriv = os.path.join(onde_processing_gdb, 'obs_finalwgs') #Layer that was used in Messger et al. 2021 for comparison
onde_inidryriv = os.path.join(onde_processing_gdb, 'obs_finalwgs_dryriv')
onde_nothyriv = os.path.join(onde_processing_gdb, 'obsnodupli_nothyriv')
onde_editdryriv = os.path.join(onde_processing_gdb, 'obsnodupli_nothyriv_editfordryriv')
onde_cleandryriv = os.path.join(onde_processing_gdb, 'obsnodupli_nothyriv_cleanfordryriv')
onde_cleandryriv_spatialjoin = os.path.join(onde_processing_gdb, 'obsnodupli_nothyriv_cleanfordryriv_spatialjoin')
onde_dryriv_merge = os.path.join(onde_processing_gdb, 'obs_dryriv_merge')
onde_dryriv_merge_wgs84 = os.path.join(onde_processing_gdb, 'obs_dryriv_merge_wgs84')
onde_dryriv_tab = os.path.join(resdir, 'onde_dryvernet_jointab.csv')

#Convert HYdroRIVERS_v10 to raster with same specs as dryvernet
if not arcpy.Exists(hydrorivers_ras) or overwrite_all:
    arcpy.env.extent = arcpy.env.snapRaster = dryver_link_ras
    arcpy.PolylineToRaster_conversion(in_features=hydrorivers,
                                      value_field="HYRIV_ID",
                                      out_rasterdataset=hydrorivers_ras,
                                      cellsize =dryver_link_ras
                                      )

#Zonal statistics with DRYVER_NET links
if not arcpy.Exists(hyriv_dryver_match) or overwrite_all:
    ZonalStatisticsAsTable(in_zone_data=dryver_link_ras,
                           zone_field='Value',
                           in_value_raster=hydrorivers_ras,
                           out_table=hyriv_dryver_match,
                           statistics_type='MAJORITY')

#Get raw and formatted ONDE data from Messager et al. 2021
if not arcpy.Exists(onde_processing_gdb) or overwrite_all:
    arcpy.CreateFileGDB_management(os.path.split(onde_processing_gdb)[0], os.path.split(onde_processing_gdb)[1])

for lyr in ['obsraw', 'obsnodupli', 'obs_finalwgs']:
    existing_onde_lyrs = getfilelist(onde_processing_gdb)
    if not lyr in existing_onde_lyrs or overwrite_all:
        print('Transferring {}'.format(lyr))
        arcpy.CopyFeatures_management(os.path.join(globalIRmap_onde_gdb, lyr),
                                      os.path.join(onde_processing_gdb, lyr)
                                      )

#Get DRYVER_RIV for these already
if not arcpy.Exists(onde_inidryriv) or overwrite_all:
    arcpy.management.MakeFeatureLayer(onde_inihyriv, 'onde_inihyriv')
    arcpy.AddJoin_management('onde_inihyriv', in_field='HYRIV_IDjoinedit',
                             join_table=hyriv_dryver_match, join_field='MAJORITY',
                             join_type='KEEP_COMMON')
    arcpy.CopyFeatures_management('onde_inihyriv', onde_inidryriv)

arcpy.management.AlterField(onde_inidryriv, 'obs_finalwgs_F_CdSiteHydro_',
                            'F_CdSiteHydro_', 'F_CdSiteHydro_')
arcpy.management.AlterField(onde_inidryriv, 'obs_finalwgs_F_CdSiteHydro__X',
                            'F_CdSiteHydro_X', 'F_CdSiteHydro_X')
arcpy.management.AlterField(onde_inidryriv, 'obs_finalwgs_F_CdSiteHydro__Y',
                            'F_CdSiteHydro_Y', 'F_CdSiteHydro_Y')
arcpy.management.AlterField(onde_inidryriv, 'hyriv_dryver_match_MAJORITY',
                            'DRYVER_RIVID', 'DRYVER_RIVID')


#Check other ONDE sites not already snapped to HydroRIVERS
snapped_ids = [row[0] for row in arcpy.da.SearchCursor(onde_inidryriv, ['F_CdSiteHydro_'])]

if not arcpy.Exists(onde_nothyriv) or overwrite_all:
    arcpy.management.CopyFeatures(onde_nodupli, onde_nothyriv)
    with arcpy.da.UpdateCursor(onde_nothyriv, 'F_CdSiteHydro_') as cursor:
        for row in cursor:
            if row[0] in snapped_ids:
                cursor.deleteRow()

if not arcpy.Exists(onde_editdryriv) or overwrite_all:
    arcpy.management.CopyFeatures(onde_nothyriv, onde_editdryriv)
    if not 'mathis_snap' in [f.name for f in arcpy.ListFields(onde_editdryriv)]:
        arcpy.management.AddField(onde_editdryriv,
                                  'mathis_snap',
                                  'SHORT')
###############EDIT MANUALLY################
if not arcpy.Exists(onde_cleandryriv) or overwrite_all:
    arcpy.management.CopyFeatures(onde_editdryriv, onde_cleandryriv)

    #Snap to river network
    snapenv = [[dryver_netline, 'EDGE', '1000 meters']]
    arcpy.edit.Snap(in_features=onde_cleandryriv, snap_environment=snapenv)

    #Remove sites for which no nearby river line in DRYVER network matches
    with arcpy.da.UpdateCursor(onde_cleandryriv, 'mathis_snap') as cursor:
        for row in cursor:
            if row[0] == -1:
                cursor.deleteRow()

if not arcpy.Exists(onde_cleandryriv_spatialjoin) or overwrite_all:
    join = arcpy.management.AddSpatialJoin(
        target_features=onde_cleandryriv,
        join_features = dryver_netline,
        join_operation= "JOIN_ONE_TO_ONE",
        match_option="CLOSEST"
    )
    arcpy.management.CopyFeatures(join, onde_cleandryriv_spatialjoin)

#Merge old and new ONDE stations
if not arcpy.Exists(onde_dryriv_merge) or overwrite_all:
    arcpy.management.Merge(inputs=[onde_cleandryriv_spatialjoin,
                                   onde_inidryriv],
                           output=onde_dryriv_merge)

    arcpy.Project_management(onde_dryriv_merge,
                             onde_dryriv_merge_wgs84,
                             out_coor_system=dryver_netline)

    arcpy.management.AddGeometryAttributes(onde_dryriv_merge_wgs84,
                                           Geometry_Properties="POINT_X_Y_Z_M")

    arcpy.management.AlterField(onde_dryriv_merge_wgs84, 'POINT_X',
                                'dryriv_lon', 'dryriv_lon')
    arcpy.management.AlterField(onde_dryriv_merge_wgs84, 'POINT_Y',
                                'dryriv_lat', 'dryriv_lat')

    arcpy.management.DeleteField(
        onde_dryriv_merge_wgs84,
        drop_field=[f.name for f in arcpy.ListFields(onde_dryriv_merge_wgs84) if f.name not in
                    ["F_CdSiteHydro_", "DRYVER_RIVID", "OBJECTID", "Shape", "dryriv_lon", "dryriv_lat"]])

if not arcpy.Exists(onde_dryriv_tab) or overwrite_all:
    arcpy.management.CopyRows(onde_dryriv_merge_wgs84,
                              onde_dryriv_tab)