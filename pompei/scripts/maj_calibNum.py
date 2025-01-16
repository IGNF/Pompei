"""
Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/

File main authors:
- Célestin Huet
- Arnaud Le Bris

This file is part of Pompei: https://github.com/IGNF/Pompei

Pompei is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Pompei is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Pompei. If not, see <https://www.gnu.org/licenses/>.
"""

import os
from PIL import Image
from lxml import etree
import argparse
from tools import getSensors

#à partir d'une liste d'éléments, renvoie une sous-liste de tous les éléments qui contiennent une liste de pattern  
def filter_list_pattern_in(list_to_filter, list_pattern_in): 
    return [str for str in list_to_filter if
             all(subin in str for subin in list_pattern_in)] 


def get_images(sensors, identifiant):
	for sensor_dict in sensors:
		if sensor_dict["identifiant"]==identifiant:
			return sensor_dict["images"]

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description="Met à jour le fichier Ori-CalibNum")
	parser.add_argument('--identifiant', help="Identifiant du vol à pour lequel il faut calculer la position moyenne", type=int)
	parser.add_argument('--ta', help="Tableau d'assemblage")
	args = parser.parse_args()

	TA_path = args.ta
	identifiant = args.identifiant

	input_calib_folder = "Ori-CalibNum"

	tree = etree.parse(TA_path)
	root = tree.getroot()

	# On récupère les capteurs et leurs images associées
	sensors = getSensors(root)

	# On récupère la liste des images associées au vol identifiant
	images = get_images(sensors, identifiant)

	list_xml = []
	list_OIS = []	
	
	
	suffixe = f"Argentique{identifiant}.xml"
	list_xml = [i for i in os.listdir(input_calib_folder) if i[-len(suffixe):]==suffixe]

	#On récupère les clichés argentiques rééchantillonnés
	list_OIS = []
	list_OIS_tmp = [i.replace("OIS-Reech_", "") for i in os.listdir() if i[:10]=="OIS-Reech_" and i[-4:]==".tif"]
	for im in list_OIS_tmp:
		if im in images:
			list_OIS.append(im)
	list_OIS = filter_list_pattern_in(os.listdir(),['OIS-Reech_', '.tif'])
	
	#On augmente la taille maximale des images acceptées par PIL
	Image.MAX_IMAGE_PIXELS = 1e15

	#taille image des clichés argentiques rééchantillonnés
	im = Image.open(list_OIS[0])
	w, h = im.size
	half_w = int(float(w)/2)
	half_h = int(float(h)/2)
	
	str_width=str(w)
	str_height=str(h)

	
	#lecture fichier Ori-CalibNum
	for xml in list_xml:
		tree = etree.parse(os.path.join(input_calib_folder, xml))
		root = tree.getroot()

		root.find(".//PP").text = "{} {}".format(half_w, half_h)
		root.find(".//SzIm").text = "{} {}".format(w, h)
		root.find(".//CDist").text = "{} {}".format(half_w, half_h)

		AutoCal_Foc_path = os.path.join(input_calib_folder, xml)
		with open(AutoCal_Foc_path, "w") as f:
			f.write("<?xml version=\"1.0\" ?>\n")
			f.write(str(etree.tostring(root, encoding='unicode')))
		


	with open("find_tie_points.sh", "r") as f:
		text = f.readlines()
	
	with open("find_tie_points.sh", "w") as f:
		for line in text:
			if "mm3d Tapioca File CouplesTA.xml" in line:
				if len(list_OIS) >= 4:
					line = "mm3d Tapioca File CouplesTA.xml " + str(max(half_w, half_h)) + " | tee reports/rapport_Tapioca.txt >> logfile \n"
				else:
					line = "mm3d Tapioca All OIS-Reech.*.tif " + str(max(half_w, half_h)) + " | tee reports/rapport_Tapioca.txt >> logfile \n"
			if "mm3d OriConvert OriTxtInFile" in line:
				if len(list_OIS) >= 4:
					line = "mm3d OriConvert OriTxtInFile SommetsNav.csv Nav NameCple=CouplesTA.xml >> logfile \n"
				else:
					line = "mm3d OriConvert OriTxtInFile SommetsNav.csv Nav >> logfile \n"
			f.write(line)
