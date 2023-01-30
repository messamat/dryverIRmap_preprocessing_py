#Import libraries
import arcpy.management
import numpy as np
import pandas as pd

from utility_functions_py3 import *
from arcpy.sa import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

#Define paths
#Folder structure
rootdir = get_root_fromsrcdir()
datdir = os.path.join(rootdir, 'data')
resdir = os.path.join(rootdir, 'results')

#Input data from hydrosheds
hydrosheds_geometry_dir = os.path.join(datdir, 'HydroATLAS', 'HydroATLAS_Geometry')
landmask_hydrosheds = os.path.join(hydrosheds_geometry_dir, 'Masks', 'hydrosheds_landmask_15s.gdb', 'hys_land_15s')
flowdir_hydrosheds = os.path.join(hydrosheds_geometry_dir, 'Flow_directions' ,'flow_dir_15s_global.gdb', 'flow_dir_15s')
upa_hydrosheds = os.path.join(hydrosheds_geometry_dir, 'Accu_area_grids', 'upstream_area_skm_15s.gdb', 'up_area_skm_15s')
reaches_ras_hydrosheds = os.path.join(hydrosheds_geometry_dir, 'Link_zone_grids', 'link_stream.gdb', 'link_str_arc')
dis_nat_15s_hydrorivers = os.path.join(datdir, 'HydroATLAS', 'HydroATLAS_Data', 'Hydrology',
                                       'discharge_wg22_1971_2000.gdb', 'dis_nat_wg22_ls_year')

#Input data from dryver WP1
data_from_frankfurt_dir = os.path.join(datdir, 'data_from_frankfurt')
flowdir_dryver = os.path.join(data_from_frankfurt_dir, '09_modifiedflowdir', 'eurasia_dir_geq0_15s.tif')
flowacc_dryver = os.path.join(data_from_frankfurt_dir, '12_downscalingdata_eu', 'euassi_acc_15s.tif')
upa_dryver = os.path.join(data_from_frankfurt_dir, '12_downscalingdata_eu', 'euassi_upa_15s.tif')
dis_nat_15s_dryver = os.path.join(data_from_frankfurt_dir, 'WaterGAP_mean_1981to2019.tif')

#Input data about DRNs (official two-letter country code prefix hr: Croatia)
drn_dir = os.path.join(data_from_frankfurt_dir, '08_finaldrnrivernetwork', 'riv_network', 'River_networks_for_J2000')

cz_drn_net = os.path.join(drn_dir, 'Morava_CzechRepublic', 'streamsMorava.shp')
es_drn_net = os.path.join(drn_dir, 'Guadiaro_Spain' ,'streamsGuadiaro.shp')
fi_drn_net = os.path.join(drn_dir, 'Vantaanjoki_Finland', 'river_network_reference.shp')
fr_drn_net = os.path.join(drn_dir, 'Ain_France', 'river_network_reference_Ain.shp')
hr_drn_net = os.path.join(drn_dir, 'Krka_Croatia' , 'streamsKrka.shp')
hu_drn_net = os.path.join(drn_dir, 'Fekete_Hungary', 'river_network_reference.shp')

drn_dict = {'cz': cz_drn_net, 'es': es_drn_net, 'fi': fi_drn_net,
            'fr': fr_drn_net, 'hr': hr_drn_net, 'hu': hu_drn_net}

#Create processing and products geodatabases
process_gdb = os.path.join(resdir, 'extend_HydroRIVERS_process.gdb')
pathcheckcreate(path=process_gdb, verbose=True)

#Output layers
flowdir_diff_hydrosheds_vs_dryver = os.path.join(process_gdb, 'flowdir_diff_hydrosheds_vs_dryver')
reaches_ras_hydrosheds_euassiclip = os.path.join(process_gdb, 'link_str_arc_hydrosheds_euassiclip')

dis_nat_dryver_u01o001 = os.path.join(process_gdb, 'dis_nat_dryver_u01o001')
dis_nat_dryver_u01o002 = os.path.join(process_gdb, 'dis_nat_dryver_u01o002')
dis_nat_dryver_u01o003 = os.path.join(process_gdb, 'dis_nat_dryver_u01o003')
dis_nat_dryver_u01o005 = os.path.join(process_gdb, 'dis_nat_dryver_u01o005')
upa_dryver_u10o2 = os.path.join(process_gdb, 'upa_dryver_u10o2')
upa_dryver_u10o1 = os.path.join(process_gdb, 'upa_dryver_u10o1')

drn_firstorder_midupa_tab = os.path.join(resdir, 'drn_firstorder_mid_upstreamarea_percentiles.csv')
drn_firstorder_middis_tab = os.path.join(resdir, 'drn_firstorder_mid_discharge_percentiles.csv')

dryver_netras = os.path.join(process_gdb, 'netras_dryver_upao2_dis003')
dryver_netlinks = os.path.join(process_gdb, 'links_dryver_upao2_dis003')
dryver_netline = os.path.join(process_gdb, 'net_dryver_upao2_dis003')
dryver_netpourpoints_ras = os.path.join(process_gdb, 'net_dryver_upao2_dis003_pourpoints_ras')
dryver_netpourpoints = os.path.join(process_gdb, 'net_dryver_upao2_dis003_pourpoints')
dryver_netcatchments = os.path.join(process_gdb, 'net_dryver_upao2_dis003_catchments') #watershe

dryver_netras_upa01_dis003 = os.path.join(process_gdb, 'netras_dryver_upao1_dis003')
dryver_netlinks_upa01_dis003 = os.path.join(process_gdb, 'links_dryver_upa01_dis003')

#Set environment
arcpy.env.extent = arcpy.env.snapRaster = dis_nat_15s_dryver

#Assess differences in flow direction performed by Tim
if not arcpy.Exists(flowdir_diff_hydrosheds_vs_dryver):
    Con(Raster(flowdir_hydrosheds) != Raster(flowdir_dryver), 1, 0).save(flowdir_diff_hydrosheds_vs_dryver)

#Count number of reaches in HydroRIVERS in the desired extent
if not arcpy.Exists(reaches_ras_hydrosheds_euassiclip):
    fdir_ext = arcpy.Describe(flowdir_dryver).Extent
    arcpy.management.Clip(in_raster = reaches_ras_hydrosheds,
                          rectangle = f"{fdir_ext.XMin} {fdir_ext.YMin} {fdir_ext.XMax} {fdir_ext.YMax}",
                          out_raster = reaches_ras_hydrosheds_euassiclip,
                          in_template_dataset = flowdir_dryver
                          )

if not Raster(reaches_ras_hydrosheds_euassiclip).hasRAT:
    arcpy.management.BuildRasterAttributeTable(in_raster = reaches_ras_hydrosheds_euassiclip)
arcpy.management.GetRasterProperties(in_raster = reaches_ras_hydrosheds_euassiclip,
                                     property_type = 'UNIQUEVALUECOUNT')

#Create raster of cells with watergap downscaled discharge between 0.1 m3/s and 0.01 m3/s
if not arcpy.Exists(dis_nat_dryver_u01o001):
    Con((Raster(dis_nat_15s_dryver) >= 0.01) & (Raster(dis_nat_15s_dryver) < 0.1), 1, 0).save(dis_nat_dryver_u01o001)

if not arcpy.Exists(dis_nat_dryver_u01o002):
    Con((Raster(dis_nat_15s_dryver) >= 0.02) & (Raster(dis_nat_15s_dryver) < 0.1), 1, 0).save(dis_nat_dryver_u01o002)

if not arcpy.Exists(dis_nat_dryver_u01o003):
    Con((Raster(dis_nat_15s_dryver) >= 0.03) & (Raster(dis_nat_15s_dryver) < 0.1), 1, 0).save(dis_nat_dryver_u01o003)

if not arcpy.Exists(dis_nat_dryver_u01o005):
    Con((Raster(dis_nat_15s_dryver) >= 0.05) & (Raster(dis_nat_15s_dryver) < 0.1), 1, 0).save(dis_nat_dryver_u01o005)

#Create raster of cells with upstream area (based on modified direction raster) between 10 km2 and 2 km2
if not arcpy.Exists(upa_dryver_u10o2):
    Con((Raster(upa_dryver) >= 2) & (Raster(upa_dryver) < 10), 1, 0).save(upa_dryver_u10o2)

if not arcpy.Exists(upa_dryver_u10o1):
    Con((Raster(upa_dryver) >= 1) & (Raster(upa_dryver) < 10), 1, 0).save(upa_dryver_u10o1)

#For each DRN, get the pour point of all first order streams
drn_dangle_dict = {}
drn_mids_dict = {}

drn_firstorder_midupa_dict ={}
drn_firstorder_middis_dict ={}

drn_firstorder_mid_dict = {}

for country, drn_net_path in drn_dict.items():
    drn_dangle_dict[country] = os.path.join(process_gdb, f"{country}_drn_net_dangles")

    if not arcpy.Exists(drn_dangle_dict[country]):
        print(f'Producing dangle points for {drn_net_path}...')
        arcpy.management.FeatureVerticesToPoints(in_features = drn_net_path,
                                                 out_feature_class = drn_dangle_dict[country],
                                                 point_location = 'DANGLE'
                                                 )
    else:
        print(f"{drn_dangle_dict[country]} already exists. Skipping...")

    out_mids = os.path.join(process_gdb, f"{country}_drn_net_mids")
    drn_firstorder_mid_dict[country] = os.path.join(process_gdb, f"{country}_drn_firstordernet_mids")

    if not arcpy.Exists(drn_firstorder_mid_dict[country]):
        print(f'Producing first order mid points for {drn_net_path}...')
        arcpy.management.FeatureVerticesToPoints(in_features=drn_net_path,
                                                 out_feature_class=out_mids,
                                                 point_location='MID'
                                                 )
        arcpy.management.AddJoin(out_mids, 'ORIG_FID',
                                 drn_dangle_dict[country], 'ORIG_FID',
                                 join_type = 'KEEP_COMMON')

        arcpy.management.CopyFeatures(out_mids, drn_firstorder_mid_dict[country])

        # For each DRN, analyze the distribution of upstream area and WaterGAP discharge of the pourpoint of all first order streams
        print(f'Extracting the upstream area and watergap discharge for {drn_firstorder_mid_dict[country]}...')
        ExtractMultiValuesToPoints(in_point_features = drn_firstorder_mid_dict[country],
                                   in_rasters = [[Raster(upa_dryver), 'mid_upa_km2'],
                                                 [Raster(dis_nat_15s_dryver), 'mid_dis_nat_15s']],
                                   bilinear_interpolate_values = 'NONE')
    else:
        print(f"{drn_firstorder_mid_dict[country]} already exists. Skipping...")

    drn_firstorder_midupa_dict[country] = np.percentile([row[0] for row in
                                                 arcpy.da.SearchCursor(drn_firstorder_mid_dict[country], 'mid_upa_km2')],
                                             range(0, 100, 5))
    drn_firstorder_middis_dict[country] = np.percentile([row[0] for row in
                                                  arcpy.da.SearchCursor(drn_firstorder_mid_dict[country], 'mid_dis_nat_15s')],
                                             range(0, 100, 5))

if not arcpy.Exists(drn_firstorder_midupa_tab):
    pd.DataFrame.from_dict(drn_firstorder_midupa_dict, orient='columns').to_csv(drn_firstorder_midupa_tab)
if not arcpy.Exists(drn_firstorder_middis_tab):
    pd.DataFrame.from_dict(drn_firstorder_middis_dict, orient='columns').to_csv(drn_firstorder_middis_tab)


for country, path in drn_firstorder_mid_dict.items():
    minupa_km2 = 10
    mindis_m3s = 0.1
    print(country)
    all_count = arcpy.management.GetCount(path)[0]
    sel_count = arcpy.management.GetCount(
        arcpy.MakeFeatureLayer_management(path, out_layer = 'test_sel',
                                      where_clause = f'mid_upa_km2 >= {minupa_km2} AND mid_dis_nat_15s >= {mindis_m3s}')
    )[0]
    print(f'Initiating streams when upstream area is at least {minupa_km2} km2 '
          f'and mean annual discharge is at least {mindis_m3s} m3/s \n includes the middle point of'
          f' {np.round(100*int(sel_count)/int(all_count))}% of first order streams in {country}')

#Create raster of new reaches
if not arcpy.Exists(dryver_netras):
    Con(((Raster(upa_dryver) >= 2) | (Raster(dis_nat_15s_dryver) >= 0.03)), 1, 0).save(dryver_netras)

if not arcpy.Exists(dryver_netras_upa01_dis003):
    Con(((Raster(upa_dryver) >= 1) | (Raster(dis_nat_15s_dryver) >= 0.03)), 1, 0).save(dryver_netras_upa01_dis003)

#Create stream links
if not arcpy.Exists(dryver_netlinks):
    StreamLink(in_stream_raster = dryver_netras,
               in_flow_direction_raster=flowdir_dryver).save(dryver_netlinks)

if not arcpy.Exists(dryver_netlinks_upa01_dis003):
    StreamLink(in_stream_raster = dryver_netras_upa01_dis003,
               in_flow_direction_raster=flowdir_dryver).save(dryver_netlinks_upa01_dis003)

if not Raster(dryver_netlinks_upa01_dis003).hasRAT:
    arcpy.management.BuildRasterAttributeTable(in_raster = dryver_netlinks_upa01_dis003)
arcpy.management.GetRasterProperties(in_raster = dryver_netlinks_upa01_dis003,
                                     property_type = 'UNIQUEVALUECOUNT')

#Create network polylines
if not arcpy.Exists(dryver_netline):
    StreamToFeature(in_stream_raster = dryver_netlinks,
                    in_flow_direction_raster = flowdir_dryver,
                    out_polyline_features = dryver_netline,
                    simplify = 'NO_SIMPLIFY')
#arcpy.management.GetCount(dryver_netline)[0]

#Create pourpoint raster for extraction
if not arcpy.Exists(dryver_netpourpoints_ras):
    link_maxacc = os.path.join(process_gdb, 'links_dryver_upao2_dis003_maxacc')
    ZonalStatistics(in_zone_data=dryver_netlinks, zone_field='Value', in_value_raster=flowacc_dryver,
                    statistics_type='MAXIMUM', ignore_nodata='DATA').save(
        link_maxacc)
    Con(Raster(link_maxacc) == Raster(flowacc_dryver), dryver_netlinks).save(dryver_netpourpoints_ras)

#Create pourpoint point feature class
if not arcpy.Exists(dryver_netpourpoints):
    arcpy.conversion.RasterToPoint(in_raster = dryver_netpourpoints_ras,
                                   out_point_features = dryver_netpourpoints,
                                   raster_field = 'Value')

#Create catchments
if not arcpy.Exists(dryver_netcatchments):
    Watershed(in_flow_direction_raster=flowdir_dryver,
              in_pour_point_data=dryver_netpourpoints_ras,
              pour_point_field='Value').save(dryver_netcatchments)

