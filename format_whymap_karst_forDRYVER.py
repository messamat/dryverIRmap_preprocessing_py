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

statpredgdb = os.path.join(resdir, 'DryverIRmodel_static_predictors_forMahdi_20221122', 'static_predictors.gdb')

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
