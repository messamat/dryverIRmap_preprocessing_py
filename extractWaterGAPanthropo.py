from utility_functions import *

arcpy.CheckOutExtension('Spatial')
arcpy.env.overwriteOutput = True

# Use all of the cores on the machine
arcpy.env.parallelProcessingFactor = "100%"

if __name__ == '__main__':
    hydrodir = os.path.join(datdir, "Bernhard/HydroATLAS")
    pourpoints_location = os.path.join(hydrodir, 'HydroATLAS_Geometry', 'Link_zone_grids',
                                       'link_stream.gdb', 'link_str_pnt')
    linkhyriv = os.path.join(hydrodir, 'HydroATLAS_Geometry', 'Link_shapefiles', 'link_hyriv_v10.gdb', 'link_hyriv_v10')
    dis_grid = os.path.join(hydrodir, 'HydroATLAS_Data', 'Hydrology', 'discharge_wg22_1971_2000.gdb', 'dis_ant_wg22_ls_year')
    out_ztab = os.path.join(resdir, "RiverATLAS_v11_dis_ant_year")
    out_csvtab = "{0}.csv".format(out_ztab)

    if not arcpy.Exists(out_csvtab):
        ZonalStatisticsAsTable(in_zone_data= pourpoints_location, zone_field= 'Value',
                               in_value_raster= dis_grid,
                               out_table = out_ztab,
                               ignore_nodata= 'DATA', statistics_type='MEAN')

        linkdict = {row[0]: row[1] for row in arcpy.da.SearchCursor(linkhyriv, ['LINK_RIV', 'HYRIV_ID'])}
        arcpy.AddField_management(out_ztab, 'HYRIV_ID', 'LONG')
        with arcpy.da.UpdateCursor(out_ztab, ['VALUE', 'HYRIV_ID']) as cursor:
            for row in cursor:
                row[1] = linkdict[row[0]]
                cursor.updateRow(row)
        arcpy.CopyRows_management(out_ztab, out_csvtab)
        arcpy.Delete_management(out_ztab)






