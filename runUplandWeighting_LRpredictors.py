import time
import numpy as np
import xarray as xr

from utility_functions_py3 import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

#Folder structure
geomdir = os.path.join(datdir, 'HydroATLAS', 'HydroATLAS_Geometry')
downscaling_dir_sa = os.path.join(datdir, 'aggregate_lrpredictors_sa')

#Input layers (this would need to be edited for new direction maps)
dis_ant_15s_dryver = os.path.join(downscaling_dir_sa, '15sec_dis_1_1981.tiff')

pxarea_grid = os.path.join(downscaling_dir_sa,'downscaling_static_data_sa', 'sa_pixarea_15s.tif')
uparea_grid = os.path.join(downscaling_dir_sa,'downscaling_static_data_sa', 'sa_upa_15s.tif')
flowdir_grid = os.path.join(downscaling_dir_sa,'downscaling_static_data_sa', 'sa_dir_15s.tif')

#Output directories
LRpred_dir_hist = os.path.join(downscaling_dir_sa,'lr_predictors_1981to2019')
LRpred_dir_cc = os.path.join(downscaling_dir_sa,'lr_predictors_GCMs')

LRpred_resdir = os.path.join(resdir, 'LRpredictors_sa')
pathcheckcreate(LRpred_resdir)

scratchgdb = os.path.join(LRpred_resdir, 'scratch.gdb')
pathcheckcreate(scratchgdb)

#Get variables (netcdf and multiplier to convert variable to integer)
LRpred_vardict = {}
LRpred_vardict['Prec_wetdays_1981_2019'] = [os.path.join(LRpred_dir_hist, "Prec_wetdays_1981_2019.nc"),
                                            pow(10,2)]
LRpred_vardict['qrdif_ql_ratio_mon_1981to2019'] = [os.path.join(LRpred_dir_hist, "qrdif_ql_ratio_mon_1981to2019.nc"),
                                                   pow(10,2)]
# LRpred_vardict['runoff_daily_var'] = [os.path.join(LRpred_dir_hist, "runoff_daily_var.nc"),
#                                       pow(10,6)]


def flowacc_nc(in_ncpath, in_var, in_template_extentlyr, in_template_resamplelyr,
               pxarea_grid, uparea_grid, flowdir_grid, out_resdir, scratchgdb, integer_multiplier):
    out_croppedintnc = os.path.join(out_resdir, "{}_croppedint.nc".format(in_var))
    LRpred_resgdb = os.path.join(out_resdir, "{}.gdb".format(in_var))
    pathcheckcreate(LRpred_resgdb)

    pred_nc = xr.open_dataset(in_ncpath)

    # Crop xarray and convert it to integer
    if not arcpy.Exists(out_croppedintnc):
        print("Producing {}".format(out_croppedintnc))
        templateext = arcpy.Describe(in_template_extentlyr).extent
        cropdict = {list(pred_nc.dims)[0]: slice(templateext.YMax, templateext.YMin),
                    list(pred_nc.dims)[1]: slice(templateext.XMin, templateext.XMax)}  # Lat is from north to south so need to reverse slice order
        pred_nc_cropped = pred_nc.loc[cropdict]
        (pred_nc_cropped * integer_multiplier).astype(np.intc).to_netcdf(out_croppedintnc)

    out_croppedint = os.path.join(scratchgdb, "{}_croppedint".format(in_var))
    #print("Saving {0} to {1}".format(out_croppedintnc, out_croppedint))
    arcpy.md.MakeNetCDFRasterLayer(in_netCDF_file=out_croppedintnc,
                                   variable=list(pred_nc.variables)[-1],
                                   x_dimension=list(pred_nc.dims)[1],
                                   y_dimension=list(pred_nc.dims)[0],
                                   out_raster_layer='tmpras',
                                   band_dimension=list(pred_nc.dims)[2],
                                   value_selection_method='BY_INDEX',
                                   cell_registration='CENTER')

        # For ArcGIS Pro (and add an "if not arcpy.Exists(out_croppedint) before "print("Saving {0} to {1}...")
        # output_ras = Raster('tmpras_check')
        # Con(output_ras >= 0, output_ras).save(out_croppedint)

    #For ArcGIS desktop
    out_croppedint_dict = {}
    ts_count = int(arcpy.Describe('tmpras').BandCount)
    for in_band in range(ts_count):
        out_croppedint_band = "{0}_{1}".format(out_croppedint, in_band+1)
        if not arcpy.Exists(out_croppedint_band):
            print('Processing {}'.format(out_croppedint_band))
            arcpy.MakeRasterLayer_management(in_raster='tmpras',
                                             out_rasterlayer="tmpras_{}".format(in_band+1),
                                             band_index="{}".format(in_band+1))
            compras = Raster("tmpras_{}".format(in_band+1))
            Con(compras >= 0, compras).save(out_croppedint_band)
            arcpy.Delete_management("tmpras_{}".format(in_band + 1))
        out_croppedint_dict[in_band+1] = out_croppedint_band


    # Set environment
    arcpy.env.extent = arcpy.env.snapRaster = in_template_resamplelyr
    # Resample
    for i in range(ts_count):
        start = time.time()
        out_rsmpbi = os.path.join(scratchgdb, "{0}_rsmpbi_{1}".format(in_var, i + 1))

        if not arcpy.Exists(out_rsmpbi):
            print("Resampling {}".format(out_croppedint_dict[i + 1]))
            arcpy.management.Resample(in_raster=out_croppedint_dict[i + 1],
                                      out_raster=out_rsmpbi,
                                      cell_size=arcpy.Describe(in_template_resamplelyr).MeanCellWidth,
                                      resampling_type='BILINEAR')

        # Run weighting
        value_grid = out_rsmpbi
        out_grid = os.path.join(LRpred_resgdb, '{0}_{1}'.format(in_var, i + 1))

        if not arcpy.Exists(out_grid):
            print("Running flow accumulation for {}".format(value_grid))
            # Multiply input grid by pixel area
            valueXarea = Times(Raster(value_grid), Raster(pxarea_grid))
            outFlowAccumulation = FlowAccumulation(in_flow_direction_raster=flowdir_grid,
                                                   in_weight_raster=valueXarea,
                                                   data_type="FLOAT")
            outFlowAccumulation_2 = Plus(outFlowAccumulation, valueXarea)
            UplandGrid = Int((Divide(outFlowAccumulation_2, Raster(uparea_grid))) + 0.5)
            UplandGrid.save(out_grid)
        end = time.time()
        print(end - start)

for var in LRpred_vardict:
    flowacc_nc(in_ncpath=LRpred_vardict[var][0],
               in_var=var,
               in_template_extentlyr=flowdir_grid,
               in_template_resamplelyr=dis_ant_15s_dryver,
               pxarea_grid=pxarea_grid,
               uparea_grid=uparea_grid,
               flowdir_grid=flowdir_grid,
               out_resdir=LRpred_resdir,
               scratchgdb=scratchgdb,
               integer_multiplier=LRpred_vardict[var][1])

# in_ncpath=LRpred_vardict[var][0]
# in_var=var
# in_template_extentlyr=flowdir_grid
# in_template_resamplelyr=dis_ant_15s_dryver
# pxarea_grid=pxarea_grid
# uparea_grid=uparea_grid
# flowdir_grid=flowdir_grid
# out_resdir=LRpred_resdir
# scratchgdb=scratchgdb
# integer_multiplier=LRpred_vardict[var][1]