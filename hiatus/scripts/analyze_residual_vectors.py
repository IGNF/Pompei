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

import argparse
import json
from math import sqrt
from lxml import etree
import os
import numpy as np
from tools import getResolution
import log # Chargement des configurations des logs
import logging

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Analyse de VecteursResidusAppuis.geojson")

parser.add_argument('--input_geojson', help="Fichier geojson contenant les distances entre points d'appuis")
parser.add_argument('--input_appuis', help='Fichier GCP.xml')
parser.add_argument('--etape', help='1 ou 10')
parser.add_argument('--scripts', help='répertoire contenant les scripts')
parser.add_argument('--filter_GCP', help='filter_GCP')
args = parser.parse_args()


def open_xml(path):
    planimetrie = []
    tree = etree.parse(path)
    root = tree.getroot()

    for appui in root.findall(".//OneAppuisDAF"):
        incertitude = appui.find("Incertitude").text
        if not "-1" in incertitude:
            planimetrie.append(appui.find("NamePt").text.strip())
    return planimetrie

def compute_mean_error(chemin_geojson, planimetrie, resolution):
    distance_totale_plani = []
    distance_totale_alti = []
    with open(chemin_geojson, "r") as f:
        document = json.load(f)
        features = document["features"]
        for feature in features:
            nom = feature["properties"]["ID"]
            if nom in planimetrie:
                vx = feature["properties"]["Vx"]
                vy = feature["properties"]["Vy"]
                distance_totale_plani.append(sqrt(vx**2 + vy**2))
            
            distance_totale_alti.append(abs(feature["properties"]["Vz"]))

    erreur_moyenne_plani = np.mean(np.array(distance_totale_plani))
    erreur_moyenne_alti = np.mean(np.array(distance_totale_alti))
    erreur_moyenne_plani_pixel = erreur_moyenne_plani / resolution
    logger.info("Erreur moyenne en planimétrie sur les points d'appuis : {} mètres".format(erreur_moyenne_plani))
    logger.info("Ecart-type des résidus en planimétrie sur les points d'appuis : {} mètres\n".format(np.std(np.array(distance_totale_plani))))
    logger.info("Erreur moyenne en planimétrie sur les points d'appuis : {} pixels\n".format(erreur_moyenne_plani_pixel))
    logger.info("Erreur moyenne en altimétrie sur les points d'appuis : {} mètres".format(erreur_moyenne_alti))
    logger.info("Ecart-type des résidus en altimétrie sur les points d'appuis : {} mètres\n".format(np.std(np.array(distance_totale_alti))))    

    if erreur_moyenne_plani_pixel > 25 and args.etape=="1":
        #Si l'erreur en pixel est supérieure à 25 pixels, alors on relance les calculs avec les points d'appuis trouvés sur les images sous-échantillonnées
        logger.warning("L'erreur moyenne en planimétrie est supérieure à 25 pixels. Les points d'appuis utilisés sont ceux du sous échantillonnage")
        os.system("sh {0}/aeroSousEch10.sh {0} {1}".format(args.scripts, args.filter_GCP))



if __name__ == "__main__":

    logger.info("Analyse de VecteursResidusAppuis.geojson")

    planimetrie = open_xml(args.input_appuis)

    resolution = getResolution()
    
    compute_mean_error(args.input_geojson, planimetrie, resolution)


    