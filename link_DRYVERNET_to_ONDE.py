import arcpy.management

from utility_functions_py3 import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

#Define paths
#Folder structure
rootdir = get_root_fromsrcdir()
datdir = os.path.join(rootdir, 'data')
resdir = os.path.join(rootdir, 'results')

raw_net_gdb = os.path.join(resdir, 'DRYVERnet.gdb')
process_gdb = os.path.join(resdir, 'extend_HydroRIVERS_process.gdb')

#Input
dryver_netline = os.path.join(raw_net_gdb, 'dryvernet')
dryver_link_ras = os.path.join(raw_net_gdb, 'dryvernet_link_ras')

hydrorivers = os.path.join(datdir, 'HydroATLAS', 'HydroRIVERS_v10_final_data', 'geodatabases',
                           'HydroRIVERS_v10.gdb', 'HydroRIVERS_v10')
hydrosheds_geometry_dir = os.path.join(datdir, 'HydroATLAS', 'HydroATLAS_Geometry')
flowdir_hydrosheds = os.path.join(hydrosheds_geometry_dir, 'Flow_directions' ,'flow_dir_15s_global.gdb', 'flow_dir_15s')

#Outputs
hydrorivers_ras = os.path.join(process_gdb, 'hyriv_id_ras')
hyriv_dryver_match = os.path.join(process_gdb, 'hyriv_dryver_match')

#Convert HYdroRIVERS_v10 to raster with same specs as dryvernet
if not arcpy.Exists(hydrorivers_ras):
    arcpy.env.extent = arcpy.env.snapRaster = dryver_link_ras
    arcpy.PolylineToRaster_conversion(in_features=hydrorivers,
                                      value_field="HYRIV_ID",
                                      out_rasterdataset=hydrorivers_ras,
                                      cellsize =dryver_link_ras
                                      )

#Zonal statistics with DRYVER_NET links
if not arcpy.Exists(hyriv_dryver_match):
    ZonalStatisticsAsTable(in_zone_data=dryver_link_ras,
                           zone_field='Value',
                           in_value_raster=hydrorivers_ras,
                           out_table=hyriv_dryver_match,
                           statistics_type='MAJORITY')


