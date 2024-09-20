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

import os
import argparse
from osgeo import gdal
import numpy as np
import log # Chargement des configurations des logs
import logging

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Supprime les dalles noires pour éviter d'y faire la recherche de points d'appuis")

parser.add_argument('--path', help="Répertoire contenant les dalles")
parser.add_argument('--seuil_value', help="Valeur maximale d'un pixel pour qu'il soit considéré comme sans information")
parser.add_argument('--seuil_prop', help="Proportion de pixels sans informations au-delà de laquelle l'image est supprimée")
args = parser.parse_args()

liste_images = os.listdir(args.path)
compte = 0
for image in liste_images:
    if image[-4:] == ".tif":
        inputds = gdal.Open(os.path.join(args.path, image))
        inputlyr = np.array(inputds.GetRasterBand(1).ReadAsArray())
        array_count = np.zeros(inputlyr.shape)
        array_count[inputlyr<=float(args.seuil_value)] = 1
        if np.sum(array_count) / (inputlyr.shape[0] * inputlyr.shape[1]) >= float(args.seuil_prop):
            os.remove(os.path.join(args.path, image))
            compte += 1
logger.info("{} dalles ont été supprimées".format(compte))