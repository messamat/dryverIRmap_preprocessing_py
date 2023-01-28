from utility_functions import *
from format_HydroSHEDS import *

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


#No need to inspect as same mask as WorldClimv2 (see format_WorldClim2)