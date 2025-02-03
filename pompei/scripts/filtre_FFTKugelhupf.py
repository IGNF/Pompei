#Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/
#
#File main authors:
#- Célestin Huet
#This file is part of Pompei: https://github.com/IGNF/Pompei
#
#Pompei is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#Pompei is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#You should have received a copy of the GNU General Public License along with Pompei. If not, see <https://www.gnu.org/licenses/>.

import os
import rasterio
import numpy as np
import argparse
from tools import getSensors
from lxml import etree

parser = argparse.ArgumentParser(description="Calcule la position moyenne des repères de fond de chambre")
parser.add_argument('--identifiant', help="Identifiant du vol à pour lequel il faut calculer la position moyenne", type=int)
parser.add_argument('--ta', help="Tableau d'assemblage")
args = parser.parse_args()


def get_images(sensors, identifiant):
	for sensor_dict in sensors:
		if sensor_dict["identifiant"]==identifiant:
			return sensor_dict["images"]

TA_path = args.ta
identifiant = args.identifiant

input_calib_folder = "Ori-CalibNum"

tree = etree.parse(TA_path)
root = tree.getroot()

# On récupère les capteurs et leurs images associées
sensors = getSensors(root)

# On récupère la liste des images associées au vol identifiant
images = get_images(sensors, identifiant)

files = [i for i in os.listdir() if i in images]

for filename in files:
    image_src = rasterio.open(filename)
    array = image_src.read()
    array = array[0,:,:]
    array = np.where(array < 20, 0, 255)
    array = np.expand_dims(array, axis=0)

    with rasterio.open(
            "filtre_FFTKugelHupf_"+filename, "w",
            driver = "GTiff",
            dtype = rasterio.uint8,
            count = array.shape[0],
            width = array.shape[2],
            height = array.shape[1]) as dst:
        dst.write(array)





