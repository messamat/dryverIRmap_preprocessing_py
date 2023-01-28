#Import libraries
import arcpy
import numpy as np
import pandas as pd
import time

from utility_functions_py3 import *
from arcpy.sa import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

#Define paths
#Folder structure
rootdir = get_root_fromsrcdir()
datdir = os.path.join(rootdir, 'data')
resdir = os.path.join(rootdir, 'results')
statpredgdb = os.path.join(resdir, 'DryverIRmodel_static_predictors_forMahdi_20221122', 'static_predictors.gdb')

process_gdb = os.path.join(resdir, 'extend_HydroRIVERS_process.gdb')
dryver_netpourpoints_ras = os.path.join(process_gdb, 'net_dryver_upao2_dis003_pourpoints_ras')
dryver_netline = os.path.join(process_gdb, 'net_dryver_upao2_dis003')
dryver_netpourpoints = os.path.join(process_gdb, 'net_dryver_upao2_dis003_pourpoints')

#Input variable rasters
gai3gdb = os.path.join(resdir, 'gai3_uav.gdb')

#Create gdb for static predictors
dryver_predvargdb = os.path.join(resdir, 'net_dryver_predvars.gdb')
pathcheckcreate(path=dryver_predvargdb, verbose=True)

products_gdb = os.path.join(resdir, 'extend_HydroRIVERS_products.gdb')
pathcheckcreate(path=products_gdb, verbose=True)

#Set environment
arcpy.env.extent = arcpy.env.snapRaster = dryver_netpourpoints_ras

#Compute groundwater depth in stream catchment

#Compute snow extent in whole catchment

#Export table of reach IDs
if 'DRYVER_RIVID' not in [f.name for f in arcpy.ListFields(dryver_netline)]:
    arcpy.management.AlterField(dryver_netline, 'grid_code', 'DRYVER_RIVID')

attri_tab = os.path.join(products_gdb, 'net_dryver_staticpredictors')
if not arcpy.Exists(attri_tab):
    arcpy.management.CopyRows(dryver_netline, attri_tab)
    arcpy.management.DeleteField(attri_tab,
                                 [f.name for f in arcpy.ListFields(attri_tab)
                                  if f.name not in [arcpy.Describe(attri_tab).OIDFieldName,
                                               'DRYVER_RIVID']
                                 ])

#Insert into a single table
field_dict = {
    'ai3_01_uav': 'ai_ix_01',
    'ai3_02_uav': 'ai_ix_02',
    'ai3_03_uav': 'ai_ix_03',
    'ai3_04_uav': 'ai_ix_04',
    'ai3_05_uav': 'ai_ix_05',
    'ai3_06_uav': 'ai_ix_06',
    'ai3_07_uav': 'ai_ix_07',
    'ai3_08_uav': 'ai_ix_08',
    'ai3_09_uav': 'ai_ix_09',
    'ai3_10_uav': 'ai_ix_10',
    'ai3_11_uav': 'ai_ix_11',
    'ai3_12_uav': 'ai_ix_12',
    'up_area_skm_15s': 'UPLAND_SKM',
    'pnv_cl_umj': 'pnv_cl_umj',
    'glc_cl_umj': 'glc_cl_umj',
    'eenv90_slope_deg_x100_uav': 'slp_dg_uav',
    'glims_glacier_ext_pc_acc': 'gla_pc_use',
    'hylak_all_area_pc_x100_acc': 'lka_pc_use',
    'permafrost_ext_pc_x100_use': 'prm_pc_use'
}

#Extract values
statspred_paths = getfilelist(statpredgdb) + getfilelist(gai3gdb)

start = time.time()
for ras in statspred_paths[3:6]:
    if os.path.basename(ras) in field_dict:
        out_field = field_dict[os.path.basename(ras)]
        if out_field not in [f.name for f in arcpy.ListFields(attri_tab)]:
            out_tab = os.path.join(dryver_predvargdb, os.path.basename(ras))

            if not arcpy.Exists(out_tab):
                print(f'Processing zonal statistics for {ras}')
                ZonalStatisticsAsTable(in_zone_data=dryver_netpourpoints_ras,
                                       zone_field='Value',
                                       in_value_raster=ras,
                                       out_table=out_tab,
                                       statistics_type='SUM')

            #Tried join field. Stopped after >2h for a single field
            arcpy.management.AddField(in_table = attri_tab,
                                      field_name = out_field,
                                      field_type = 'LONG')
            val_dict = {row[0] : row[1] for row in arcpy.da.SearchCursor(out_tab, ['VALUE', 'SUM'])}
            print('Writing in attri_tab')
            with arcpy.da.UpdateCursor(attri_tab, ['DRYVER_RIVID', out_field]) as cursor:
                for row in cursor:
                    row[1] = val_dict[row[0]]
                    cursor.updateRow(row)
end = time.time()
print(end-start)


#Try extract to points
start = time.time()
ExtractMultiValuesToPoints(in_point_features = dryver_netpourpoints,
                           in_rasters = statspred_paths,
                           bilinear_interpolate_values = 'NONE')
end = time.time()
print(end-start)


        # JoinField(in_data=attri_tab,
        #                        in_field = 'DRYVER_RIVID',
        #                        join_table= test_tab,
        #                        join_field = 'VALUE',
        #                        fields = ['SUM']
        #                        )
    #arcpy.management.AlterField(attri_tab, 'SUM', out_field)




