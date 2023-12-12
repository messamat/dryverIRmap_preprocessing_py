from utility_functions_py3 import *
import xarray as xr
import numpy as np
import time
import netCDF4

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

analysis_period = 'future'

data_from_frankfurt_dir = os.path.join(datdir, 'data_from_frankfurt')

def flowacc_extract_nc(in_ncpath, in_var, in_template_extentlyr, in_template_resamplelyr,
                       pxarea_grid, uparea_grid, flowdir_grid, out_resdir, scratchgdb, integer_multiplier,
                       in_location_data, id_field, out_tabdir, fieldroot, save_raster=False, save_tab=True):

    out_croppedintnc = os.path.join(out_resdir, f"{in_var}_croppedint.nc")
    LRpred_resgdb = os.path.join(out_resdir, f"{in_var}.gdb")
    pathcheckcreate(LRpred_resgdb)

    pred_nc = xr.open_dataset(in_ncpath)
    new_variable_name = re.sub('\\s', '_', list(pred_nc.variables)[-1])

    out_tablist = [os.path.join(out_tabdir, f'{in_var}_{i + 1}') for i in range(pred_nc.coords.dims['Time (Month)'])]

    if not all([arcpy.Exists(out_tab) for out_tab in out_tablist]):
        # Crop xarray and convert it to integer
        if not arcpy.Exists(out_croppedintnc):
            print(f"Producing {out_croppedintnc}")
            templateext = arcpy.Describe(in_template_extentlyr).extent
            cropdict = {list(pred_nc.dims)[0]: slice(templateext.XMin, templateext.XMax),
                        list(pred_nc.dims)[1]: slice(templateext.YMax,
                                                     templateext.YMin)}  # Lat is from north to south so need to reverse slice order
            pred_nc_cropped = pred_nc.loc[cropdict]
            (pred_nc_cropped * integer_multiplier). \
                astype(np.intc). \
                rename({list(pred_nc.variables)[-1]:new_variable_name}). \
                to_netcdf(out_croppedintnc)

        out_croppedint = os.path.join(scratchgdb, f"{in_var}_croppedint")
        if not arcpy.Exists(out_croppedint):
            print(f"Saving {out_croppedintnc} to {out_croppedint}")
            arcpy.md.MakeNetCDFRasterLayer(in_netCDF_file=out_croppedintnc,
                                           variable=new_variable_name,
                                           x_dimension=list(pred_nc.dims)[0],
                                           y_dimension=list(pred_nc.dims)[1],
                                           out_raster_layer='tmpras_check',
                                           band_dimension=list(pred_nc.dims)[2],
                                           value_selection_method='BY_INDEX',
                                           cell_registration='CENTER')
            output_ras = Raster('tmpras_check')
            Con(output_ras >= 0, output_ras).save(out_croppedint)

        # Set environment
        arcpy.env.extent = arcpy.env.snapRaster = in_template_resamplelyr
        # Resample
        out_rsmpbi = os.path.join(scratchgdb, f"{re.sub(r'[ -]', '_', in_var)}_rsmpbi")
        if not arcpy.Exists(out_rsmpbi):
            print(f"Resampling {out_croppedint}")
            arcpy.management.Resample(in_raster=out_croppedint,
                                      out_raster=out_rsmpbi,
                                      cell_size=arcpy.Describe(in_template_resamplelyr).MeanCellWidth,
                                      resampling_type='BILINEAR')


        for i in range(int(arcpy.management.GetRasterProperties(out_rsmpbi, 'BANDCOUNT').getOutput(0))):
            # Run weighting
            value_grid = os.path.join(out_rsmpbi, f'Band_{i + 1}')
            out_grid = os.path.join(LRpred_resgdb, f'{in_var}_{i + 1}')
            out_table = os.path.join(out_tabdir, f'{in_var}_{i + 1}')

            if ((not arcpy.Exists(out_grid)) and save_raster) or \
                    ((not arcpy.Exists(out_table)) and save_tab):
                print(f"Running flow accumulation for {value_grid}")
                # Multiply input grid by pixel area
                start = time.time()
                valueXarea = Times(Raster(value_grid), Raster(pxarea_grid))
                outFlowAccumulation = FlowAccumulation(in_flow_direction_raster=flowdir_grid,
                                                       in_weight_raster=Raster(valueXarea),
                                                       data_type="FLOAT")
                outFlowAccumulation_2 = Plus(outFlowAccumulation, valueXarea)
                UplandGrid = Int((Divide(outFlowAccumulation_2, Raster(uparea_grid))) + 0.5)

                if save_raster:
                    UplandGrid.save(out_grid)
                if save_tab:
                    Sample(in_rasters=UplandGrid, in_location_data=in_location_data, out_table=out_table,
                           resampling_type='NEAREST', unique_id_field=id_field, layout='COLUMN_WISE',
                           generate_feature_class='TABLE')

                    arcpy.management.AlterField(out_table, field=os.path.split(in_location_data)[1],
                                                new_field_name=id_field, new_field_alias=id_field)

                    field_to_rename = [f.name for f in arcpy.ListFields(out_table) if f.name not in
                                       [id_field, 'X', 'Y', arcpy.Describe(out_table).OIDFieldName]]
                    arcpy.management.AlterField(out_table,
                                                field=field_to_rename[0],
                                                new_field_name=f'{fieldroot}_{i + 1}',
                                                new_field_alias=f'{fieldroot}_{i + 1}'
                                                )
                end = time.time()
                print(end - start)

        # arcpy.Delete_management(out_croppedint)
        # arcpy.Delete_management(out_rsmpbi)
    else:
        print("All tables already exists for {}".format(in_var))

def extract_rename(in_rasters, in_location_data, out_table, id_field, fieldroot):
    Sample(in_rasters=in_rasters, in_location_data=in_location_data, out_table=out_table,
           resampling_type='NEAREST', unique_id_field=id_field, layout='COLUMN_WISE', generate_feature_class='TABLE')

    arcpy.management.AlterField(out_table, field=os.path.split(in_location_data)[1],
                                new_field_name=id_field, new_field_alias=id_field)

    for f in arcpy.ListFields(out_table):
        rootvar = re.sub("[0-9]+$", "", os.path.split(in_rasters[0])[1])
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

#---------------------------------- LR predictors downscaling for historical period ------------------------------------
if analysis_period == 'historical':
    # Input layers
    dis_nat_15s_dryver = os.path.join(data_from_frankfurt_dir, 'WaterGAP_mean_1981to2019.tif')
    eu_flowdir_hydrosheds = os.path.join(datdir, 'HydroATLAS', 'HydroATLAS_Geometry', 'Flow_directions',
                                         'flow_dir_15s_by_continent.gdb', 'eu_dir_15s')

    pxarea_grid = os.path.join(data_from_frankfurt_dir, '12_downscalingdata_eu', 'euassi_pixarea_15s.tif')
    uparea_grid = os.path.join(data_from_frankfurt_dir, '12_downscalingdata_eu', 'euassi_upa_15s.tif')
    flowdir_grid = os.path.join(data_from_frankfurt_dir, '09_modifiedflowdir', 'eurasia_dir_geq0_15s.tif')

    #Output directories
    LRpred_dir = os.path.join(data_from_frankfurt_dir, 'LRpredictors_20230216')

    LRpred_resdir = os.path.join(resdir, 'LRpredictors')
    pathcheckcreate(LRpred_resdir)

    scratchgdb = os.path.join(LRpred_resdir, 'scratch.gdb')
    pathcheckcreate(scratchgdb)

    #Get variables (netcef and multiplier to convert variable to integer)
    LRpred_vardict = {}
    LRpred_vardict['Prec_wetdays_1981_2019'] = [os.path.join(LRpred_dir, "Prec_wetdays_1981_2019.nc"),
                                                pow(10,2)]
    LRpred_vardict['qrdif_ql_ratio_mon_1981to2019'] = [os.path.join(LRpred_dir, "qrdif_ql_ratio_mon_1981to2019.nc"),
                                                       pow(10,2)]
    LRpred_vardict['runoff_daily_var'] = [os.path.join(LRpred_dir, "runoff_daily_var.nc"),
                                          pow(10,6)]

    for var in LRpred_vardict:
        flowacc_extract_nc(in_ncpath=LRpred_vardict[var][0],
                           in_var=var,
                           in_template_extentlyr=eu_flowdir_hydrosheds,
                           in_template_resamplelyr=dis_nat_15s_dryver,
                           pxarea_grid=pxarea_grid,
                           uparea_grid=uparea_grid,
                           flowdir_grid=flowdir_grid,
                           out_resdir=LRpred_resdir,
                           scratchgdb=scratchgdb,
                           integer_multiplier=LRpred_vardict[var][1])

# ---------------------------------- LR predictors downscaling for future climate scenarios ----------------------------
if analysis_period == 'future':
    pxarea_grid = os.path.join(data_from_frankfurt_dir, 'downscaling_static_data_eu', 'eu_pixarea_15s.tif')
    uparea_grid = os.path.join(data_from_frankfurt_dir, 'downscaling_static_data_eu', 'eu_upa_15s.tif')
    flowdir_grid = os.path.join(data_from_frankfurt_dir, 'downscaling_static_data_eu', 'eu_dir_15s.tif')

    LRpred_datdir_gcms = os.path.join(data_from_frankfurt_dir, 'lr_predictors_GCMs')

    LRpred_resdir_gcms = os.path.join(resdir, 'LRpredictors_downscaled_GCMS')
    pathcheckcreate(LRpred_resdir_gcms)

    dryver_net_gdb = os.path.join(resdir, 'DRYVERnet.gdb')
    dryver_netpourpoints = os.path.join(dryver_net_gdb, 'dryvernet_prpt')

    dryver_netpourpoints_sub = os.path.join(dryver_net_gdb, 'dryvernet_prpt_sub')
    if not arcpy.Exists(dryver_netpourpoints_sub):
        arcpy.analysis.Clip(in_features=dryver_netpourpoints,
                            clip_features=arcpy.Describe(flowdir_grid).extent.polygon,
                            out_feature_class=dryver_netpourpoints_sub)

    # Create gdb for WaterGAP time-series predictors
    LRpred_tabgdb = os.path.join(resdir, 'LRpredtabs.gdb')
    pathcheckcreate(path=LRpred_tabgdb, verbose=True)

    #Get variables (netcef and multiplier to convert variable to integer)
    LRpred_vardict = {os.path.splitext(os.path.split(f)[1])[0]: [f] for f in getfilelist(LRpred_datdir_gcms)}
    for ts in LRpred_vardict:
        if re.findall('wetdays', ts):
            LRpred_vardict[ts].append(pow(10,2))
        elif re.findall('qrdifoverql', ts):
            LRpred_vardict[ts].append(pow(10,6))

    #Indices done: 0: 'gfdl-esm4_r1i1p1f1_w5e5_historical_wetdays', 1: 'gfdl-esm4_r1i1p1f1_w5e5_ssp126_wetdays',
    # 2:  'gfdl-esm4_r1i1p1f1_w5e5_ssp585_wetdays', 4: watergap2_2e_gfdl_esm4_w5e5_ssp126_2015soc_from_histsoc_qrdifoverql
    for var in list(LRpred_vardict.keys())[8:10]: #Using the list(dict.keys()) allows to slice it the keys
        in_var_formatted = re.sub(r'[ -.]', '_', var)

        scratchgdb_var = os.path.join(LRpred_resdir_gcms, 'scratch_{}.gdb'.format(in_var_formatted))
        pathcheckcreate(scratchgdb_var)

        final_csvtab = os.path.join(LRpred_resdir_gcms, "{}.csv".format(in_var_formatted))

        if not arcpy.Exists(final_csvtab):
            # Subset pourpoints if needed
            fieldroot = re.split('_', in_var_formatted)[-1]
            flowacc_extract_nc(in_ncpath=LRpred_vardict[var][0],
                               in_var=in_var_formatted,
                               in_template_extentlyr=flowdir_grid,
                               in_template_resamplelyr=flowdir_grid,
                               pxarea_grid=pxarea_grid,
                               uparea_grid=uparea_grid,
                               flowdir_grid=flowdir_grid,
                               out_resdir=LRpred_resdir_gcms,
                               scratchgdb=scratchgdb_var,
                               integer_multiplier=LRpred_vardict[var][1],
                               in_location_data=dryver_netpourpoints_sub,
                               out_tabdir = LRpred_tabgdb,
                               id_field='DRYVER_RIVID',
                               fieldroot= fieldroot,
                               save_raster=False,
                               save_tab=True)

            pred_nc = xr.open_dataset(LRpred_vardict[var][0])
            new_variable_name = re.sub('\\s', '_', list(pred_nc.variables)[-1])
            out_tablist = [os.path.join(LRpred_tabgdb, f'{in_var_formatted}_{i + 1}') for i in
                           range(pred_nc.coords.dims['Time (Month)'])]
            def get_LRpred_pd(in_gdbtab, in_fieldroot, in_dtype, last_col=False):
                print(in_gdbtab)

                var_colname = "{0}_{1}".format(
                    in_fieldroot,
                    re.findall('[0-9]{1,3}$', os.path.split(in_gdbtab)[1])[0])

                if last_col:
                    step_pd = pd.DataFrame(data=arcpy.da.SearchCursor(in_gdbtab,
                                                                      [f.name for f in arcpy.ListFields(in_gdbtab)][-1]),
                                           dtype=in_dtype)
                    step_pd.columns = [var_colname]
                else:
                    rcols = ['DRYVER_RIVID', var_colname]
                    step_pd = pd.DataFrame(data=arcpy.da.SearchCursor(in_gdbtab, rcols),
                                           columns=rcols,
                                           dtype=in_dtype)
                return(step_pd)

            if all([arcpy.Exists(out_tab) for out_tab in out_tablist]):
                print("Concatenating tables...")
                out_tab = get_LRpred_pd(in_gdbtab=out_tablist[0],
                                        in_fieldroot=fieldroot,
                                        in_dtype=np.int32)

                invar_types = {'qrdifoverql': np.int32,
                               'wetdays': np.int16}

                for in_tab in out_tablist[1:]:
                    temp_tab = get_LRpred_pd(in_gdbtab=in_tab,
                                             in_fieldroot=fieldroot,
                                             in_dtype=invar_types[fieldroot],
                                             last_col=True)
                    if len(temp_tab) == len(out_tab):
                        out_tab = pd.concat([out_tab, temp_tab], axis=1)
                    else:
                        raise Exception("gdb table is not the same length as main table")

                print("Writing out {}...".format(final_csvtab))
                out_tab.to_csv(final_csvtab)