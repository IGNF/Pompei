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
from math import sqrt
import os
import log # Chargement des configurations des logs
import logging
from lxml import etree
import sys

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Analyse du rapport de CenterBascule pour vérifier qu'il n'y a pas de problèmes lors du passage en coordonnées absolues approximatives")

parser.add_argument('--input_report', help='Rapport CenterBascule')
parser.add_argument('--ori_abs', help='Orientation après la bascule en orientation absolue')
args = parser.parse_args()

ori_abs = args.ori_abs


def find_problem(chemin_rapport):
    distance_max = 0
    image_distance_min = ""

    with open(chemin_rapport, "r") as f:
        for line in f:
            if "Basc-Residual" in line:
                line_splitted = line.split()
                coordinate = line_splitted[2].replace("[", "").replace("]", "")
                coordinate_splitted = coordinate.split(",")
                dx = float(coordinate_splitted[0])
                dy = float(coordinate_splitted[1])
                dz = float(coordinate_splitted[2])
                distance = sqrt(dx**2 + dy**2 + dz**2)
                if distance > distance_max:
                    distance_max = distance
                    image_distance_min = line_splitted[1]

    logger.info("Le plus gros déplacement concerne l'image {} : {} mètres".format(image_distance_min, distance_max))


def check_verticale(ori_abs):
    """
    Pour vérifier qu'un chantier est à peu près à la verticale, il faut regarder la dernière valeur de la ligne L3 
    dans les orientations. Cette valeur doit être en valeur absolue proche de 1 
    """
    ori_xmls = [i for i in os.listdir(ori_abs) if i[:11]=="Orientation" and i[-4:]==".xml"]
    for ori_xml in ori_xmls:
        tree = etree.parse(os.path.join(ori_abs, ori_xml))
        root = tree.getroot()
        l3_balise = root.find(".//L3")
        value = abs(float(l3_balise.text.split(" ")[2]))
        if value < 0.95:
            logger.warning(f"L'orientation dans le fichier {os.path.join(ori_abs, ori_xml)} n'est pas verticale : {value}")
            sys.exit(1)


if __name__ == "__main__":

    find_problem(args.input_report)
    check_verticale(ori_abs)


    