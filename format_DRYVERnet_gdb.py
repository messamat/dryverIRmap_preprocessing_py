import arcpy.management

from utility_functions_py3 import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

#Define paths
#Folder structure
rootdir = get_root_fromsrcdir()
datdir = os.path.join(rootdir, 'data')
resdir = os.path.join(rootdir, 'results')

process_gdb = os.path.join(resdir, 'extend_HydroRIVERS_process.gdb')
products_gdb = os.path.join(resdir, 'DRYVERnet.gdb')

#Input
dryver_netlinks = os.path.join(process_gdb, 'links_dryver_upao2_dis003')
dryver_netline = os.path.join(process_gdb, 'net_dryver_upao2_dis003')
dryver_netpourpoints_ras = os.path.join(process_gdb, 'net_dryver_upao2_dis003_pourpoints_ras')
dryver_netpourpoints = os.path.join(process_gdb, 'net_dryver_upao2_dis003_pourpoints')
dryver_netcatchments = os.path.join(process_gdb, 'net_dryver_upao2_dis003_catchments') #watershe

#Output
dryver_netlinks_format = os.path.join(products_gdb, 'dryvernet_link_ras')
dryver_netline_format = os.path.join(products_gdb, 'dryvernet')
dryver_netpourpoints_ras_format = os.path.join(products_gdb, 'dryvernet_prpt_ras')
dryver_netpourpoints_format = os.path.join(products_gdb, 'dryvernet_prpt')
dryver_netcatchments_format = os.path.join(products_gdb, 'dryvernet_cat_ras')
attri_tab = os.path.join(products_gdb, 'dryvernet_attri_tab')
dryver_netpourpoints_tab = os.path.join(resdir, 'dryvernet_pourpoints.csv')


#Copy
if not arcpy.Exists(dryver_netlinks_format):
    arcpy.management.CopyRaster(dryver_netlinks, dryver_netlinks_format)
if not arcpy.Exists(dryver_netline_format):
    arcpy.management.CopyFeatures(dryver_netline, dryver_netline_format)
if not arcpy.Exists(dryver_netpourpoints_ras_format):
    arcpy.management.CopyRaster(dryver_netpourpoints_ras, dryver_netpourpoints_ras_format)
if not arcpy.Exists(dryver_netpourpoints_format):
    arcpy.management.CopyFeatures(dryver_netpourpoints, dryver_netpourpoints_format)
if not arcpy.Exists(dryver_netcatchments_format):
    arcpy.management.CopyRaster(dryver_netcatchments, dryver_netcatchments_format)

#Format network lines
arcpy.management.DeleteField(dryver_netline_format, 'arcid')
arcpy.management.AlterField(dryver_netline_format, field='DRYVER_RIVID',
                            new_field_alias='DRYVER_RIVID')
arcpy.management.AddGeometryAttributes(dryver_netline_format,
                                       Geometry_Properties='LENGTH_GEODESIC',
                                       Length_Unit='METERS')

#Format attribute table
arcpy.management.AlterField(attri_tab, field='DRYVER_RIVID',
                            new_field_alias='DRYVER_RIVID')

#Format pourpoints
arcpy.management.AlterField(dryver_netpourpoints_format, field='DRYVER_RIVID', new_field_alias='DRYVER_RIVID')
arcpy.management.DeleteField(dryver_netpourpoints_format,
                             [f.name for f in arcpy.ListFields(dryver_netpourpoints_format)
                              if f.name not in [arcpy.Describe(dryver_netpourpoints_format).OIDFieldName,
                                           'DRYVER_RIVID', 'Shape']
                             ])
arcpy.management.AddGeometryAttributes(dryver_netpourpoints_format,
                                       Geometry_Properties='POINT_X_Y_Z_M')
if not arcpy.Exists(dryver_netpourpoints_tab):
    arcpy.management.CopyRows(dryver_netpourpoints_format, dryver_netpourpoints_tab)