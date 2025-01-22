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

import os
import log # Chargement des configurations des logs
import logging
from equations import Shot, Calibration
from lxml import etree

logger = logging.getLogger()



class Sensor:

    def __init__(self) -> None:
        self.width = None
        self.height = None
        self.focale = None

    def setWidth(self, width):
        self.width = width

    def setHeight(self, height):
        self.height = height

    def setFocale(self, focale):
        self.focale = focale

def getEPSG(metadata):
    with open(os.path.join(metadata, "EPSG.txt"), "r") as f:
        for line in f:
            return int(line)

def load_bbox(metadata):
    #Charge la bounding box créée lorsqu'on a lancé sh.visualisation.sh
    bbox = []
    with open(os.path.join(metadata, "bbox.txt"), "r") as f:
        for line in f:
            bbox.append(float(line.strip()))
    return bbox

def getNbCouleurs(metadata):
    with open(os.path.join(metadata, "nb_colors.txt"), "r") as f:
        for line in f:
            return int(line)

def getResolution():
    path = os.path.join("Ortho-MEC-Malt-Abs-Ratafia", "Orthophotomosaic.tfw")
    if not os.path.exists(path):# Cas de pompei_rapide.sh
        path = os.path.join("metadata", "resolution.txt")
    if not os.path.exists(path):
        raise Exception("Impossible de récupérer la résolution du chantier")
    
    with open(path, "r") as f:
        for line in f:
            resolution = float(line)
            return float(resolution)


def get_resol_scan(metadata):
    with open(os.path.join(metadata, "resol.txt"), "r") as f:
        for line in f:
            return float(line.strip())
        
def get_calibration_file(ori, suffixe):
    files = os.listdir(ori)
    for file in files:
        if file[-len(suffixe):]==suffixe:
            return file
    logger.warning(f"Fichier avec le suffixe {suffixe} non trouvé dans {ori}")


def read_ori(ori, TA_path, EPSG):
    tree = etree.parse(TA_path)
    root = tree.getroot()
    sensors = getSensors(root)
    proj = Shot.getProj(EPSG)
    shots = []
    for sensor_dict in sensors:
        images = sensor_dict["images"]
        identifiant = sensor_dict["identifiant"]
        calibration_suffixe = f"Argentique{identifiant}.xml"
        calibration_file = get_calibration_file(ori, calibration_suffixe)
        calibration = Calibration.createCalibration(os.path.join(ori, calibration_file))
        for image in images:
            ori_file = f"Orientation-OIS-Reech_{image}.xml"
            if os.path.isfile(os.path.join(ori, ori_file)):
                shot = Shot.createShot(os.path.join(ori, ori_file), proj, calibration)
                shots.append(shot)
    return shots


def createSensor(sensor_xml):
    sensor = Sensor()
    rect = sensor_xml.find(".//rect")
    w = int(rect.find(".//w").text.strip())
    sensor.setWidth(w)
    h = int(rect.find(".//h").text.strip())
    sensor.setHeight(h)
    focal = sensor_xml.find(".//focal")
    f = int(float(focal.find(".//z").text.strip()))
    sensor.setFocale(f)
    logger.debug(f"Ajout d'une caméra")
    logger.debug(f"Taille du capteur : ({w}, {h})")
    logger.debug(f"Focale de la caméra : {f}")
    return sensor


def getSensors(root):
    """
    Renvoie une liste de dictionnaires :
    - sensor : capteur
    - images : liste des images acquise avec le capteur
    """
    sensors = []
    identifiant = 0
    for vol in root.findall(".//vol"):
        images = []
        for cliche in vol.findall(".//cliche"):
            image_path = f"{cliche.find("image").text.strip()}.tif"
            imageOIS_path = f"OIS-Reech_{cliche.find("image").text.strip()}.tif"
            if os.path.exists(image_path) or os.path.exists(imageOIS_path):
                images.append(image_path)
        
        if len(images)>=1:
            sensor_xml = vol.find(".//sensor")
            sensor = createSensor(sensor_xml)
            sensors.append({
                "sensor":sensor,
                "images":images,
                "identifiant":identifiant
                })
            identifiant += 1
    return sensors