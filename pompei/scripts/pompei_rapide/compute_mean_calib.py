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
from lxml import etree
import numpy as np
import shutil
import log # Chargement des configurations des logs
import logging

logger = logging.getLogger()


"""
Récupère la moyenne pour chaque paramètre de calibration interne à l'issue du calcul d'aéro effectué sur chaque image individuellement
"""

def read_xml(ori_dir):
    """
    Ouverture du fichier de calibration dans le répertoire ori_dir
    """
    xml_path = [i for i in os.listdir(ori_dir) if i[:11]=="AutoCal_Foc"]
    if len(xml_path)==1:
        tree = etree.parse(os.path.join(ori_dir, xml_path[0]))
        root = tree.getroot()
        return root, xml_path[0]
    else:
        return None, None
    

def get_values(value, root):
    """
    Récupère toutes les balises value dans le fichier xml root
    """
    return root.findall(".//{}".format(value))


def write_calib_xml(root, resultats, file_name):
    """
    On écrit le fichier de calibration avec les valeurs moyennes trouvées pour chaque paramètre
    """
    root.find(".//PP").text = "{} {}".format(resultats["PP_x"], resultats["PP_y"])
    root.find(".//F").text = "{}".format(resultats["F"])
    root.find(".//CDist").text = "{} {}".format(resultats["CDist_x"], resultats["CDist_y"])
    coeffdist_balises = root.findall(".//CoeffDist")
    for i, coeffdist_balise in enumerate(coeffdist_balises):
        coeffdist_balise.text = "{}".format(resultats["CoeffDist_{}".format(i)])

    root.find(".//P1").text = "{}".format(resultats["P1"])
    root.find(".//P2").text = "{}".format(resultats["P2"])
    root.find(".//b1").text = "{}".format(resultats["b1"])
    root.find(".//b2").text = "{}".format(resultats["b2"])
    
    with open(os.path.join("Ori-Aero_0", file_name), "w") as f:
            f.write("<?xml version=\"1.0\" ?>\n")
            f.write(str(etree.tostring(root,encoding='unicode')))


def copy_ori(ori_dir):
    # On copie dans Ori-Aero_0 le fichier orientation qui se trouve dans ori_dir
    xml_path = [i for i in os.listdir(ori_dir) if i[:11]=="Orientation"]
    if len(xml_path)==1:
        shutil.copy(os.path.join(ori_dir, xml_path[0]), os.path.join("Ori-Aero_0", xml_path[0]))


dict_values = {
    "PP_x" : [],
    "PP_y" : [],
    "F" : [],
    "CDist_x" : [],
    "CDist_y" : [],
    "CoeffDist_0" : [],
    "CoeffDist_1" : [],
    "CoeffDist_2" : [],
    "CoeffDist_3" : [],
    "P1" : [],
    "P2" : [],
    "b1" : [],
    "b2" : []
}



root_not_None = None
filename_not_None = None

# Création du répertoire Ori-Aero_0 qui contiendra les nouvelles orientations réunies
os.makedirs("Ori-Aero_0", exist_ok=True)
# On parcourt toutes les images
images = [i for i in os.listdir() if i[:10]=="OIS-Reech_" and i[-4:]==".tif"]
for image in images:
    # Si le répertoire orientation de l'image n'existe pas, on l'ignore
    ori_image_dir = "Ori-{}_1".format(image)
    if not os.path.isdir(ori_image_dir):
        continue
    
    # On lit le fichier de calibration pour l'orientation de l'image
    root, filename = read_xml(ori_image_dir)
    if root is not None:
        root_not_None = root
        filename_not_None = filename
        # On copie le fichier orientation de l'image dans le nouveau répertoire orientation
        copy_ori(ori_image_dir)
        
        # Pour chaque paramètre, on récupère la valeur dans le fichier de calibration
        for value_name in dict_values.keys():
            value_splitted = value_name.split("_")
            value = get_values(value_splitted[0], root)
            
            if len(value_splitted)==1:
                dict_values[value_name].append(float(value[0].text))
            else:
                if value_splitted[1]=="x":
                    dict_values[value_name].append(float(value[0].text.split()[0]))
                elif value_splitted[1]=="y":
                    dict_values[value_name].append(float(value[0].text.split()[1]))
                else:
                    dict_values[value_name].append(float(value[int(value_splitted[1])].text))

# Pour chaque paramètre, on calcule la moyenne et l'écart-type des valeurs trouvées pour chaque image
resultats = {}
for value_name in dict_values.keys():
    logger.info(f"{value_name}")
    array = np.array(dict_values[value_name])
    mean = np.mean(array)
    std = np.std(array)
    logger.info("Moyenne : {}".format(mean))
    logger.info("Ecart-type : {}".format(std))
    resultats[value_name] = mean

# On écrit le nouveau fichier de calibration avec les valeurs moyennes
if root_not_None is None:
    raise ValueError("Aucune image n'a réussi à passer l'étape du Campari individuel")
write_calib_xml(root_not_None, resultats, filename_not_None)
