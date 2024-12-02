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

logger = logging.getLogger()

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
            logger.info("Résolution du chantier : {} mètres".format(resolution))
            return float(resolution)


def get_resol_scan(metadata):
    with open(os.path.join(metadata, "resol.txt"), "r") as f:
        for line in f:
            return float(line.strip())