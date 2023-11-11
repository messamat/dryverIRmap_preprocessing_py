import arcpy.management
from utility_functions_py3 import *

#Inputs
int_frac_eu_mean = os.path.join(resdir, 'model_predictions', '01_intermittency_frac_reaches_eu_new.shp')
int_frac_eu_200308 = os.path.join(resdir, 'model_predictions', 'all_reaches_eu_200308.shp')

for lyr in [int_frac_eu_mean, int_frac_eu_200308]:
    for da in [[0, 10], [10, 100], [100, 1000], [10**3,10**4], [10**4,10**5], [10**5,10**6]]:
        subriver_out = os.path.join(os.path.split(lyr)[0],
                                    '{0}_DA{1}_{2}.shp'.format(os.path.splitext(os.path.split(lyr)[1])[0],
                                                               re.sub('[.]', '', str(da[0])),
                                                               re.sub('[.]', '', str(da[1]))))
        if not arcpy.Exists(subriver_out):
            sqlexp = 'upa >= {0} AND upa <= {1}'.format(da[0], da[1])
            print('Processing {}...'.format(subriver_out))
            arcpy.MakeFeatureLayer_management(lyr, out_layer='subriver', where_clause=sqlexp)
            arcpy.CopyFeatures_management('subriver', subriver_out)
            arcpy.Delete_management('subriver')
