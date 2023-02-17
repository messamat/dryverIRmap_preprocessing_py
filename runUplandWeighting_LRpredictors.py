from utility_functions_py3 import *
import xarray as xr
import numpy as np
import time

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

#Folder structure
geomdir = os.path.join(datdir, 'HydroATLAS', 'HydroATLAS_Geometry')

#Input layers (this would need to be edited for new direction maps)
eu_flowdir_hydrosheds = os.path.join(datdir, 'HydroATLAS', 'HydroATLAS_Geometry', 'Flow_directions',
                                     'flow_dir_15s_by_continent.gdb', 'eu_dir_15s')

data_from_frankfurt_dir = os.path.join(datdir, 'data_from_frankfurt')
dis_nat_15s_dryver = os.path.join(data_from_frankfurt_dir, 'WaterGAP_mean_1981to2019.tif')

pxarea_grid = os.path.join(data_from_frankfurt_dir, '12_downscalingdata_eu', 'euassi_pixarea_15s.tif')
uparea_grid = os.path.join(data_from_frankfurt_dir, '12_downscalingdata_eu', 'euassi_upa_15s.tif')
flowdir_grid = os.path.join(data_from_frankfurt_dir, '09_modifiedflowdir', 'eurasia_dir_geq0_15s.tif')

#Output directories
LRpred_dir = os.path.join(data_from_frankfurt_dir, 'LRpredictors_20230216')

LRpred_resdir = os.path.join(resdir, 'LRpredictors')
pathcheckcreate(LRpred_resdir)

scratchgdb = os.path.join(LRpred_resdir, 'scratch.gdb')
pathcheckcreate(scratchgdb)


#Get variables
LRpred_vardict = {}
LRpred_vardict['Prec_wetdays_1981_2019'] = [os.path.join(LRpred_dir, "Prec_wetdays_1981_2019.nc"),
                                            pow(10,2)]
LRpred_vardict['qrdif_ql_ratio_mon_1981to2019'] = [os.path.join(LRpred_dir, "qrdif_ql_ratio_mon_1981to2019.nc"),
                                                   pow(10,2)]
LRpred_vardict['runoff_daily_var'] = [os.path.join(LRpred_dir, "runoff_daily_var.nc"),
                                      pow(10,6)]


def flowacc_nc(in_ncpath, in_var, in_template_extentlyr, in_template_resamplelyr,
               pxarea_grid, uparea_grid, flowdir_grid, out_resdir, scratchgdb, integer_multiplier):
    out_croppedintnc = os.path.join(out_resdir, f"{in_var}_croppedint.nc")
    LRpred_resgdb = os.path.join(out_resdir, f"{in_var}.gdb")
    pathcheckcreate(LRpred_resgdb)

    pred_nc = xr.open_dataset(in_ncpath)

    # Crop xarray and convert it to integer
    if not arcpy.Exists(out_croppedintnc):
        print(f"Producing {out_croppedintnc}")
        templateext = arcpy.Describe(in_template_extentlyr).extent
        cropdict = {list(pred_nc.dims)[0]: slice(templateext.XMin, templateext.XMax),
                    list(pred_nc.dims)[1]: slice(templateext.YMax,
                                                 templateext.YMin)}  # Lat is from north to south so need to reverse slice order
        pred_nc_cropped = pred_nc.loc[cropdict]
        (pred_nc_cropped * integer_multiplier).astype(np.intc).to_netcdf(out_croppedintnc)

    out_croppedint = os.path.join(scratchgdb, f"{in_var}_croppedint")
    if not arcpy.Exists(out_croppedint):
        print(f"Saving {out_croppedintnc} to {out_croppedint}")
        arcpy.md.MakeNetCDFRasterLayer(in_netCDF_file=out_croppedintnc,
                                       variable=list(pred_nc.variables)[-1],
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
    out_rsmpbi = os.path.join(scratchgdb, f"{in_var}_rsmpbi")
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

        if not arcpy.Exists(out_grid):
            print(f"Running flow accumulation for {value_grid}")
            # Multiply input grid by pixel area
            start = time.time()
            valueXarea = Times(Raster(value_grid), Raster(pxarea_grid))
            outFlowAccumulation = FlowAccumulation(in_flow_direction_raster=flowdir_grid,
                                                   in_weight_raster=Raster(valueXarea),
                                                   data_type="FLOAT")
            outFlowAccumulation_2 = Plus(outFlowAccumulation, valueXarea)
            UplandGrid = Int((Divide(outFlowAccumulation_2, Raster(uparea_grid))) + 0.5)
            UplandGrid.save(out_grid)
            end = time.time()
            print(end - start)

for var in LRpred_vardict:
    flowacc_nc(in_ncpath=LRpred_vardict[var][0],
               in_var=var,
               in_template_extentlyr=eu_flowdir_hydrosheds,
               in_template_resamplelyr=dis_nat_15s_dryver,
               pxarea_grid=pxarea_grid,
               uparea_grid=uparea_grid,
               flowdir_grid=flowdir_grid,
               out_resdir=LRpred_resdir,
               scratchgdb=scratchgdb,
               integer_multiplier=LRpred_vardict[var][1])