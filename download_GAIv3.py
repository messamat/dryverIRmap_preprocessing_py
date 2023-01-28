'''Purpose: download Global Aridity Index and Potential Evapotranspiration ET0 Climate Database v2'''
from utility_functions import *

GAIv3dir = os.path.join(datdir, 'GAIv3')
pathcheckcreate(GAIv3dir)

#https://figshare.com/articles/Global_Aridity_Index_and_Potential_Evapotranspiration_ET0_Climate_Database_v2/7504448/3
dlfile(url = "https://figshare.com/ndownloader/files/34377269",
       outpath = GAIv3dir,
       outfile = 'Global-AI_v3_monthly',
       ignore_downloadable=True)

