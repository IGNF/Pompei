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
import shutil
import argparse
from lxml import etree
from tools import getSensors


parser = argparse.ArgumentParser(description="Création d'un masque par image pour Malt")
parser.add_argument('--TA', help='Fichier TA du chantier')
args = parser.parse_args()


TA_path = args.TA

tree = etree.parse(TA_path)
root = tree.getroot()
sensors = getSensors(root)


for sensor_dict in sensors:
    identifiant = sensor_dict["identifiant"]
    images = sensor_dict["images"]
    filtre_name = f"filtre{identifiant}.tif"
    if os.path.isfile(filtre_name):
        for image in images:
            filtre_image_name = image[:-4]
            filtre_image_name = f"OIS-Reech_{filtre_image_name}_Masq.tif"
            shutil.copy(filtre_name, filtre_image_name)
