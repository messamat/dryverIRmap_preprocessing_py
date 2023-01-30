from utility_functions import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

scratchgdb = os.path.join(resdir, 'scratch.gdb')
pathcheckcreate(scratchgdb)
arcpy.env.scratchWorkspace = scratchgdb

lcdir = os.path.join(datdir, 'HydroATLAS', 'HydroATLAS_Data', 'Landcover')
glclist = getfilelist(os.path.join(lcdir, 'landcover_glc2000_by_class_acc.gdb'))
glc_umaj = os.path.join(scratchgdb, 'glc_cl_umj')

pnvlist = getfilelist(os.path.join(lcdir, 'potential_vegetation_by_class_acc.gdb'))
pnv_umaj = os.path.join(scratchgdb, 'pnv_cl_umj')

#Compute upstream majority for landcover
HighestPosition(glclist).save(glc_umaj)
#Compute upstream majority for potential natural vegetation
HighestPosition(pnvlist).save(pnv_umaj)



