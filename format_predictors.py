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

data_from_frankfurt_dir = os.path.join(datdir, 'data_from_frankfurt')
dis_nat_15s_dryver = os.path.join(data_from_frankfurt_dir, 'WaterGAP_mean_1981to2019.tif')
karstpoly = os.path.join(datdir, 'poly_shp_abbasi20221124', 'whymap_karst__v1_poly.shp')

data_from_frankfurt_dir = os.path.join(datdir, 'data_from_frankfurt')
flowdir_dryver = os.path.join(data_from_frankfurt_dir, '09_modifiedflowdir', 'eurasia_dir_geq0_15s.tif')
upa_dryver = os.path.join(data_from_frankfurt_dir, '12_downscalingdata_eu', 'euassi_upa_15s.tif')
pxarea_15s_dryver = os.path.join(data_from_frankfurt_dir, '12_downscalingdata_eu', 'euassi_pixarea_15s.tif')

statpredgdb = os.path.join(resdir, 'static_predictors', 'static_predictors.gdb')

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ WHYMAP KARST ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#Output
karstras = os.path.join(statpredgdb, "whymap_karst_v1_ras15s")
karstras_bool = os.path.join(statpredgdb, 'whymap_karst_v1_ras15s_bool')

#Set environment
arcpy.env.extent = arcpy.env.snapRaster = dis_nat_15s_dryver

#Convert to raster
if not arcpy.Exists(karstras):
    arcpy.conversion.PolygonToRaster(in_features=karstpoly,
                                     value_field='rock_type',
                                     out_rasterdataset=karstras,
                                     cellsize = dis_nat_15s_dryver)

#Create boolean raster
if not arcpy.Exists(karstras_bool):
    Con(~IsNull(Raster(landmask_hydrosheds)) & ~IsNull(Raster(karstras)), 100, 0).save(karstras_bool)

#Run flow accumulation
hydroUplandWeighting(value_grid=karstras_bool,
                     direction_grid=flowdir_dryver,
                     weight_grid=pxarea_15s_dryver,
                     upland_grid=upa_dryver,
                     scratch_dir=os.path.join(resdir, 'scratch.gdb'),
                     out_dir=statpredgdb,
                     shiftval=0)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Accumulate anthropogenic predictors ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
gmia_pc = os.path.join(datdir, 'HydroATLAS', 'HydroATLAS_Data', 'Landcover', 'irrigation_gmia.gdb', 'gmia_equipped_ext_pc_x100') #MEAN
worldpop_dens = os.path.join(resdir, 'static_predictors', 'worldpop.gdb', 'wp_mosaicked')

arcpy.env.extent = arcpy.env.snapRaster = dis_nat_15s_dryver


hydroUplandWeighting(value_grid=gmia_pc,
                     direction_grid=flowdir_dryver,
                     weight_grid=pxarea_15s_dryver,
                     upland_grid=upa_dryver,
                     scratch_dir=os.path.join(resdir, 'scratch.gdb'),
                     out_dir=statpredgdb,
                     shiftval=0)

#Run flow accumulation for world pop
wp_filled = os.path.join(resdir, 'static_predictors', 'worldpop.gdb', 'wp_filled')
Con(IsNull(worldpop_dens), 0, worldpop_dens).save(wp_filled)
hydroUplandWeighting(value_grid=wp_filled,
                     direction_grid=flowdir_dryver,
                     weight_grid=pxarea_15s_dryver,
                     upland_grid=upa_dryver,
                     scratch_dir=os.path.join(resdir, 'scratch.gdb'),
                     out_dir=statpredgdb,
                     shiftval=0)

#Format GRAND volume
grand_mcm = os.path.join(datdir, 'HydroATLAS', 'HydroATLAS_Data', 'Hydrology', 'reservoirs_grand_v11.gdb', 'grand_cap_mcm_x10_pour') #SUM
dor_pc_va = os.path.join(statpredgdb, 'dor_pc_pva')

cap_acc = os.path.join(resdir, 'scratch.gdb','grand_cap_acc')
FlowAccumulation(in_flow_direction_raster=flowdir_dryver,
                 in_weight_raster=Raster(grand_mcm),
                 data_type="INTEGER").save(cap_acc)

dis_nat_mcm = os.path.join(resdir, 'scratch.gdb','dis_nat_mcm')
(Raster(dis_nat_15s_dryver)*0.31536).save(dis_nat_mcm)
grand_dor = Int(Divide(Raster(cap_acc), Raster(dis_nat_mcm))+0.5).save(dor_pc_va) #Result will be 10*%. A value of 10 will mean 1%.




