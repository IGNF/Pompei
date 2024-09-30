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
import os


parser = argparse.ArgumentParser(description="Calcule la résolution terrain du chantier")

parser.add_argument('--input_ori', help="Répertoire avec l'orientation")
parser.add_argument('--metadata', help='Résolution du scannage')
args = parser.parse_args()


input_ori = args.input_ori
metadata = args.metadata

def get_focale(input_ori):
    """
    Renvoie la focale en pixels
    """
    xml_file = [i for i in os.listdir(input_ori) if i[:11]=="AutoCal_Foc" and i[-4:]==".xml"]
    if len(xml_file)==0:
        raise ValueError("Le fichier de calibration n'a pas été trouvé dans {}".format(input_ori))
    tree = etree.parse(os.path.join(input_ori, xml_file[0]))
    root = tree.getroot()
    focale = root.find(".//F")
    return float(focale.text)

def get_profondeur(input_ori):
    """
    Renvoie la distance approximative entre l'avion et le sol en mètres
    """
    xml_files = [i for i in os.listdir(input_ori) if i[:11]=="Orientation" and i[-4:]==".xml"]
    if len(xml_files)==0:
        raise ValueError("Aucun fichier d'orientation n'a été trouvé dans {}".format(input_ori))
    tree = etree.parse(os.path.join(input_ori, xml_files[0]))
    root = tree.getroot()
    profondeur = root.find(".//Profondeur")
    return float(profondeur.text)

def save_resolution(resolution, metadata):
    with open(os.path.join(metadata, "resolution.txt"), "w") as f:
        f.write(str(resolution))


focale_pixel = get_focale(input_ori)
profondeur = get_profondeur(input_ori)
resolution = int(profondeur/focale_pixel*10)/10
save_resolution(resolution, metadata)
