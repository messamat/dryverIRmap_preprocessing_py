import arcpy.management

from utility_functions_py3 import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

#Define paths
#Folder structure
rootdir = get_root_fromsrcdir()
datdir = os.path.join(rootdir, 'data')
resdir = os.path.join(rootdir, 'results')

hydrosheds_geometry_dir = os.path.join(datdir, 'HydroATLAS', 'HydroATLAS_Geometry')
landmask_hydrosheds = os.path.join(hydrosheds_geometry_dir, 'Masks', 'hydrosheds_landmask_15s.gdb', 'hys_land_15s')

HydroATLAS_datdir = os.path.join(datdir, 'HydroATLAS', 'HydroATLAS_Data')

data_from_frankfurt_dir = os.path.join(datdir, 'data_from_frankfurt')
dis_nat_15s_dryver = os.path.join(data_from_frankfurt_dir, 'WaterGAP_mean_1981to2019.tif')
karstpoly = os.path.join(datdir, 'poly_shp_abbasi20221124', 'whymap_karst__v1_poly.shp')

data_from_frankfurt_dir = os.path.join(datdir, 'data_from_frankfurt')
flowdir_dryver = os.path.join(data_from_frankfurt_dir, '09_modifiedflowdir', 'eurasia_dir_geq0_15s.tif')
upa_dryver = os.path.join(data_from_frankfurt_dir, '12_downscalingdata_eu', 'euassi_upa_15s.tif')
pxarea_15s_dryver = os.path.join(data_from_frankfurt_dir, '12_downscalingdata_eu', 'euassi_pixarea_15s.tif')

statpredgdb = os.path.join(resdir, 'static_predictors', 'static_predictors.gdb')

karstras = os.path.join(statpredgdb, "whymap_karst_v1_ras15s")
karstras_bool = os.path.join(statpredgdb, 'whymap_karst_v1_ras15s_bool')

worldpop_dens = os.path.join(resdir, 'static_predictors', 'worldpop.gdb', 'wp_mosaicked')
wp_filled = os.path.join(resdir, 'static_predictors', 'worldpop.gdb', 'wp_filled')

carbon_raw = os.path.join(HydroATLAS_datdir, 'Soils', 'soil_grids_1km_nodata_org.gdb', 'carbon_tha_nodata')
carbon_filled = os.path.join(statpredgdb, 'carbon_tha_zeros')

grand_mcm = os.path.join(datdir, 'HydroATLAS', 'HydroATLAS_Data', 'Hydrology',
                         'reservoirs_grand_v11.gdb', 'grand_cap_mcm_x10_pour') #SUM
dor_pc_va = os.path.join(statpredgdb, 'dor_pc_pva')
dis_nat_mcm = os.path.join(resdir, 'scratch.gdb','dis_nat_mcm')

#Set environment
arcpy.env.extent = arcpy.env.snapRaster = dis_nat_15s_dryver

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ TRANSFER UPSTREAM DRAINAGE AREA ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
arcpy.management.CopyRaster(upa_dryver,
                            os.path.join(statpredgdb, os.path.splitext(os.path.split(upa_dryver)[1])[0]))

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ WHYMAP KARST ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#Convert to raster
if not arcpy.Exists(karstras):
    arcpy.conversion.PolygonToRaster(in_features=karstpoly,
                                     value_field='rock_type',
                                     out_rasterdataset=karstras,
                                     cellsize = dis_nat_15s_dryver)

#Create boolean raster
if not arcpy.Exists(karstras_bool):
    Con(~IsNull(Raster(landmask_hydrosheds)) & ~IsNull(Raster(karstras)), 100, 0).save(karstras_bool)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Format GRAND volume ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
cap_acc = os.path.join(resdir, 'scratch.gdb','grand_cap_acc')
FlowAccumulation(in_flow_direction_raster=flowdir_dryver,
                 in_weight_raster=Raster(grand_mcm),
                 data_type="INTEGER").save(cap_acc)

(Raster(dis_nat_15s_dryver)*0.31536).save(dis_nat_mcm)
grand_dor = Int(Divide(Raster(cap_acc), Raster(dis_nat_mcm))+0.5).save(dor_pc_va) #Result will be 10*%. A value of 10 will mean 1%.

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Format worldpop ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
if not arcpy.Exists(wp_filled):
    Con(IsNull(worldpop_dens), 0, worldpop_dens).save(wp_filled)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Format soil organic carbon ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
if not arcpy.Exists(carbon_filled):
    Con(IsNull(carbon_raw), 0, carbon_raw).save(carbon_filled)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Accumulate predictors ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
raslist_to_accumulate = \
    [karstras_bool,
     os.path.join(HydroATLAS_datdir, 'Landcover', 'irrigation_gmia.gdb', 'gmia_equipped_ext_pc_x100'),
     wp_filled,
     os.path.join(HydroATLAS_datdir, 'Landcover', 'agriculture_earthstat.gdb', 'cropland_ext_pc_x100'),
     os.path.join(HydroATLAS_datdir, 'Landcover', 'agriculture_earthstat.gdb', 'pasture_ext_pc_x100'),
     carbon_filled,
    os.path.join(HydroATLAS_datdir, 'Demography', 'urban_areas_ghs_v2016.gdb', 'ghs_smod_2015_urb_ext_pc'),
] + \
      [os.path.join(HydroATLAS_datdir,'Landcover', 'landcover_glc2000_by_class.gdb',
                    f'glc2000_ext_bin_cl{str(cl).zfill(2)}') for cl in range(1, 23)] +\
  [os.path.join(resdir, 'static_predictors', 'gai3.db',
                f'ai3_{str(m).zfill(2)}_nib') for m in range(1, 13)]

for ras in raslist_to_accumulate:
    hydroUplandWeighting(value_grid=ras,
                         direction_grid=flowdir_dryver,
                         weight_grid=pxarea_15s_dryver,
                         upland_grid=upa_dryver,
                         scratch_dir=os.path.join(resdir, 'scratch.gdb'),
                         out_dir=statpredgdb,
                         shiftval=0)





