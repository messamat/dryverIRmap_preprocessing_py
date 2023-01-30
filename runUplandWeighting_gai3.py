import os.path

from utility_functions import *
from runUplandWeighting import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

#Folder structure
geomdir = os.path.join(datdir, 'HydroATLAS', 'HydroATLAS_Geometry')

#Input layers (this would need to be edited for new direction maps)
directionras = os.path.join(geomdir, 'Flow_directions', 'flow_dir_15s_global.gdb', 'flow_dir_15s')
weightras = os.path.join(geomdir,'Accu_area_grids', 'pixel_area_skm_15s.gdb', 'px_area_skm_15s')
uplandras = os.path.join(geomdir, 'Accu_area_grids', 'upstream_area_skm_15s.gdb', 'up_area_skm_15s')

def hydroUplandWeighting(value_grid, direction_grid, weight_grid, upland_grid, scratch_dir,
                        out_dir, shiftval=0, overwrite=False):
    #Check that directories exist, otherwise, create them
    pathcheckcreate(scratch_dir)
    pathcheckcreate(out_dir)
    arcpy.env.scratchWorkspace = scratch_dir

    #UPLAND WEIGHT GRID
    nameroot = os.path.splitext(os.path.split(value_grid)[1])[0]
    out_grid = os.path.join(scratch_dir, '{}_acc'.format(nameroot))
    xpxarea = os.path.join(scratch_dir, '{}_xpxarea'.format(nameroot))
    xpxarea_ac1 = os.path.join(scratch_dir, '{}_xpxarea_ac1'.format(nameroot))
    xpxarea_ac_fin = os.path.join(scratch_dir, '{}_xpxarea_ac_fin'.format(nameroot))

    if (not arcpy.Exists(out_grid)) or (overwrite == True):
        try:
            set_environment(out_dir, direction_grid)

            # Multiply input grid by pixel area
            print('Processing {}...'.format(xpxarea))
            valueXarea = Times(Raster(value_grid) + float(shiftval), Raster(weight_grid))
            valueXarea.save(xpxarea)

            # Flow accumulation of value grid and pixel area product
            print('Processing {}...'.format(xpxarea_ac1))
            outFlowAccumulation = FlowAccumulation(direction_grid, Raster(xpxarea), "FLOAT")
            outFlowAccumulation.save(xpxarea_ac1)

            print('Processing {}...'.format(xpxarea_ac_fin))
            outFlowAccumulation_2 = Plus(xpxarea_ac1, xpxarea)
            outFlowAccumulation_2.save(xpxarea_ac_fin)

            # Divide by the accumulated pixel area grid
            print('Processing {}...'.format(out_grid))
            UplandGrid = (Divide(xpxarea_ac_fin, upland_grid)-shiftval)
            UplandGrid.save(out_grid)

        except Exception, e:
            # If an error occurred, print line number and error message
            import traceback, sys
            tb = sys.exc_info()[2]
            arcpy.AddMessage("Line %i" % tb.tb_lineno)
            arcpy.AddMessage(str(e.message))

        print('Deleting intermediate grids...')
        for lyr in [xpxarea, xpxarea_ac1, xpxarea_ac_fin]:
            if arcpy.Exists(lyr):
                arcpy.Delete_management(lyr)
    else:
        print('{} already exists and overwrite==False...'.format(out_grid))


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