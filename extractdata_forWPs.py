import arcpy.management

from utility_functions_py3 import *
import pandas as pd

arcpy.CheckOutExtension('Spatial')

#Inputs
eu_net_dir = os.path.join(resdir, 'eu_nets')
eu_net_resdir = os.path.join(resdir, 'eu_nets_format')
eu_net_gdb = os.path.join(eu_net_resdir, 'dryver_net_eu.gdb')

eu_net = os.path.join(eu_net_dir, '01_dryver_net_eu.shp')

process_gdb = os.path.join(resdir, 'extend_HydroRIVERS_process.gdb')
dryver_netpourpoints = os.path.join(process_gdb, 'net_dryver_upao2_dis003_pourpoints')
dryver_predvargdb = os.path.join(resdir, 'net_dryver_predvars_zonalstats.gdb')

attris_to_add = os.path.join(datdir, 'RiverATLAS_variables_required_for_WPs.xlsx')

#Outputs
attri_tab_eu = os.path.join(eu_net_gdb, 'dryver_net_attri_forWPs')
attri_tab_eu_csv = os.path.join(eu_net_resdir, 'dryver_net_attri_forWPs.csv')

########################################################################################################################
#Export attribute table from reduced layer
if not arcpy.Exists(attri_tab_eu):
    arcpy.management.CreateTable(out_path = eu_net_gdb,
                                 out_name = os.path.basename(attri_tab_eu))
    arcpy.management.AddField(attri_tab_eu, 'DRYVER_RIV', 'LONG')

    idlist = [row[0] for row in arcpy.da.SearchCursor(eu_net, ['DRYVER_RIV'])]
    with arcpy.da.InsertCursor(attri_tab_eu, ['DRYVER_RIV']) as cursor:
        for id in idlist:
            cursor.insertRow([id])

#List desired attributes from main network layer
field_dict_upstream = {
    'up_area_skm_15s': 'UPLAND_SKM',
    'hylak_all_area_pc_x100_acc': 'lka_pc_use',
    'dor_pc_pva': 'dor_pc_pva',
    'ai3_01_uav': 'ai_ix_m01_uav',
    'ai3_02_uav': 'ai_ix_m02_uav',
    'ai3_03_uav': 'ai_ix_m03_uav',
    'ai3_04_uav': 'ai_ix_m04_uav',
    'ai3_05_uav': 'ai_ix_m05_uav',
    'ai3_06_uav': 'ai_ix_m06_uav',
    'ai3_07_uav': 'ai_ix_m07_uav',
    'ai3_08_uav': 'ai_ix_m08_uav',
    'ai3_09_uav': 'ai_ix_m09_uav',
    'ai3_10_uav': 'ai_ix_m10_uav',
    'ai3_11_uav': 'ai_ix_m11_uav',
    'ai3_12_uav': 'ai_ix_m12_uav',
    'cropland_ext_pc_x100_acc': 'crp_pc_use',
    'pasture_ext_pc_x100_acc': 'pst_pc_use',
    'carbon_tha_zeros_acc': 'soc_th_uav',
    'ghs_smod_2015_urb_ext_pc_acc': 'urb_pc_use',
}

#Fast join them
attriflist = [f.name for f in arcpy.ListFields(attri_tab_eu)]
ftojoin = [[k, v] for k, v in field_dict_upstream.items() if v not in attriflist]
if len(ftojoin) > 0:
    fast_joinfield(in_data=attri_tab_eu,
                   in_field='DRYVER_RIV',
                   join_table=dryver_netpourpoints,
                   join_field='DRYVER_RIVID',
                   fields=ftojoin,
                   round=True)

#Fast join land cover
field_dict_upstream_lc = {}
for cl in range(1, 23):
    field_dict_upstream_lc[f'glc2000_ext_bin_cl{str(cl).zfill(2)}_acc'] = f'glc_pc_u{str(cl).zfill(2)}'
attriflist = [f.name for f in arcpy.ListFields(attri_tab_eu)]
ftojoin_lc = [[k, v] for k, v in field_dict_upstream_lc.items() if v not in attriflist]
if len(ftojoin_lc) > 0:
    fast_joinfield(in_data=attri_tab_eu,
                   in_field='DRYVER_RIV',
                   join_table=dryver_netpourpoints,
                   join_field='DRYVER_RIVID',
                   fields=ftojoin_lc,
                   round=True,
                   factor=100)

#Add attributes from zonal statistics
#Fast join land cover
for cltab in [os.path.join(dryver_predvargdb, f'glc_pc_c{str(cl).zfill(2)}') for cl in range(1, 23)]:
    fast_joinfield(in_data=attri_tab_eu,
                   in_field='DRYVER_RIV',
                   join_table=cltab,
                   join_field='Value',
                   fields=[['MEAN', os.path.basename(cltab)]],
                   round=True,
                   factor=100)

allattris_to_add_pd = pd.read_excel(attris_to_add).iloc[:,0].tolist()
existing_attriflist = [f.name for f in arcpy.ListFields(attri_tab_eu)]
computed_attris = [os.path.basename(p) for p in getfilelist(dryver_predvargdb)]

catchmentstats_toadd = [f for f in allattris_to_add_pd #Only extract variable if it is:
                        if ((f not in existing_attriflist) and #in list of variales to add
                            (f in computed_attris))]

for var in catchmentstats_toadd:
    fast_joinfield(in_data=attri_tab_eu,
                   in_field='DRYVER_RIV',
                   join_table=os.path.join(dryver_predvargdb, var),
                   join_field='Value',
                   fields=[['MEAN', var]],
                   round=True)


#~~~~~~~~~~~~~~~~~ Compute statistics along the reach ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

'ria_ha_rsu'
'riv_tc_rsu'


#~~~~~~~~~~~~~~~~~~ Compute derived statistics ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
arcpy.management.AddField(attri_tab_eu, 'for_pc_cse', 'SHORT')
arcpy.management.AddField(attri_tab_eu, 'tmp_dc_cyr', 'SHORT')
arcpy.management.AddField(attri_tab_eu, 'pet_mm_cyr', 'SHORT')
arcpy.management.AddField(attri_tab_eu, 'pre_mm_cyr', 'SHORT')

with arcpy.da.UpdateCursor(attri_tab_eu, ['for_pc_cse', ])
'for_pc_use'
'for_pc_cse'
'tmp_dc_cyr'
'pet_mm_cyr'
'pre_mm_cyr'

#~~~~~~~~~~~~~~~~~~ Export table to CSV ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
arcpy.management.CopyRows(attri_tab_eu, attri_tab_eu_csv)
