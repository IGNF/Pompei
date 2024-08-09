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
import os
import geopandas as gpd
from shapely import Polygon, LineString


parser = argparse.ArgumentParser(description="Visualise les points de liaisons")
parser.add_argument('--homol', help='Répertoire contenant les points homologues')
parser.add_argument('--footprints', help='Emprises au sol')
parser.add_argument('--reports', help='Répertoire contenant les reports')
args = parser.parse_args()








homol_dir = args.homol
footprints = args.footprints
reports_dir = args.reports

def get_number_homol(file):
    compte = 0
    with open(file, "r") as f:
        for line in f:
            compte += 1
    return compte

def get_barycenter(coordinates):
    p = Polygon(coordinates[0])
    return p.centroid


def get_center(gdf, image_name):
    for image in gdf.iterfeatures():
        if image["properties"]["nom"] == image_name:
            return get_barycenter(image["geometry"]["coordinates"])
    raise ValueError("Impossible de trouver l'image {}".format(image_name))


gdf = gpd.read_file(footprints)

nb_homol_list = []
geometries = []

homol_dir_images = os.listdir(homol_dir)
for homol_dir_image in homol_dir_images:
    image_name = homol_dir_image[16:-4]
    center_image_1 = get_center(gdf, image_name)
    homol_files = [i for i in os.listdir(os.path.join(homol_dir, homol_dir_image)) if i[-4:]==".txt"]
    for homol_file in homol_files:
        homol_file_name = homol_file[10:-8]
        nb_homol = get_number_homol(os.path.join(homol_dir, homol_dir_image, homol_file))
        center_image_2 = get_center(gdf, homol_file_name)
        nb_homol_list.append(nb_homol)
        geometries.append(LineString([center_image_1, center_image_2]))

d = {"nb_homol":nb_homol_list, "geometry": geometries}
gdf = gpd.GeoDataFrame(d, crs="EPSG:2154")
gdf.to_file(os.path.join(reports_dir, "nb_homologues.shp"))     
        