"""
Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/

File main authors:
- Célestin Huet

This file is part of Pompei: https://github.com/IGNF/Pompei

Pompei is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Pompei is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Pompei. If not, see <https://www.gnu.org/licenses/>.
"""

import argparse
from osgeo import gdal
import os
from pyproj import CRS, Transformer
import requests
from tools import getEPSG
import log # Chargement des configurations des logs
import logging

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Téléchargement des dalles du SRTM du chantier")
parser.add_argument('--metadata', help='Dossier contenant EPSG.txt')
parser.add_argument('--output', help='Chemin où enregistrer la dalle du SRTM')
args = parser.parse_args()



def load_bbox(metadata):
    #Charge la bounding box créée lorsqu'on a lancé sh.visualisation.sh
    bbox = []
    with open(os.path.join(metadata, "bbox.txt"), "r") as f:
        for line in f:
            bbox.append(float(line.strip()))
    points = [(bbox[0], bbox[3]), (bbox[2], bbox[3]), (bbox[2], bbox[1]), (bbox[0], bbox[1])]
    return points


def transform_Points_WGS84(EPSG, points):
    crsWGS84 = CRS.from_epsg(4326)
    crsChantier = CRS.from_epsg(EPSG)
    transformer = Transformer.from_crs(crsChantier, crsWGS84)
    pointsWGS84 = []
    for point in points:
        pointsWGS84.append(transformer.transform(point[0], point[1]))
    #Les points sont en latitude longitude
    return pointsWGS84


def download(pointsWGS84, path):
    south = pointsWGS84[0][0]
    north = pointsWGS84[0][0]
    east = pointsWGS84[0][1]
    west = pointsWGS84[0][1]
    for point in pointsWGS84:
        south = min(south, point[0])
        north = max(north, point[0])
        west = min(west, point[1])
        east = max(east, point[1])
    url = "https://portal.opentopography.org/API/globaldem?demtype=SRTMGL1&south={}&north={}&west={}&east={}&outputFormat=GTiff&API_Key=demoapikeyot2022".format(south, north, west, east)
    logger.info(url)
    r = requests.get(url)
    with open(path, 'wb') as out:
        out.write(bytes(r.content))
    


points = load_bbox(args.metadata)  
EPSG = getEPSG(args.metadata)  
pointsWGS84 = transform_Points_WGS84(EPSG, points)
download(pointsWGS84, args.output)
