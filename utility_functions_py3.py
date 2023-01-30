import arcpy
from arcpy.sa import *
from inspect import getsourcefile
import os
import re
import sys

#Get current root directory
def get_root_fromsrcdir():
    return(os.path.dirname(os.path.abspath(
        getsourcefile(lambda:0)))).split('\\src')[0]

def pathcheckcreate(path, verbose=True):
    """"Function that takes a path as input and:
      1. Checks which directories and .gdb exist in the path
      2. Creates the ones that don't exist"""

    dirtocreate = []
    # Loop upstream through path to check which directories exist, adding those that don't exist to dirtocreate list
    while not os.path.exists(os.path.join(path)):
        dirtocreate.append(os.path.split(path)[1])
        path = os.path.split(path)[0]

    dirtocreate.reverse()

    # After reversing list, iterate through directories to create starting with the most upstream one
    for dir in dirtocreate:
        # If gdb doesn't exist yet, use arcpy method to create it and then stop the loop to prevent from trying to create anything inside it
        if os.path.splitext(dir)[1] == '.gdb':
            if verbose:
                print('Create {}...'.format(dir))
            arcpy.management.CreateFileGDB(out_folder_path=path,
                                           out_name=dir)
            break

        # Otherwise, if it is a directory name (no extension), make a new directory
        elif os.path.splitext(dir)[1] == '':
            if verbose:
                print('Create {}...'.format(dir))
            path = os.path.join(path, dir)
            os.mkdir(path)

#Get all files in a ArcGIS workspace (file or personal GDB)
def getwkspfiles(dir, repattern=None):
    arcpy.env.workspace = dir
    filenames_list = (arcpy.ListDatasets() or []) +\
                     (arcpy.ListTables() or []) +\
                     (arcpy.ListFeatureClasses() or []) # Either LisDatsets or ListTables may return None so need to create empty list alternative
    if not repattern == None:
        filenames_list = [filen for filen in filenames_list if re.search(repattern, filen)]

    return ([os.path.join(dir, f) for f in filenames_list])
    arcpy.ClearEnvironment('workspace')

def getfilelist(dir, repattern=None, gdbf=True, nongdbf=True, fullpath=False):
    """Function to iteratively go through all subdirectories inside 'dir' path
    and retrieve path for each file that matches "repattern"
    gdbf and nongdbf allows the user to choose whether to consider ArcGIS workspaces (GDBs) or not or exclusively"""

    try:
        if arcpy.Describe(dir).dataType == 'Workspace':
            if gdbf == True:
                print('{} is ArcGIS workspace...'.format(dir))
                filenames_list = getwkspfiles(dir, repattern)
            else:
                raise ValueError(
                    "A gdb workspace was given for dir but gdbf=False... either change dir or set gdbf to True")
        else:
            filenames_list = []

            if gdbf == True:
                for (dirpath, dirnames, filenames) in os.walk(dir):
                    for in_dir in dirnames:
                        fpath = os.path.join(dirpath, in_dir)
                        if arcpy.Describe(fpath).dataType == 'Workspace':
                            print('{} is ArcGIS workspace...'.format(fpath))
                            filenames_list.extend(getwkspfiles(dir=fpath, repattern=repattern))
            if nongdbf == True:
                for (dirpath, dirnames, filenames) in os.walk(dir):
                    for file in filenames:
                        if repattern is None:
                            filenames_list.append(os.path.join(dirpath, file))
                        else:
                            if re.search(repattern, file):
                                filenames_list.append(os.path.join(dirpath, file))
        return (filenames_list)

    # Return geoprocessing specific errors
    except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessages(2))
    # Return any other type of error
    except:
        # By default any other errors will be caught here
        e = sys.exc_info()[1]
        print(e.args[0])

def fast_joinfield(in_data, in_field, join_table, join_field, fields, round=False):
    in_data_fields = [f.name for f in arcpy.ListFields(in_data)]
    join_table_ftypes = {f.name: f.type for f in arcpy.ListFields(join_table)}

    for f in fields:
        fname_orig = f[0]  # Field name in join_table
        fname_dest = f[1]  # Field name in destination table (in_data)
        print(f'Adding {fname_orig} from {os.path.basename(join_table)} as {fname_dest} to {os.path.basename(in_data)}')

        if fname_dest in in_data_fields:
            print(f'{fname_dest} is already in the attribute table of {in_data}')
        else:
            #Build dictionary of all values to join
            val_dict = {row[0]: row[1] for row in arcpy.da.SearchCursor(join_table, [join_field, fname_orig])}

            #Determine output field type
            if (round==False) or (join_table_ftypes[fname_orig] in ["Integer", "SmallInteger"]):
                ftype_dest = join_table_ftypes[fname_orig]
            else:
                ftype_dest = 'LONG' if ((max(val_dict) > 32767) or (min(val_dict) < -32767)) else 'SHORT'

            #Create field in destination table
            arcpy.management.AddField(in_table=in_data,
                                      field_name=fname_dest,
                                      field_type=ftype_dest)

            print('Writing in attri_tab')
            with arcpy.da.UpdateCursor(in_data, [in_field, fname_dest]) as cursor:
                for row in cursor:
                    row[1] = val_dict[row[0]]
                    cursor.updateRow(row)


# Use all of the cores on the machine.
def set_environment(workspace, mask_layer):
    arcpy.CheckOutExtension("spatial")
    arcpy.env.cellSize = mask_layer
    arcpy.env.extent = mask_layer
    arcpy.env.workspace = workspace
    arcpy.overwriteOutputs = True
    arcpy.env.overwriteOutput = True

def hydroUplandWeighting(value_grid, direction_grid, weight_grid, upland_grid, scratch_dir,
                        out_dir, shiftval=0, overwrite=False):
    #Check that directories exist, otherwise, create them
    pathcheckcreate(scratch_dir)
    pathcheckcreate(out_dir)
    arcpy.env.scratchWorkspace = scratch_dir

    #UPLAND WEIGHT GRID
    nameroot = os.path.splitext(os.path.split(value_grid)[1])[0]
    out_grid = os.path.join(out_dir, '{}_acc'.format(nameroot))
    xpxarea = os.path.join(out_dir, '{}_xpxarea'.format(nameroot))
    xpxarea_ac1 = os.path.join(out_dir, '{}_xpxarea_ac1'.format(nameroot))
    xpxarea_ac_fin = os.path.join(out_dir, '{}_xpxarea_ac_fin'.format(nameroot))

    if (not arcpy.Exists(out_grid)) or (overwrite == True):
        try:
            set_environment(out_dir, direction_grid)

            # Multiply input grid by pixel area
            print('Processing {}...'.format(xpxarea))
            valueXarea = Times(Raster(value_grid) + float(shiftval), Raster(weight_grid))
            valueXarea.save(xpxarea)

            # Flow accumulation of value grid and pixel area product
            print('Processing {}...'.format(xpxarea_ac1))
            outFlowAccumulation = FlowAccumulation(direction_grid, Raster(xpxarea), "FLOAT")
            outFlowAccumulation.save(xpxarea_ac1)

            print('Processing {}...'.format(xpxarea_ac_fin))
            outFlowAccumulation_2 = Plus(xpxarea_ac1, xpxarea)
            outFlowAccumulation_2.save(xpxarea_ac_fin)

            # Divide by the accumulated pixel area grid
            print('Processing {}...'.format(out_grid))
            UplandGrid = (Divide(xpxarea_ac_fin, upland_grid)-shiftval)
            UplandGrid.save(out_grid)

        except Exception:
            e = sys.exc_info()[1]
            print(e.args[0])
            arcpy.AddError(e.args[0])

        print('Deleting intermediate grids...')
        for lyr in [xpxarea, xpxarea_ac1, xpxarea_ac_fin]:
            if arcpy.Exists(lyr):
                arcpy.management.Delete(lyr)
    else:
        print('{} already exists and overwrite==False...'.format(out_grid))
