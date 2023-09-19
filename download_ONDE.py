from utility_functions_py3 import *
import requests
import zipfile
import pandas as pd
#Onde Eau dirs
datdir_onde = os.path.join(datdir, 'ONDE')
if not os.path.exists(datdir_onde):
    os.mkdir(datdir_onde)

resdir_onde = os.path.join(resdir, "onde_process.gdb")
ondeau_mergecsv = os.path.join(datdir, 'onde_france_merge.csv')
obsraw = os.path.join(resdir_onde,'obsraw')
obsnodupli = os.path.join(resdir_onde, 'obsnodupli')


# -------------------- FRANCE - ONDE EAU -------------------------------------------------------------------------------
for yr in range(2012, 2024):
    in_url = "https://onde.eaufrance.fr/sites/default/files/fichiers-telechargeables/onde_france_{}.zip".format(yr)
    print(in_url)
    out_file = os.path.join(datdir_onde, os.path.split(in_url)[1])
    if not os.path.exists(os.path.join(datdir_onde, out_file)):
        with open(out_file, "wb") as file:
            # get request
            print(f"Downloading HydroRIVERs")
            response = requests.get(in_url, verify=False)
            file.write(response.content)
        with zipfile.ZipFile(out_file, 'r') as zip_ref:
            zip_ref.extractall(os.path.dirname(out_file))

# Merge OndeEau csv
if not arcpy.Exists(ondeau_mergecsv):
    mergedelcsv(dir=datdir_onde,
                repattern="onde_france_[0-9]{4}[.]csv",
                outfile=ondeau_mergecsv,
                returndf=False,
                delete=False,
                verbose=True)

# Convert to points (SpatialReference from ProjCoordSiteHydro referenced to http://mdm.sandre.eaufrance.fr/node/297134 - code 26 (247 observations also have code 2154 which must be a mistake and refers to the ESPG code)
if not arcpy.Exists(obsraw):
    arcpy.MakeXYEventLayer_management(table=ondeau_mergecsv,
                                      in_x_field="<CoordXSiteHydro>",
                                      in_y_field="<CoordYSiteHydro>",
                                      out_layer='ondelyr',
                                      spatial_reference=arcpy.SpatialReference(
                                          2154))  # Lambert 93 for mainland France and Corsica
    arcpy.CopyFeatures_management('ondelyr', obsraw)

#Delete duplicated locations
if not arcpy.Exists(obsnodupli):
    group_duplishape(in_features=obsraw, deletedupli=True, out_featuresnodupli=obsnodupli)

########### SEE https://github.com/messamat/globalIRmap_py/blob/master/format_FROndeEaudata.py for details on getting to obsfinal

################################################### ANALYSIS ###########################################################
# <LbSiteHydro>Name of site
# <CdSiteHydro> Unique code for site
# <Annee>Year of observation
# <TypeCampObservations>:
#       Usuelle: La campagne usuelle (réseau ONDE) vise à acquérir de la donnée pour la constitution d'un réseau
#       stable de connaissance. Elle est commune à l'ensemble des départements, sa fréquence d'observation est mensuelle,
#       au plus près du 25 de chaque mois à plus ou moins 2 jours, sur la période de mai à septembre.
#   `   Crise:La campagne de crise (réseau ONDE) vise à acquérir de la donnée destinée aux services de l'État en charge
#       de la gestion dela crise en période de sécheresse.
# <DtRealObservation>': Datee of observation
# <LbRsObservationDpt>:Observation result label (Departmental typology)
# <RsObservationDpt>: Observation result(Department typology)
# <LbRsObservationNat> Observation result label (National typology)
# <RsObservationNat> Observation result (National typology)
# <NomEntiteHydrographique>
# <CdTronconHydrographique>
# <CoordXSiteHydro>
# <CoordYSiteHydro>
# <ProjCoordSiteHydro>
# FLG: End of line--- not useful - NOT FLAG