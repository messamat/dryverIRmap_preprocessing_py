from utility_functions_py3 import *

from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from io import StringIO
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd

#Define paths
#Folder structure
rootdir = get_root_fromsrcdir()
datdir = os.path.join(rootdir, 'data')

stationdir = Path(datdir, 'stations_france')
if not stationdir.exists():
    stationdir.mkdir()
stations_corsica_tab = Path(stationdir, 'stations_corsica.csv')

corsicadir = Path(datdir, 'stations_france', 'corsica')
if not corsicadir.exists():
    corsicadir.mkdir()

#Download list of stations in Corsica
station_requrl_corsica =  "https://hubeau.eaufrance.fr/api/v1/hydrometrie/referentiel/stations.csv?code_region=94&size=1000"
with urlopen(Request(station_requrl_corsica)) as response:
    soup = BeautifulSoup(response.read(), 'html.parser')
    stations_corsica_pd = pd.read_csv(StringIO(str(soup)), sep=';')
stations_corsica_pd.to_csv(stations_corsica_tab)

#Période à récupérer : ~200 ans
debut = datetime.strptime("1980-01-01", "%Y-%m-%d").isoformat()

url_API = "https://hubeau.eaufrance.fr/api/v1/hydrometrie/obs_elab.csv"
for station in stations_corsica_pd['code_station']:
    print(f"Downloading data for station {station}")
    url = url_API+ f"?code_entite={station}&" \
                   f"grandeur_hydro_elab=QmJ&" \
                   f"size=20000&" \
                   f"date_debut_obs_elab={debut}&" \
                   f"date_fin_obs_elab={datetime.now().isoformat()}"
    out_csv = Path(corsicadir, f'QmJ_{station}.csv')
    if not out_csv.exists():
        with urlopen(Request(url)) as response:
            resp = response.read()
            if resp != b'':
                soup = BeautifulSoup(resp, 'html.parser')
                pd.read_csv(StringIO(str(soup)), sep = ';').to_csv(out_csv)
            else:
                print('Empty result. Skipping...')