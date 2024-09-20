"""
Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/

File main authors:
- Célestin Huet

This file is part of Hiatus: https://github.com/IGNF/Hiatus

Hiatus is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Hiatus is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Hiatus. If not, see <https://www.gnu.org/licenses/>.
"""

import requests
import json
import geojson
import argparse
import os
import log # Chargement des configurations des logs
import logging

logger = logging.getLogger()



parser = argparse.ArgumentParser(description="Récupère les footprints au sol des chantiers disponibles sur la géoplateforme")
parser.add_argument('--outdir', help="Répertoire où écrire les footprints")
args = parser.parse_args()



def open_json(path):
    if not os.path.exists(path):
        raise ValueError("Le fichier suivant n'existe pas : {}".format(path))
    with open(path, "r") as f:
        json_focale = json.load(f)
    return json_focale


def find_chantier(identifiant, json_focale):
    for chantier in json_focale:
        if chantier["chantier"]==identifiant:
            return chantier
    logger.warning("La focale et la résolution n'ont pas été trouvées pour le chantier {}".format(identifiant))
    return None

def getFocale(data):
    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    path_export_focale = os.path.join(currentDirectory, "export_focales.json")
    json_focale = open_json(path_export_focale)

    for chantier in data["features"]:
        identifiant = chantier["properties"]["dataset_idta"]
        chantier_with_focale = find_chantier(identifiant, json_focale)
        if chantier_with_focale is not None:
            chantier["properties"]["resolution"] = chantier_with_focale["resolution"]
            chantier["properties"]["focale"] = chantier_with_focale["focale"]
    
    return data
    
     


def save_geojson(data, path):
    with open(path, "w") as f:
        f.write(geojson.dumps(data))



def getChantiers():
    url = "https://data.geopf.fr/wfs?service=WFS&version=2.0.0&typeName=pva:dataset&request=GetFeature&outputFormat=json&sortBy=date_mission"

    r = requests.get(url)
    if r.status_code==200:
        data0 = json.loads(r.text)
        nb_features = data0["totalFeatures"]

        for i in range(5000, nb_features, 5000):
            url = "https://data.geopf.fr/wfs?service=WFS&version=2.0.0&typeName=pva:dataset&request=GetFeature&outputFormat=json&sortBy=date_mission&startIndex={}".format(i)

            r = requests.get(url)
            if r.status_code==200:
                data = json.loads(r.text)
                data0["features"] += data["features"]
            
        return data0
    
    else:
        raise ValueError("La requête {} renvoie le code {}".format(url, r.status_code))


outdir = args.outdir

os.makedirs(outdir, exist_ok=True)
data = getChantiers()
data = getFocale(data)
save_geojson(data, os.path.join(outdir, "footprints.geojson"))