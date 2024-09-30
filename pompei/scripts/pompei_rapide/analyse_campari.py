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
import numpy as np
import argparse
import os
import shutil
import log # Chargement des configurations des logs
import logging

logger = logging.getLogger()


parser = argparse.ArgumentParser(description="Analyse des résultats Campari où chaque image est calculée individuellement")
parser.add_argument('--appuis', help="Points d'appuis de la BD Ortho")
parser.add_argument('--report_residuals', help="Rapport Campari sur les résidus")
args = parser.parse_args()

def lecture_appui_xml(path):
    liste_plani = []
    liste_alti = []
    
    tree = etree.parse(path)
    root = tree.getroot()
    liste_appuis = root.findall(".//OneAppuisDAF")
    
    for appui in liste_appuis:
        nomPoint = appui.find("NamePt").text
        incertitude = appui.find("Incertitude").text
        if "-1" in incertitude:
            liste_alti.append(nomPoint)
        else:
            liste_plani.append(nomPoint)
    return liste_alti, liste_plani


def lecture_rapport_residus(path, liste_plani):

    dict_appuis = []
    delta_plani = []
    delta_alti = []

    with open(path, "r") as f:
        for line in f:
            if "*APP" in line:
                line_splitted = line.split()
                nom_point = line_splitted[0][1:]
                ZTer = float(line_splitted[3])
                Zcomp = float(line_splitted[6])
                if nom_point in liste_plani:
                    XTer = float(line_splitted[1])
                    Xcomp = float(line_splitted[4])
                    YTer = float(line_splitted[2])
                    Ycomp = float(line_splitted[5])

                    delta = np.sqrt((XTer - Xcomp)**2 + (YTer - Ycomp)**2 + (ZTer - Zcomp)**2)
                    dict_appuis.append({"nom":nom_point, "delta":delta, "plani":True})
                    delta_plani.append(delta)
                else:
                    delta = np.abs(ZTer - Zcomp)
                    dict_appuis.append({"nom":nom_point, "delta":delta, "plani":False})
                    delta_alti.append(delta)
    return dict_appuis, delta_plani, delta_alti
                
def calcul_ecart_type(delta_plani):
    if len(delta_plani)>0:
        delta_numpy = np.array(delta_plani)
        return np.std(delta_numpy)
    return 0


def check_compute_failed(path_rapport_residus):
    if not os.path.exists(path_rapport_residus):
        return True
    ori_dir = "Ori-"+path_rapport_residus.replace(".txt", "")
    if not os.path.isdir(ori_dir):
        return True
    orifiles = [i for i in os.listdir(ori_dir) if i[:11]=="Orientation"]
    if len(orifiles)==0:
        return True
    return False


path_appuis_xml = args.appuis
path_rapport_residus = args.report_residuals

if check_compute_failed(path_rapport_residus):
    # Si le calcul est un échec, alors on retire l'image du chantier
    logger.warning("Echec du calcul")
    image_name = path_rapport_residus.split(".")[0]+".tif"
    if os.path.exists(image_name):
        os.makedirs("echec_campari", exist_ok=True)
        shutil.move(image_name, os.path.join("echec_campari", image_name))
else:

    #On parcourt la liste des points d'appuis et on les sépare en deux catégories : ceux qui sont dépondérés en plani et les autres
    liste_alti, liste_plani = lecture_appui_xml(path_appuis_xml)
    

    #On calcule les résidus pour chaque point d'appui
    dict_appuis, delta_plani, delta_alti = lecture_rapport_residus(path_rapport_residus, liste_plani)
    logger.info("Nombre de points alti : {}".format(len(delta_alti)))
    logger.info("Nombre de points plani : {}".format(len(delta_plani)))

    #On calcule les écart-types pour les points plani et les points alti
    ecart_type_plani = calcul_ecart_type(delta_plani)
    ecart_type_alti = calcul_ecart_type(delta_alti)
    logger.info("Ecart-type des points plani : {} mètres".format(ecart_type_plani))
    logger.info("Ecart-type des points alti : {} mètres".format(ecart_type_alti))

