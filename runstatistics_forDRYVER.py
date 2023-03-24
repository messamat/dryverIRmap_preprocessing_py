#Import libraries
import os.path

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
statpredgdb = os.path.join(resdir, 'DryverIRmodel_static_predictors_forMahdi_20221122', 'static_predictors.gdb')


LRpred_resdir = os.path.join(resdir, 'LRpredictors')
LRpred_runoffvar_gdb = os.path.join(LRpred_resdir, 'runoff_daily_var.gdb')
LRpred_gwtorunoff_gdb = os.path.join(LRpred_resdir, 'qrdif_ql_ratio_mon_1981to2019.gdb')
LRpred_prec_wetdays_gdb = os.path.join(LRpred_resdir, 'Prec_wetdays_1981_2019.gdb')

process_gdb = os.path.join(resdir, 'extend_HydroRIVERS_process.gdb')
dryver_netline = os.path.join(process_gdb, 'net_dryver_upao2_dis003')
dryver_netpourpoints = os.path.join(process_gdb, 'net_dryver_upao2_dis003_pourpoints')
dryver_netpourpoints_ras = os.path.join(process_gdb, 'net_dryver_upao2_dis003_pourpoints_ras')
dryver_netcatchments = os.path.join(process_gdb, 'net_dryver_upao2_dis003_catchments')

#Input variable rasters
gai3gdb = os.path.join(resdir, 'gai3_uav.gdb')


#Create gdb for WaterGAP time-series predictors
LRpred_tabgdb = os.path.join(resdir, 'LRpredtabs.gdb')
pathcheckcreate(path=LRpred_tabgdb, verbose=True)

#Create gdb for static predictors
dryver_predvargdb = os.path.join(resdir, 'net_dryver_predvars_zonalstats.gdb')
pathcheckcreate(path=dryver_predvargdb, verbose=True)

products_gdb = os.path.join(resdir, 'DRYVERnet.gdb')
pathcheckcreate(path=products_gdb, verbose=True)

#Output paths
attri_tab = os.path.join(products_gdb, 'dryvernet_attri_tab')
dryver_netpourpoints_sub = os.path.join(process_gdb, 'net_dryver_upao2_dis003_pourpoints_sub')

#Set environment
arcpy.env.extent = arcpy.env.snapRaster = dryver_netpourpoints_ras

#~~~~~~~~~~~~~~~~~ Extract low resolution predictors time series ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#Subset pourpoints
ruv_list = getfilelist(LRpred_runoffvar_gdb)

if not arcpy.Exists(dryver_netpourpoints_sub):
    arcpy.analysis.Clip(in_features=dryver_netpourpoints,
                        clip_features=arcpy.Describe(ruv_list[0]).extent.polygon,
                        out_feature_class=dryver_netpourpoints_sub)

def extract_rename(in_rasters, in_location_data, out_table, id_field, fieldroot):
    Sample(in_rasters=in_rasters, in_location_data=in_location_data, out_table=out_table,
           resampling_type='NEAREST', unique_id_field=id_field, layout='COLUMN_WISE', generate_feature_class='TABLE')

    arcpy.management.AlterField(out_table, field=os.path.split(in_location_data)[1],
                                new_field_name=id_field, new_field_alias=id_field)

    for f in arcpy.ListFields(out_table):
        rootvar = re.sub("[0-9]+$", "", os.path.split(ruv_list[0])[1])
        if re.match(rootvar, f.name):
            nfield = re.sub(
                rootvar,
                fieldroot,
                re.sub("_Band_1", "", f.name)
            )
            arcpy.management.AlterField(out_table,
                                        field=f.name,
                                        new_field_name=nfield,
                                        new_field_alias=nfield
                                        )

field_tswatergap_dict = {
    'ruv_mm_um': ruv_list, #Runoff variability
    'gtr_ix_u': getfilelist(LRpred_gwtorunoff_gdb), #Groundwater recharge to reunoff ratio
    'pre_md_u': getfilelist(LRpred_prec_wetdays_gdb) #Number of precipitation days per month
}

for var in field_tswatergap_dict:
    start = time.time()
    out_table = os.path.join(LRpred_tabgdb, var)
    if not arcpy.Exists(out_table):
        print(f'Building {out_table}')
        extract_rename(out_table=out_table,
                       in_location_data=dryver_netpourpoints_sub,
                       in_rasters=field_tswatergap_dict[var],
                       id_field='DRYVER_RIVID',
                       fieldroot = var
                       )
    else:
        print(f'{out_table} already exists. Skipping...')
    end = time.time()
    print(end-start)


#Insert into a single table
field_dict = {
    'ai3_01_uav': 'ai_ix_m01_uav',
    'ai3_02_uav': 'ai_ix_m02_uav',
    'ai3_03_uav': 'ai_ix_m03_uav',
    'ai3_04_uav': 'ai_ix_m04_uav',
    'ai3_05_uav': 'ai_ix_m05_uav',
    'ai3_06_uav': 'ai_ix_m06_uav',
    'ai3_07_uav': 'ai_ix_m07_uav',
    'ai3_08_uav': 'ai_ix_m08_uav',
    'ai3_09_uav': 'ai_ix_m09_uav',
    'ai3_10_uav': 'ai_ix_m10_uav',
    'ai3_11_uav': 'ai_ix_m11_uav',
    'ai3_12_uav': 'ai_ix_m12_uav',
    'up_area_skm_15s': 'UPLAND_SKM',
    'pnv_cl_umj': 'pnv_cl_umj',
    'glc_cl_umj': 'glc_cl_umj',
    'eenv90_slope_deg_x100_uav': 'slp_dg_uav',
    'glims_glacier_ext_pc_acc': 'gla_pc_use',
    'hylak_all_area_pc_x100_acc': 'lka_pc_use',
    'permafrost_ext_pc_x100_use': 'prm_pc_use',
    'whymap_karst_v1_ras15s_bool_acc': 'kar_pc_use',
    'whymap_karst_v1_ras15s_bool': 'kar_pc_p'
}

# ----------- Extract values ------------------------------------------------------
statspred_paths = getfilelist(statpredgdb) + \
                  getfilelist(gai3gdb, repattern='ai3_[0-9]*_uav$')

flist = [f.name for f in arcpy.ListFields(dryver_netpourpoints)]
rtoextract = [f for f in statspred_paths #Only extract variable if it is:
              if ((os.path.basename(f) in field_dict) and #in list of variales to add
                  (os.path.basename(f) not in flist) and #its raw variable name is not already in target table
                  (field_dict[os.path.basename(f)] not in flist) #its formatted variable name is not already in target table
                  )]

ExtractMultiValuesToPoints(in_point_features = dryver_netpourpoints,
                           in_rasters = rtoextract,
                           bilinear_interpolate_values = 'NONE')

fast_joinfield(in_data=attri_tab,
               in_field='DRYVER_RIVID',
               join_table=dryver_netpourpoints,
               join_field='DRYVER_RIVID',
               fields=[['hylak_all_area_pc_x100_acc', 'lka_pc_use']],
               round=True)


#Format ID name
if 'DRYVER_RIVID' not in [f.name for f in arcpy.ListFields(dryver_netline)]:
    arcpy.management.AlterField(dryver_netline, 'grid_code', 'DRYVER_RIVID')
if 'DRYVER_RIVID' not in [f.name for f in arcpy.ListFields(dryver_netpourpoints)]:
    arcpy.management.AlterField(dryver_netpourpoints, 'grid_code', 'DRYVER_RIVID')

#Export table and format it
if not arcpy.Exists(attri_tab):
    print(f"Copying {attri_tab}...")
    arcpy.management.CopyRows(dryver_netpourpoints, attri_tab)

    print('Formatting fields...')
    for field in field_dict:
        if field in [f.name for f in arcpy.ListFields(attri_tab)]:
            arcpy.management.AlterField(attri_tab,
                                        field=field,
                                        new_field_name=field_dict[field],
                                        new_field_alias=field_dict[field])

    arcpy.management.DeleteField(attri_tab,
                                 [f.name for f in arcpy.ListFields(attri_tab)
                                  if f.name not in [arcpy.Describe(attri_tab).OIDFieldName,
                                               'DRYVER_RIVID']+list(field_dict.values())
                                 ])
#Compute groundwater depth in stream catchment
gwt_cav_tab = os.path.join(dryver_predvargdb, 'gwt_cm_cav')
if not arcpy.Exists(gwt_cav_tab):
    ZonalStatisticsAsTable(in_zone_data=dryver_netcatchments,
                           zone_field='Value',
                           in_value_raster=os.path.join(statpredgdb, 'fan_gwt_depth_mm_px'),
                           out_table=gwt_cav_tab,
                           ignore_nodata='DATA',
                           statistics_type='MEAN')


fast_joinfield(in_data=attri_tab,
               in_field='DRYVER_RIVID',
               join_table=gwt_cav_tab,
               join_field='Value',
               fields=[['MEAN', 'gwt_cm_cav']],
               round=True)

#Compute snow extent in whole catchment
for ras in getfilelist(dir = statpredgdb, repattern='snow_ext_pc_x100_m[0-9]{2}_px'):
    out_snow_tab = os.path.join(dryver_predvargdb,
                                re.sub('px', 'cav', os.path.basename(ras)))
    if not arcpy.Exists(out_snow_tab):
        print(f'Processing {out_snow_tab}...')
        ZonalStatisticsAsTable(in_zone_data=dryver_netcatchments,
                               zone_field='Value',
                               in_value_raster=ras,
                               out_table=out_snow_tab,
                               ignore_nodata='DATA',
                               statistics_type='MEAN')

    fast_joinfield(in_data=attri_tab,
                   in_field='DRYVER_RIVID',
                   join_table=out_snow_tab,
                   join_field='Value',
                   fields=[['MEAN', re.sub('snow_ext_pc_x100_', 'snw_pc_', os.path.basename(out_snow_tab))]],
                   round=True)

#Compute snow extent in whole catchment
for ras in getfilelist(dir = statpredgdb, repattern='snow_ext_pc_x100_m[0-9]{2}_px'):
    out_snow_tab = os.path.join(dryver_predvargdb,
                                re.sub('px', 'cav', os.path.basename(ras)))
    if not arcpy.Exists(out_snow_tab):
        print(f'Processing {out_snow_tab}...')
        ZonalStatisticsAsTable(in_zone_data=dryver_netcatchments,
                               zone_field='Value',
                               in_value_raster=ras,
                               out_table=out_snow_tab,
                               ignore_nodata='DATA',
                               statistics_type='MEAN')

    fast_joinfield(in_data=attri_tab,
                   in_field='DRYVER_RIVID',
                   join_table=out_snow_tab,
                   join_field='Value',
                   fields=[['MEAN', re.sub('snow_ext_pc_x100_', 'snw_pc_', os.path.basename(out_snow_tab))]],
                   round=True)

