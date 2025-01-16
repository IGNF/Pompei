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

from lxml import etree
import os
import numpy as np
import argparse
from tools import getSensors


parser = argparse.ArgumentParser(description="Calcule la position moyenne des repères de fond de chambre")
parser.add_argument('--identifiant', help="Identifiant du vol à pour lequel il faut calculer la position moyenne", type=int)
parser.add_argument('--ta', help="Tableau d'assemblage")
args = parser.parse_args()

identifiant = args.identifiant
TA_path = args.ta


def get_images(sensors, identifiant):
	for sensor_dict in sensors:
		if sensor_dict["identifiant"]==identifiant:
			return sensor_dict["images"]

if __name__ == "__main__":

	tree = etree.parse(TA_path)
	root = tree.getroot()

	# On récupère les capteurs et leurs images associées
	sensors = getSensors(root)

	# On récupère la liste des images associées au vol identifiant
	images = get_images(sensors, identifiant)

	# Récupération des identifiants des repères de fond de chambre dans id_reperes.txt
	listReperes = []
	with open("id_reperes.txt", "r") as filerepere:
		for ligne in filerepere:
			listReperes.append(ligne.rstrip('\n\r'))

	#On récupère la liste des fichiers contenant la position des repères de fond de chambre pour chaque cliché
	InterneScan_path = "Ori-InterneScan"
	listFile = [i for i in os.listdir(InterneScan_path) if i[:10]=="MeasuresIm" and i[-4:]==".xml"]
	listXml = []
	#on ne garde que les fichiers Measures-Im  Xml
	for file in listFile :
		image_name = file.split('-')[1].replace(".xml", "")
		if file.split('-')[0] == 'MeasuresIm' and image_name in images:
			listXml.append(file)

	#création de la structure xml d'export
	MesureAppui = etree.Element("MesureAppuiFlottant1Im")
	idReperes = etree.SubElement(MesureAppui, "NameIm")
	idReperes.text = "id_reperes"



	listRep=[]
	listPtImCoor=[]
	#On parcourt les fichiers contenant les positions des repères de fond de chambre
	for xml in listXml :
		tree = etree.parse(os.path.join(InterneScan_path, xml))
		root = tree.getroot()
		#On récupère la position des points
		for PtIm in root.getiterator("PtIm"):
			listPtImCoor.append(PtIm.text)

		#On récupère le nom des points
		for NamePt in root.getiterator("NamePt"):
			listRep.append(NamePt.text)


	#Pour chaque repère de fond de chambre, on calcule sa position moyenne
	for repere in listReperes:
		xmoyen= []
		ymoyen= []
		for rep,coor in zip(listRep, listPtImCoor):
			if rep == repere:
				xmoyen.append(float(coor.split(' ')[0]))	
				ymoyen.append(float(coor.split(' ')[-1]))
			
		OneMesure = etree.SubElement(MesureAppui, "OneMesureAF1I")
		NamePt = etree.SubElement(OneMesure, "NamePt")
		NamePt.text=repere
		PtIm = etree.SubElement(OneMesure, "PtIm")
		strPtIm=str(np.mean(xmoyen))+" "+str(np.mean(ymoyen))
		PtIm.text=strPtIm


	#Construction du fichier MeasuresCamera.xml qui contient la position moyenne des repères de fond de chambre
	with open(os.path.join(InterneScan_path, "MeasuresCamera.xml"), "w") as f:
		f.write('<?xml version="1.0" ?>')
		f.write(str(etree.tostring(MesureAppui,encoding='unicode')))




