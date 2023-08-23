#Import libraries
from utility_functions_py3 import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

#Define paths
#Folder structure
HydroATLAS_datdir = os.path.join(datdir, 'HydroATLAS', 'HydroATLAS_Data')
statpredgdb = os.path.join(resdir, 'static_predictors', 'static_predictors.gdb')

LRpred_resdir = os.path.join(resdir, 'LRpredictors')
LRpred_runoffvar_gdb = os.path.join(LRpred_resdir, 'runoff_daily_var.gdb')
LRpred_gwtorunoff_gdb = os.path.join(LRpred_resdir, 'qrdif_ql_ratio_mon_1981to2019.gdb')
LRpred_prec_wetdays_gdb = os.path.join(LRpred_resdir, 'Prec_wetdays_1981_2019.gdb')

process_gdb = os.path.join(resdir, 'extend_HydroRIVERS_process.gdb')
dryver_netline = os.path.join(process_gdb, 'net_dryver_upao2_dis003')
dryver_netpourpoints = os.path.join(process_gdb, 'net_dryver_upao2_dis003_pourpoints')
dryver_netpourpoints_ras = os.path.join(process_gdb, 'net_dryver_upao2_dis003_pourpoints_ras')
dryver_netcatchments = os.path.join(process_gdb, 'net_dryver_upao2_dis003_catchments')

#uparea_grid = os.path.join(data_from_frankfurt_dir, '12_downscalingdata_eu', 'euassi_upa_15s.tif')

#Input variable rasters
gai3gdb = os.path.join(resdir, 'static_predictors', 'gai3_uav.gdb')

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

#~~~~~~~~~~~~~~~~~ Extract accumulated variables at reach pour points ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#Insert into a single table
field_dict_upstream = {
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
    'euassi_upa_15s': 'UPLAND_SKM',
    'pnv_cl_umj': 'pnv_cl_umj',
    'glc_cl_umj': 'glc_cl_umj',
    'eenv90_slope_deg_x100_uav': 'slp_dg_uav',
    'glims_glacier_ext_pc_acc': 'gla_pc_use',
    'hylak_all_area_pc_x100_acc': 'lka_pc_use',
    'permafrost_ext_pc_x100_use': 'prm_pc_use',
    'whymap_karst_v1_ras15s_bool_acc': 'kar_pc_use',
    'whymap_karst_v1_ras15s_bool': 'kar_pc_p',
    'gmia_equipped_ext_pc_x100_acc': 'ire_pc_use',
    'wp_filled_acc': 'ppd_pk_uav',
    'dor_pc_pva': 'dor_pc_pva',
    'cropland_ext_pc_x100_acc': 'crp_pc_use',
    'pasture_ext_pc_x100_acc': 'pst_pc_use',
    'carbon_tha_zeros_acc': 'soc_th_uav',
    'ghs_smod_2015_urb_ext_pc_acc': 'urb_pc_use',
}

# for cl in range(1, 23):
#     field_dict_upstream[f'glc2000_ext_bin_cl{str(cl).zfill(2)}_acc'] = f'glc_pc_c{str(cl).zfill(2)}'

statspred_paths = getfilelist(statpredgdb) + \
                  getfilelist(gai3gdb, repattern='ai3_[0-9]*_uav$')

flist = [f.name for f in arcpy.ListFields(dryver_netpourpoints)]
rtoextract = [f for f in statspred_paths #Only extract variable if it is:
              if ((os.path.basename(f) in field_dict_upstream) and #in list of variales to add
                  (os.path.basename(f) not in flist) and #its raw variable name is not already in target table
                  (field_dict_upstream[os.path.basename(f)] not in flist) #its formatted variable name is not already in target table
                  )]

ExtractMultiValuesToPoints(in_point_features = dryver_netpourpoints,
                           in_rasters = rtoextract,
                           bilinear_interpolate_values = 'NONE')

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
    for field in field_dict_upstream:
        if field in [f.name for f in arcpy.ListFields(attri_tab)]:
            arcpy.management.AlterField(attri_tab,
                                        field=field,
                                        new_field_name=field_dict_upstream[field],
                                        new_field_alias=field_dict_upstream[field])
    oidfname = arcpy.Describe(attri_tab).OIDFieldName
    arcpy.management.DeleteField(attri_tab,
                                 [f.name for f in arcpy.ListFields(attri_tab)
                                  if f.name not in ['DRYVER_RIVID']+list(field_dict_upstream.values())
                                 ])
else:
    attriflist = [f.name for f in arcpy.ListFields(attri_tab)]
    ftojoin = [[k, v] for k, v in field_dict_upstream.items() if v not in attriflist]
    if len(ftojoin) > 0:
        fast_joinfield(in_data=attri_tab,
                       in_field='DRYVER_RIVID',
                       join_table=dryver_netpourpoints,
                       join_field='DRYVER_RIVID',
                       fields=ftojoin,
                       round=False)

#~~~~~~~~~~~~~~~~~ Compute statistics within immediate reach catchments ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
field_dict_catchment = {
    'ele_mt_cav': [os.path.join(HydroATLAS_datdir, 'Physiography', 'elevation_earthenv_dem90.gdb', 'eenv90_elevation_m'),
                   'MEAN', 1],
    'crp_pc_cse': [os.path.join(HydroATLAS_datdir, 'Landcover', 'agriculture_earthstat.gdb', 'cropland_ext_pc_x100'),
                   'MEAN', 1],
    'pst_pc_cse': [os.path.join(HydroATLAS_datdir, 'Landcover', 'agriculture_earthstat.gdb', 'pasture_ext_pc_x100'),
                   'MEAN', 1],
    'soc_th_cav': [os.path.join(statpredgdb, 'carbon_tha_zeros'),
                   'MEAN', 1],
    'urb_pc_cse': [os.path.join(HydroATLAS_datdir, 'Demography', 'urban_areas_ghs_v2016.gdb', 'ghs_smod_2015_urb_ext_pc'),
                   'MEAN', 1],
    'gwt_cm_cav': [os.path.join(statpredgdb, 'fan_gwt_depth_mm_px'),
                   'MEAN', 1],
    'ire_pc_cse': [os.path.join(HydroATLAS_datdir, 'Landcover', 'irrigation_gmia.gdb', 'gmia_equipped_ext_pc_x100'),
                   'MEAN', 1],
    'ppd_pk_cav': [os.path.join(resdir, 'static_predictors', 'worldpop.gdb', 'wp_filled'),
                   'MEAN', 1]
}

for var in ['tmp_dc_c', 'pre_mm_c', 'pet_mm_c', 'snw_pc_c', 'glc_pc_c']:
    for m in range(1, 23):
        m_format = str(m).zfill(2)
        factor = 1
        if var == 'tmp_dc_c':
            path_ext = os.path.join('Climate', 'air_temperature_worldclim_month.gdb',
                            f'wclim_temp_deg_x10_m{m_format}')
        if var == 'pre_mm_c':
            path_ext = os.path.join('Climate', 'precipitation_worldclim_month.gdb',
                            f'wclim_prec_mm_m{m_format}')
        if var == 'pet_mm_c':
            path_ext = os.path.join('Climate', 'potential_evapotrans_cgiar_month.gdb',
                            f'global_pet_mm_m{m_format}'
            )
        # if var == 'snw_pc_c':
        #     path_ext = os.path.join('Climate', 'snow_cover_extent_modis_month.gdb',
        #                             f'snow_ext_pc_x100_m{m_format}'
        #                             )
        if var == 'glc_pc_c':
            path_ext = os.path.join('Landcover', 'landcover_glc2000_by_class.gdb',
                            f'glc2000_ext_bin_cl{m_format}')
            factor= 100

        path_full = os.path.join(HydroATLAS_datdir, path_ext)

        if arcpy.Exists(path_full):
            field_dict_catchment[f'{var}{m_format}'] = [path_full, 'MEAN', factor]

#Compute groundwater depth in catchment
attriflist = [f.name for f in arcpy.ListFields(attri_tab)]
for var in field_dict_catchment:
    if var not in attriflist:
        print(f'Processing {var}...')
        out_table = os.path.join(dryver_predvargdb, var)

        if not arcpy.Exists(out_table):
            print('Zonal statistics')
            ZonalStatisticsAsTable(in_zone_data=dryver_netcatchments,
                                   zone_field='Value',
                                   in_value_raster=field_dict_catchment[var][0],
                                   out_table=out_table,
                                   ignore_nodata='DATA',
                                   statistics_type=field_dict_catchment[var][1])

        # print('Join field')
        # fast_joinfield(in_data=attri_tab,
        #                in_field='DRYVER_RIVID',
        #                join_table=out_table,
        #                join_field='Value',
        #                fields=[[field_dict_catchment[var][1], var]],
        #                factor=field_dict_catchment[var][2],
        #                round=True)