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
from lxml import etree
import log # Chargement des configurations des logs
import logging
import rasterio
import numpy as np

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Création du masque pour déterminer la zone de recherche des repères de fond de chambre")
parser.add_argument('--image', help='Image sur laquelle ont été saisis les repères de fond de chambre')
parser.add_argument('--xml_file', help="Fichier xml contenant les points saisis par l'opérateur")
parser.add_argument('--output_mask', help='Fichier masque à créer')
args = parser.parse_args()

image_path = args.image
xml_file = args.xml_file
path_output_mask = args.output_mask


def init_mask(image_path):
    input_ds = rasterio.open(image_path)
    width = input_ds.width
    height = input_ds.height
    mask = np.zeros((1, height, width))
    return mask


def read_points(xml_file):
    points = []
    tree = etree.parse(xml_file)
    root = tree.getroot()
    points_balises = root.findall(".//OneMesureAF1I")
    for point_balise in points_balises:
        ptIm_balise = point_balise.find(".//PtIm")
        ptIm = ptIm_balise.text.split()
        points.append([float(ptIm[1]), float(ptIm[0])])

    return points


def create_mask(mask, points):
    _, i_max, j_max = mask.shape
    demi_size = 500
    for point in points:
        i, j = int(point[0]), int(point[1])
        i0 = max(0, i-demi_size)
        j0 = max(0, j-demi_size)
        i1 = min(i_max, i+demi_size)
        j1 = min(j_max, j+demi_size)
        mask[:,i0:i1,j0:j1] = 1
    return mask


def save_image(mask, path_output_mask):
    with rasterio.open(
        path_output_mask, "w",
        driver = "GTiff",
        dtype = rasterio.uint8,
        count = mask.shape[0],
        width = mask.shape[2],
        height = mask.shape[1]
        ) as dst:
        dst.write(mask)


mask = init_mask(image_path)
points = read_points(xml_file)
mask = create_mask(mask, points)
save_image(mask, path_output_mask)