from format_HydroSHEDS import *
import os.path
from utility_functions_py3 import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

scratchgdb = os.path.join(resdir, 'scratch.gdb')
pathcheckcreate(scratchgdb)
arcpy.env.scratchWorkspace = scratchgdb

gai3_outdir = os.path.join(datdir, 'GAIv3', 'Global-AI_v3_monthly')
gai3resgdb = os.path.join(resdir, 'gai3.gdb')
pathcheckcreate(gai3resgdb)

gai3var = {os.path.splitext(os.path.split(lyr)[1])[0]:lyr for lyr in
           getfilelist(gai3_outdir,'^ai_v3_[0-9]{1,2}.tif$')}

#Output paths
gai3_mismask = os.path.join(gai3resgdb, 'gai3hys_missmask')
gai3rsmp = {var:os.path.join(gai3resgdb, '{}_resample'.format(var)) for var in gai3var}
gai3template = gai3rsmp['ai_v3_01']
gai3nib = {var:os.path.join(gai3resgdb, '{}_nibble'.format(var)) for var in gai3var}

#Folder structure
geomdir = os.path.join(datdir, 'HydroATLAS', 'HydroATLAS_Geometry')

#Input layers (this would need to be edited for new direction maps)
directionras = os.path.join(geomdir, 'Flow_directions', 'flow_dir_15s_global.gdb', 'flow_dir_15s')
weightras = os.path.join(geomdir,'Accu_area_grids', 'pixel_area_skm_15s.gdb', 'px_area_skm_15s')
uplandras = os.path.join(geomdir, 'Accu_area_grids', 'upstream_area_skm_15s.gdb', 'up_area_skm_15s')

#Resample to match HydroSHEDS land mask using nearest neighbors
hydroresample(in_vardict=gai3var, out_vardict=gai3rsmp, in_hydrotemplate=hydrotemplate, resampling_type='NEAREST')

#Perform euclidean allocation for all pixels that are NoData in WorldClim layers but have data in HydroSHEDS land mask
arcpy.env.extent = arcpy.env.snapRaster = hydrotemplate
arcpy.env.XYResolution = "0.0000000000000001 degrees"
arcpy.env.cellSize = arcpy.Describe(hydrotemplate).meanCellWidth

# Perform euclidean allocation to HydroSHEDS land mask pixels with no WorldClim data
for var in gai3rsmp:
    if arcpy.Exists(gai3rsmp[var]):
        outnib = gai3nib[var]
        if not arcpy.Exists(outnib):
            print('Processing {}...'.format(outnib))
            try:
                mismask = Con((Raster(gai3rsmp[var]) == 0) & (~IsNull(Raster(hydrotemplate))), Raster(hydrotemplate))

                # Perform euclidean allocation to those pixels
                Nibble(in_raster=Con(~IsNull(mismask), -9999, Raster(gai3rsmp[var])),
                       # where mismask is not NoData (pixels for which var is NoData but hydrotemplate has data), assign nodatavalue (provided by user, not NoData), otherwise, keep var data (see Nibble tool)
                       in_mask_raster=gai3rsmp[var],
                       nibble_values='DATA_ONLY',
                       nibble_nodata='PRESERVE_NODATA').save(outnib)

                del mismask

            except Exception:
                print("Exception in user code:")
                traceback.print_exc(file=sys.stdout)
                del mismask
                arcpy.ResetEnvironments()

        else:
            print('{} already exists...'.format(outnib))
    else:
        print('Input - {} does not exists...'.format(gai3rsmp[var]))


gai3var = {os.path.splitext(os.path.split(lyr)[1])[0]:lyr for lyr in
           getfilelist(gai3_outdir,'^ai_v3_[0-9]{1,2}.tif$')}
gai3nib = {var:os.path.join(resdir, 'ai3_{}_nib'.format(var)) for var in
           [str(x).zfill(2) for x in range(1, 13)]}

for gai3_valuegrid in gai3nib.values():
    print(gai3_valuegrid)
    hydroUplandWeighting(value_grid=gai3_valuegrid,
                         direction_grid=directionras,
                         weight_grid=weightras,
                         upland_grid=uplandras,
                         scratch_dir=os.path.join(resdir, 'scratch.gdb'),
                         out_dir=resdir,
                         shiftval=0)

#Convert gai3 to integer (will need to structure better)
# gai3uav_gdb = os.path.join(resdir, 'gai3_uav.gdb')
# for ras in getfilelist(gai3uav_gdb, repattern='ai3_[0-9]*_uav$'):
#     round_ras = os.path.join(gai3uav_gdb, f'{os.path.basename(ras)}_int')
#     if not arcpy.Exists(round_ras):
#         print(f'rounding {ras}')
#         arcpy.management.CopyRaster(in_raster = ras,
#                                     out_rasterdataset = round_ras,
#                                     pixel_type = '16_BIT_UNSIGNED')

#No need to inspect as same mask as WorldClimv2 (see format_WorldClim2)