import arcpy.management
from utility_functions_py3 import *

#Inputs
int_frac_eu = os.path.join(resdir, 'model_predictions', '01_intermittency_frac_reaches_eu_new.shp')

for da in [[0, 10], [10, 100], [100, 1000], [10**3,10**4], [10**4,10**5], [10**5,10**6]]:
    subriver_out = os.path.join(os.path.split(int_frac_eu)[0],
                                '{0}_DA{1}_{2}.shp'.format(os.path.splitext(os.path.split(int_frac_eu)[1])[0],
                                                           re.sub('[.]', '', str(da[0])),
                                                           re.sub('[.]', '', str(da[1]))))
    sqlexp = 'upa >= {0} AND upa <= {1}'.format(da[0], da[1])
    print(sqlexp)
    arcpy.MakeFeatureLayer_management(int_frac_eu, out_layer='subriver', where_clause=sqlexp)
    arcpy.CopyFeatures_management('subriver', subriver_out)
    arcpy.Delete_management('subriver')
