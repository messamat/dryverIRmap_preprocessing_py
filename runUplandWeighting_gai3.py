import os.path

from utility_functions_py3 import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

#Folder structure
geomdir = os.path.join(datdir, 'HydroATLAS', 'HydroATLAS_Geometry')

#Input layers (this would need to be edited for new direction maps)
directionras = os.path.join(geomdir, 'Flow_directions', 'flow_dir_15s_global.gdb', 'flow_dir_15s')
weightras = os.path.join(geomdir,'Accu_area_grids', 'pixel_area_skm_15s.gdb', 'px_area_skm_15s')
uplandras = os.path.join(geomdir, 'Accu_area_grids', 'upstream_area_skm_15s.gdb', 'up_area_skm_15s')

############################ Global Aridity Index v3 ###########################################################
gai3_outdir = os.path.join(datdir, 'GAIv3')
gai3resgdb = os.path.join(resdir, 'gai3.gdb')

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