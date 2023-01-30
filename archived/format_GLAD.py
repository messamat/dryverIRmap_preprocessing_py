import os
import arcpy
from arcpy.sa import *
import sys
import re
import time
import math
from utility_functions import *
import numpy as np
import cProfile

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True
arcpy.env.parallelProcessingFactor = "100%"

# Set up dir structure
rootdir = os.path.dirname(os.path.abspath(__file__)).split('\\src')[0]
datdir = os.path.join(rootdir, 'data')
resdir = os.path.join(rootdir, 'results')
scratchdir = os.path.join(rootdir, 'scratch')
scratchgdb = os.path.join(scratchdir, 'scratch.gdb')
pathcheckcreate(scratchgdb)
arcpy.env.scratchWorkspace = scratchgdb

hydrotemplate = os.path.join(datdir, 'Bernhard', 'HydroATLAS' ,'HydroATLAS_Geometry', 'Masks',
                             'hydrosheds_landmask_15s.gdb', 'hys_land_15s') # Grab HydroSHEDS layer for one continent as template
hydrolakes = os.path.join(datdir, 'hydrolakes', 'HydroLAKES_polys_v10.gdb', 'HydroLAKES_polys_v10')
glad_dir = os.path.join(datdir, 'GLAD')
alos_dir = os.path.join(datdir, 'ALOS')
mod44w_outdir = os.path.join(datdir, 'mod44w')
mod44w_resgdb = os.path.join(resdir, 'mod44w.gdb')
alosresgdb = os.path.join(resdir, 'alos.gdb')
gladresgdb = os.path.join(resdir, 'glad.gdb')
pathcheckcreate(gladresgdb)
pathcheckcreate(alosresgdb)
pathcheckcreate(mod44w_resgdb)

#GLAD values mean the following
#0: NoData, 1: Land, 2: Permanent water, 3: Stable seasonal, 4: Water gain, 5: Water loss
#6: Dry period, 7: Wet period, 8: High frequency, 10: Probable land, 11: Probable water, 12: Sparse data - exclude

########################################################################################################################
#Get list of tiles for raw GLAD tiles, mod44w (MODIS sea mask) and ALOS (DEM)
print('Getting tile lists for GLAD, MODIS, and ALOS...')
rawtilelist = getfilelist(glad_dir, 'class99_19.*[.]tif$')
alos_tilelist = getfilelist(alos_dir, 'ALPSMLC30_[NS][0-9]{3}[WE][0-9]{3}_DSM.tif$')
alos_wgsextdict= {i: arcpy.Describe(i).extent for i in alos_tilelist}

mod44w_tilelist = getfilelist(mod44w_outdir, '.*[.]hdf$')
#Rename all MODIS files that have points with underscores
if any([re.search('[.]', os.path.splitext(os.path.split(i)[1])[0]) for i in mod44w_tilelist]):
    for modtile in mod44w_tilelist:
        modtile_renamed = '{}.hdf'.format(re.sub('[.]', '_', os.path.splitext(os.path.split(modtile)[1])[0]))
        os.rename(modtile,os.path.join(mod44w_outdir, modtile_renamed))

#Define functions
def create_GLADseamask(in_gladtile, in_mod44w, in_alositerator, in_lakes, outpath, processgdb):
    """
    Identifies sea/ocean water pixels in a GLAD surface water classes tile
    :param in_gladtile: path to GLAD tile to be processed
    :param in_mod44w: path of extracted and mosaicked MOD44W C6 QA layer envelopping GLAD tile
    :param in_alositerator: list of dictionary that contains extents of intersecting ALOS DEM tiles
    :return: GLAD tile with same extent and pixel size but where sea water pixels are identified as class 9
    """
    gladtileid = 'glad{}'.format(re.sub('(^.*class99_1[89]_)|([.]tif)', '',
                                        gladtile))  # Unique identifier for glad tile based on coordinates
    gladtile_extent = arcpy.Describe(gladtile).extent
    mod44w_outdir = os.path.split(in_mod44w)[0]

    print('Creating seamask for {}...'.format(gladtileid))
    # Run a 3x3 majority filter on MODIS to get rid of isolated sea pixels
    modmaj = os.path.join(mod44w_outdir, 'mod44wmaj_{}'.format(gladtileid))
    print('    1/15 - Majority filter of MODIS QA layer...')
    if not arcpy.Exists(modmaj):
        focallyr = FocalStatistics(in_raster=in_mod44w,
                                   neighborhood=NbrRectangle(4, 4, "CELL"),
                                   statistics_type='MAJORITY')
        Con(IsNull(focallyr), Raster(in_mod44w), focallyr).save(modmaj)

    # Project, adjust cell size, and snap MODIS to GLAD tile
    print('    2/15 - Project and resample MODIS to match GLAD tile...')
    arcpy.env.snapRaster = in_gladtile
    arcpy.env.extent = in_gladtile
    mod44w_gladmatch_wgs = os.path.join(mod44w_outdir, 'mod44wQA_glad{}_wgs'.format(gladtileid))
    if not arcpy.Exists(mod44w_gladmatch_wgs):
        # try:
        #     arcpy.Delete_management(mod44w_gladmatch_wgs)
        # except:
        #     traceback.print_exc()
        arcpy.ProjectRaster_management(modmaj,
                                       out_raster=mod44w_gladmatch_wgs,
                                       in_coor_system=arcpy.Describe(in_mod44w).SpatialReference,
                                       out_coor_system= arcpy.SpatialReference(4326), #WGS84, same as  in_gladtile,
                                       cell_size=arcpy.Describe(in_gladtile).meanCellWidth,
                                       resampling_type='NEAREST')

    # ----------- Format ALOS ----------------------------------------------------------------------------------------------
    # Subset tiles to only keep those that intersect the GLAD tile
    print('    3/15 - Getting intersecting ALOS DEM tiles...')
    alos_seltiles = get_inters_tiles(ref_extent=gladtile_extent, tileiterator=in_alositerator, containsonly=False)

    # Format ALOS
    alos_mosaictile = os.path.join(processgdb, 'alos_mosaic_{}'.format(gladtileid))
    print('    4/15 - Mosaicking ALOS DEM tiles...')
    if not arcpy.Exists(alos_mosaictile):
        arcpy.MosaicToNewRaster_management(input_rasters=alos_seltiles,
                                           output_location=os.path.split(alos_mosaictile)[0],  # 'in_memory
                                           raster_dataset_name_with_extension=os.path.split(alos_mosaictile)[1],
                                           pixel_type='16_BIT_SIGNED',
                                           number_of_bands=1)

    alos_rsp = os.path.join(processgdb, 'alos_rsp{}'.format(gladtileid))
    print('    5/15 - Resampling ALOS DEM...')
    if not arcpy.Exists(alos_rsp):
        arcpy.Resample_management(in_raster=alos_mosaictile,
                                  out_raster=alos_rsp,
                                  cell_size=arcpy.Describe(in_gladtile).meanCellWidth,
                                  resampling_type='NEAREST')

    # ----------- Format HydroLAKES  ------------------------------------------------------------
    lakeras = os.path.join(processgdb, '{}_lakeras'.format(gladtileid))
    print('    6/15 - Rasterizing HydroLAKES...')
    if not arcpy.Exists(lakeras):
        arcpy.PolygonToRaster_conversion(in_features=in_lakes,
                                         value_field="Lake_type",
                                         out_rasterdataset=lakeras,
                                         cell_assignment='CELL_CENTER',
                                         cellsize=arcpy.Describe(in_gladtile).meanCellWidth)

    # ----------- Create seamask based on MODIS, ALOS, and GLAD  ------------------------------------------------------------
    # Create GLAD land-water mask
    print('    7/15 - Creating GLAD land-water mask, excluding known lake pixels from the analysis...')
    gladtile_mask = os.path.join(processgdb, '{}_mask'.format(gladtileid))
    if not arcpy.Exists(gladtile_mask):
        arcpy.CopyRaster_management(in_raster=Con(IsNull(lakeras),
                                                  Reclassify(in_gladtile, "Value",
                                                             RemapValue(
                                                                 [[0, "NoData"], [1, 1], [2, 2], [3, 2], [4, 2], [5, 2],
                                                                  [6, 2], [7, 2], [8, 2], [10, 1], [11, 2], [12, 0]])),
                                                  0),
                                    out_rasterdataset=gladtile_mask,
                                    pixel_type='4_BIT')

    # Prepare pixels that are water, under 0 m elevation and not already labeled as seamask by MOD44W for Nibbling
    gladtile_shore = os.path.join(processgdb, '{}_shore'.format(gladtileid))
    # If seawater in MODIS seamask and water in GLAD:
    #   9
    # else:
    #   if elevation > 0 or land in glad:
    #       glad values
    #   else (i.e. <0 & water in glad):
    #       NoData
    print('    8/15 - Creating shore mask to nibble on i.e. GLAD water, '
          'under 0 m elevation and not already labeled as seamask by MOD44W for Nibbling...')
    if not arcpy.Exists(gladtile_shore):
        Con((Raster(mod44w_gladmatch_wgs) == 4) & (Raster(gladtile_mask) == 2),
            3,
            Con((Raster(alos_rsp) > 0) | (Raster(gladtile_mask) < 2),
                Raster(gladtile_mask))).save(gladtile_shore)

    # Expand seamask in contiguous areas < 0 meters in elevation and identified as water in GLAD
    print('    9/15 - Expanding seamask in contiguous areas <= 0 meters in elevation and identified as water in GLAD...')
    outnibble1 = os.path.join(processgdb, '{}_1nibble'.format(gladtileid))
    if not arcpy.Exists(outnibble1):
        Nibble(in_raster=Raster(gladtile_shore), in_mask_raster=Raster(gladtile_shore),
               nibble_values='DATA_ONLY', nibble_nodata='PROCESS_NODATA',
               in_zone_raster=Con(IsNull(Raster(gladtile_shore)), 1,
                                  Con(Raster(gladtile_shore) == 3, 1, 0))
               ).save(outnibble1)

    # Expand seamask by ten pixels in non-sea GLAD water pixels under 10 m in elevation
    outexpand = os.path.join(processgdb, '{}_expand'.format(gladtileid))
    print(
        '    10/15 - Expand seamask by ten pixels in non-sea GLAD water pixels...')  # Another option is to constrain it at water under 10 m elevation but does not work under 10 m in elevation...')
    if not arcpy.Exists(outexpand):
        Con((Raster(outnibble1) == 2),  # & (Raster(alos_rsp)<10),
            Expand(in_raster=Raster(outnibble1), number_cells=10, zone_values=3),
            Raster(outnibble1)).save(outexpand)

    # Fill in remaining water pixels under 0 m elevation and not already labeled with nearest water value, whether inland or sea
    outnibble2 = os.path.join(processgdb, '{}_2nibble'.format(gladtileid))
    print('    11/15 - Fill in remaining water pixels under 0 m elevation and'
          ' not already labeled with nearest water value, whether inland or sea...')
    if not arcpy.Exists(outnibble2):
        Nibble(in_raster=outexpand, in_mask_raster=outexpand,
               nibble_values='DATA_ONLY', nibble_nodata='PROCESS_NODATA',
               in_zone_raster=Raster(gladtile_mask) == 2
               ).save(outnibble2)

    # Get regions
    outregion = os.path.join(processgdb, '{}_region'.format(gladtileid))
    print('    12/15 - Create regions out of contiguous areas...')
    if not arcpy.Exists(outregion):
        RegionGroup(in_raster=outnibble2,
                    number_neighbors='FOUR',
                    zone_connectivity='WITHIN',
                    excluded_value=1).save(outregion)

    # Remove sea mask regions under 2000 pixels. This avoids having artefact patches surrounded by land or inland water
    outregionclean = os.path.join(processgdb, '{}_regionclean'.format(gladtileid))
    print('    13/15 - Removing sea mask regions under 2000 pixels. '
          'This avoids having artefact patches surrounded by land or inland water...')
    if not arcpy.Exists(outregionclean):
        Con(IsNull(ExtractByAttributes(outregion, 'LINK = 3 AND Count > 2000')),
            gladtile_mask,
            3).save(outregionclean)

    # Fill in inland water zones entirely surrounded by sea water
    outeuc = os.path.join(processgdb, '{}_euc'.format(gladtileid))
    print('    14/15 - Filling in inland water zones entirely surrounded by sea water...')
    if not arcpy.Exists(outeuc):
        EucAllocation(in_source_data=InList(outregionclean, [0, 1, 3])).save(outeuc)

    outzone = os.path.join(processgdb, '{}_zone'.format(gladtileid))
    if not arcpy.Exists(outzone):
        ZonalStatistics(in_zone_data=outregion,
                        zone_field='Value',
                        in_value_raster=outeuc,
                        statistics_type='RANGE').save(outzone)

    print('    15/15 - Creating final formatted GLAD tile with sea mask...')
    # #1. To deal with remaining NoData (< 0 elevation)
    # #2. There are NoData pixels that remain following the second nibble in areas where formerly water pixels have become
    # out of contact with any other water pixel. This carries into outregion and outzone, and so must be dealt with
    # in the last step
    # #3 all other pixels that have been identified as sea water

    if not arcpy.Exists(outpath):
        Con(IsNull(Raster(outregionclean)), in_gladtile,                                                    #1
            Con(IsNull(outzone), in_gladtile,                                                               #2
                Con(((Raster(outzone) == 0) & (Raster(outeuc) == 3) & (Raster(outregionclean) == 2)) | (    #3
                        Raster(outregionclean) == 3),
                    9,
                    in_gladtile))).save(outpath)

    arcpy.ClearEnvironment('extent')
    arcpy.ClearEnvironment('snapRaster')
    arcpy.ClearEnvironment('cellSize')
    arcpy.ClearEnvironment('mask')

#---------------------------- Remove GLAD tiles with only 0 values -----------------------------------------------------
remove0tiles = False #This takes a bit of time to run so, the first time the code is run after downloading GLAD tiles, it should be run once

if remove0tiles == True:
    print('Removing GLAD tiles with only NoData or Sparse values...')
    for tile in rawtilelist:
        print(tile)
        # Get unique categorical values
        if not Raster(tile).hasRAT and arcpy.Describe(tile).bandCount == 1:  # Build attribute table if doesn't exist
            try:
                arcpy.BuildRasterAttributeTable_management(tile)  # Does not work
            except Exception:
                e = sys.exc_info()[1]
                print(e.args[0])
                arcpy.DeleteRasterAttributeTable_management(tile)

        gladvals = {row[0] for row in arcpy.da.SearchCursor(tile, 'Value')}

        if len(gladvals) == 1:  # If only one value across entire tile
            if list(gladvals)[0] == 0 or list(gladvals)[0] == 12:  # And that value is NoData
                print('Tile only has NoData values, deleting...')
                arcpy.Delete_management(tile)  # Delete tile
        if len(gladvals) == 2:  # If only one value across entire tile
            if 0 in gladvals & 12 in gladvals:
                print('Tile only has NoData values, deleting...')
                arcpy.Delete_management(tile)  # Delete tile

#---------------------------- Get dictionary of MODIS tile extents -----------------------------------------------------
#Get wgs84 extent of all mod44w tiles (because MODIS is in custom Spheroid Sinusoidal projection)
mod44w_wgsextdict= {}
mod44w_sr = arcpy.Describe(mod44w_tilelist[0]).spatialReference
print('Getting dictionary of MODIS tile extents in WGS84...')
for i in mod44w_tilelist:
    #Get MODIS tile id
    modtileid = re.search('(?<=MOD44W_A2015001_)h[0-9]{2}v[0-9]{2}(?=[0-9_]{18}[.]hdf)',
                          os.path.split(i)[1]).group()
    outmodext = os.path.join(mod44w_resgdb, 'extpoly{}'.format(modtileid))
    if not arcpy.Exists(outmodext):
        print(i)
        mod44w_wgsextdict[i] = project_extent(in_dataset=i, out_coor_system=rawtilelist[0], out_dataset=outmodext)
    else:
        #Add extent to dictionary as value with MODIS tile id as the key
        mod44w_wgsextdict[i] = arcpy.Describe(outmodext).extent

######################################## Iterate through GLAD tiles to generate sea mask ###############################
mod44w_mosaiclist = []

#For each GLAD 10 degree by 10 degree tile
print('Iterating through GLAD tiles...')
#Test MODIS tiling/mosaicking with gladtile = rawtilelist[2]
for gladtile in rawtilelist:
    gladtileid = 'glad{}'.format(
        re.sub('(^.*class99_1[89]_)|([.]tif)', '', gladtile))  # Unique identifier for glad tile based on coordinates
    outseafinal = os.path.join(gladresgdb, '{}_seamask'.format(gladtileid))
    if not arcpy.Exists(outseafinal):
        print(gladtile)
        #For troublshooting
            #gladtile = os.path.join(gladresgdb, 'glad_seatest')
            #gladtileid = "seatest"
            #gladtile = rawtilelist[1]

        gladtile_extent = arcpy.Describe(gladtile).extent

        #---------------------------- Identify sea vs freshwater pixels --------------------------------------------------------
        #----------- Format MODIS ----------------------------------------------------------------------------------------------
        #First check whether an already-processed MODIS tile contains the entire area
        print('Getting mosaic of MODIS tiles that intersect GLAD tile...')
        mod44w_seltiles = get_inters_tiles(ref_extent=gladtile_extent, tileiterator=mod44w_mosaiclist, containsonly=True)

        #If no existing extracted mosaick exists
        if len(mod44w_seltiles)>1 or len(mod44w_seltiles)==0:
            mod44w_seltiles = get_inters_tiles(ref_extent=gladtile_extent, tileiterator=mod44w_wgsextdict, containsonly=False)

            #Extract QA dataset
            mod44w_seltilesQA = []
            for tile in mod44w_seltiles:
                modtileid = re.search('(?<=MOD44W_A2015001_)h[0-9]{2}v[0-9]{2}(?=[0-9_]{18}[.]hdf)',
                                      os.path.split(tile)[1]).group()
                outQA = os.path.join(mod44w_resgdb, "QA_{}".format(modtileid))
                if not arcpy.Exists(outQA):
                    print(outQA)
                    arcpy.ExtractSubDataset_management(in_raster=tile, out_raster=outQA, subdataset_index=1)
                mod44w_seltilesQA.append(outQA)

            #If multiple MODIS tiles intersect GLAD tile, mosaick them
            if len(mod44w_seltilesQA) > 1:
                mod44w_gladmatch = os.path.join(mod44w_resgdb, 'mod44wQA_gladmosaic{}'.format(gladtileid))
                if not arcpy.Exists(mod44w_gladmatch):
                    arcpy.MosaicToNewRaster_management(input_rasters=mod44w_seltilesQA,
                                                       output_location=os.path.split(mod44w_gladmatch)[0],
                                                       raster_dataset_name_with_extension=os.path.split(mod44w_gladmatch)[1],
                                                       number_of_bands=1,
                                                       mosaic_method='FIRST')
                    mod44w_mosaiclist.append(mod44w_gladmatch)

            #Otherwise, simply use the one MODIS tile
            else:
                mod44w_gladmatch = mod44w_seltilesQA[0]

        #If a MODIS mosaick already contains the GLAD tile, use that one
        else:
            mod44w_gladmatch = mod44w_seltiles[0]

        #Check whether there are any seawater pixels in MODIS within the extent of the GLAD tile
        print('Checking whether there are seawater pixels in MODIS within GLAD tile extent...')
        cliprec = project_extent(in_dataset=gladtile, out_coor_system=mod44w_gladmatch, out_dataset=None)
        modtileclip_out = os.path.join(mod44w_resgdb, 'modclip{}'.format(gladtileid))
        modtileclip = arcpy.Clip_management(in_raster=mod44w_gladmatch,
                                            rectangle="{0} {1} {2} {3}".format(
                                                cliprec.XMin, cliprec.YMin, cliprec.XMax, cliprec.YMax),
                                            out_raster=modtileclip_out)

        if not Raster(modtileclip).hasRAT and arcpy.Describe(modtileclip).bandCount == 1:  # Build attribute table if doesn't exist
            try:
                arcpy.BuildRasterAttributeTable_management(modtileclip)  # Does not work
            except Exception:
                e = sys.exc_info()[1]
                print(e.args[0])
                arcpy.DeleteRasterAttributeTable_management(modtileclip)

        mod44wvals = {row[0] for row in arcpy.da.SearchCursor(modtileclip, 'Value')}
        arcpy.Delete_management(modtileclip_out)

        # If there are sea pixels in MODIS, then create a seamask
        if 4 in mod44wvals and not arcpy.Exists(outseafinal):
            tic = time.time()
            create_GLADseamask(in_gladtile=gladtile,
                               in_mod44w=mod44w_gladmatch,
                               in_alositerator=alos_wgsextdict,
                               in_lakes=hydrolakes,
                               outpath=outseafinal,
                               processgdb=gladresgdb)
            print(time.time()-tic)
            gladtile = outseafinal
    else:
        print('{} already exists...'.format(outseafinal))

#---------------------------- Aggregate GLAD to match HydroSHEDS -----------------------------------------------------
#Check aggregation ratio
cellsize_ratio = arcpy.Describe(hydrotemplate).meanCellWidth / arcpy.Describe(rawtilelist[0]).meanCellWidth
print('Aggregating GLAD by cell size ratio of {0} would lead to a difference in resolution of {1} mm'.format(
    math.floor(cellsize_ratio),
    11100000 * (arcpy.Describe(hydrotemplate).meanCellWidth - math.floor(cellsize_ratio) * arcpy.Describe(
        rawtilelist[0]).meanCellWidth)
))
# Make sure that the cell size ratio is a multiple of the number of rows and columns in DEM tiles to not have edge effects
float(arcpy.Describe(rawtilelist[0]).height) / math.floor(cellsize_ratio)
float(arcpy.Describe(rawtilelist[0]).width) / math.floor(cellsize_ratio)

hysogagg_dict = {}
gladvalsdict = defaultdict(list)

for gladtile in rawtilelist:
    gladtileid = 'glad{}'.format(
        re.sub('(^.*class99_1[89]_)|([.]tif)', '', gladtile))  # Unique identifier for glad tile based on coordinates
    outseafinal = os.path.join(gladresgdb, '{}_seamask'.format(gladtileid))

    hysogagg_dict[gladtileid] = os.path.join(gladresgdb,
                                             '{0}_agg'.format(os.path.splitext(os.path.split(gladtile)[1])[0]))

    if arcpy.Exists(outseafinal):
        tiletoagg = outseafinal
    else:
        tiletoagg = gladtile

    print('Getting GLAD tile values')
    gladvalsdict[gladtileid] = list({row[0] for row in arcpy.da.SearchCursor(tiletoagg, 'Value')})
    vals = [v for v in gladvalsdict[gladtileid] if v not in [0, 12]]

    if not all(arcpy.Exists(os.path.join(gladresgdb, '{0}{1}'.format(hysogagg_dict[gladtileid], v))) for v in vals):
        # Divide and aggregate each band
        if compsr(tiletoagg, hydrotemplate):  # Make sure that share spatial reference with HydroSHEDS
            print('Divide {0} into {1} bands and aggregate by rounded value of {2}'.format(
                tiletoagg, len(vals), math.floor(cellsize_ratio)))
            catdiv_list = catdivagg_list(inras=tiletoagg,
                                         vals=gladvalsdict[gladtileid],
                                         exclude_list=[0, 12],
                                         aggratio=math.floor(cellsize_ratio))

            vals = [v for v in gladvalsdict[gladtileid] if v not in [0, 12]]
            for band in xrange(0, len(vals)):
                outband = os.path.join(gladresgdb, '{0}{1}'.format(hysogagg_dict[gladtileid], vals[band]))
                print('Saving {}'.format(outband))
                catdiv_list[band].save(outband)
    else:
        print('Bands have already been divided and aggregated for {0}'.format(gladtileid))

######################################## Mosaick GLAD tiles and resample ##################################

#Mosaick tiles for each value
outmosadict = {}
for val in xrange(1,12):
    tileref = getfilelist(gladresgdb, '^class99_19_.*_agg{0}$'.format(val))
    outmosadict[val] = os.path.join(gladresgdb, 'class99_19_agg{0}'.format(val))
    if not arcpy.Exists(outmosadict[val]):
        print('Processing {}...'.format(outmosadict[val]))
        arcpy.MosaicToNewRaster_management(tileref,
                                           output_location= os.path.split(outmosadict[val])[0],
                                           raster_dataset_name_with_extension= os.path.split(outmosadict[val])[1],
                                           pixel_type= '16_BIT_UNSIGNED',
                                           number_of_bands=1)

outrspdict = {}
for val in outmosadict:
    outrspdict[val] = os.path.join(gladresgdb, 'class99_19_rsp{0}'.format(val))
    if not arcpy.Exists(outrspdict[val]):
        print("Resampling to {}...".format(outrspdict[val]))
        # Resample with nearest cell assignment
        arcpy.env.extent = arcpy.env.snapRaster = arcpy.env.cellSize = arcpy.env.mask = hydrotemplate
        arcpy.Resample_management(in_raster=outmosadict[val],
                                  out_raster=outrspdict[val],
                                  cell_size=arcpy.env.cellSize,
                                  resampling_type='NEAREST')

#Compute statistics
#GLAD values mean the following
#0: NoData, 1: Land, 2: Permanent water, 3: Stable seasonal, 4: Water gain, 5: Water loss
#6: Dry period, 7: Wet period, 8: High frequency, 10: Probable land, 11: Probable water, 12: Sparse data - exclude

datapix = os.path.join(gladresgdb, 'class99_19_datapix')
freshpix = os.path.join(gladresgdb, 'class99_19_freshpix')
freshperc = os.path.join(gladresgdb, 'class99_19_freshperc')
waterpix = os.path.join(gladresgdb, 'class99_19_waterpix')
permperc = os.path.join(gladresgdb, 'class99_19_permperc')
seasonalperc = os.path.join(gladresgdb, 'class99_19_seasonalperc')
lossperc = os.path.join(gladresgdb, 'class99_19_lossperc')
dryperiodperc = os.path.join(gladresgdb, 'class99_19_dryperiodperc')
wetperiodperc = os.path.join(gladresgdb, 'class99_19_wetperiodperc')
hfreqperc = os.path.join(gladresgdb, 'class99_19_hfreqperc')

#Number of Non-NoData pixels
if not arcpy.Exists(datapix):
    print('Computing {}'.format(datapix))
    (sum([Con(IsNull(Raster(outrspdict[i])), 0, Raster(outrspdict[i])) for i in outrspdict])).save(datapix)


#Number of freshwater pixels (2-8 and 11)
if not arcpy.Exists(freshpix):
    print('Computing {}'.format(freshpix))
    (sum([Con(IsNull(Raster(outrspdict[i])), 0, Raster(outrspdict[i])) for i in xrange(1, 12) if i not in [1, 9, 10]])).\
        save(freshpix)

#Number of freshwater pixels/Non-Nodata pixels (percentage integer)
if not arcpy.Exists(freshperc):
    print('Computing {}'.format(freshperc))
    Con(datapix > 0,
        Int(0.5 + 100 * Raster(freshpix) / Float(Raster(datapix)))).save(freshperc)

#Number of water pixels (# freshwater pixels + 9)
if not arcpy.Exists(waterpix):
    print('Computing {}'.format(waterpix))
    (Raster(freshpix) + Con(IsNull(Raster(outrspdict[9])), 0, Raster(outrspdict[9]))).save(waterpix)


#### Compute water dynamics stats #####
def comp_dynaperc(in_dyna, in_freshpix, out_ras):
    Con(Raster(in_freshpix) > 0,
        Int(0.5 + (100 *
                   Con(IsNull(Raster(in_dyna)), 0, Raster(in_dyna)) / Float(Raster(in_freshpix))),
            )
        ).save(out_ras)

#Permanent + probable water
Con(Raster(freshpix) > 0,
    Int(0.5 + 100 * ((Con(IsNull(Raster(outrspdict[2])), 0, Raster(outrspdict[2])) +
                      Con(IsNull(Raster(outrspdict[11])), 0, Raster(outrspdict[11]))) / Float(Raster(freshpix))),
        )
    ).save(permperc)

comp_dynaperc(in_dyna=outrspdict[3], in_freshpix=freshpix, out_ras=seasonalperc) #Stable seasonal
comp_dynaperc(in_dyna=outrspdict[5], in_freshpix=freshpix, out_ras=lossperc) #Water loss
comp_dynaperc(in_dyna=outrspdict[6], in_freshpix=freshpix, out_ras=dryperiodperc) #Dry period
comp_dynaperc(in_dyna=outrspdict[7], in_freshpix=freshpix, out_ras=wetperiodperc) #Wet period
comp_dynaperc(in_dyna=outrspdict[8], in_freshpix=freshpix, out_ras=hfreqperc) #High frequency

#Compute statistics within buffer around river based on width


#Create 1.5 minute buffer around sea areas
coastalbuf3k = os.path.join(gladresgdb, 'class99_19_rsp9_buf3k')
EucAllocation(in_source_data=outrspdict[9], maximum_distance=0.0041666667*6).save(coastalbuf3k)