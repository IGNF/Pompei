"""
Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/

File main authors:
- Célestin Huet

This file is part of Hiatus: https://github.com/IGNF/Hiatus

Hiatus is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Hiatus is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Hiatus. If not, see <https://www.gnu.org/licenses/>.
"""

from lxml import etree
import numpy as np
import argparse
import os
import log # Chargement des configurations des logs
import logging

logger = logging.getLogger("root")


parser = argparse.ArgumentParser(description="Suppression des points d'appuis les moins bons")
parser.add_argument('--GCP', help="Points d'appuis de la BD Ortho")
parser.add_argument('--S2D', help="Points d'appuis de l'orthomosaïque")
parser.add_argument('--GCP_save', help="Points d'appuis de la BD Ortho")
parser.add_argument('--S2D_save', help="Points d'appuis de l'orthomosaïque")
parser.add_argument('--report_residuals', help="Rapport Campari sur les résidus")
parser.add_argument('--factor', help="Seuil sur l'écart-type")
parser.add_argument('--delete', help="Supprimer les points d'appuis", type=bool, default=True)# Si false, permet de voir uniquement les écart-types et erreur sur les points d'appuis. Utile juste après la dernière aéro
args = parser.parse_args()

def read_GCP(path):
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


def read_report_residuals(path, liste_plani):

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
                
def compute_std(delta_plani):
    if len(delta_plani)>0:
        delta_numpy = np.array(delta_plani)
        return np.std(delta_numpy)
    return 0

def define_deleted_GCP(dict_appuis, ecart_type_plani, ecart_type_alti, factor):
    liste_points_a_supprimer = []
    compte_plani = 0
    compte_alti = 0
    for point in dict_appuis:
        if point["plani"]:
            if point["delta"] > ecart_type_plani * factor:
                liste_points_a_supprimer.append(point["nom"])
                compte_plani += 1
        else:
            if point["delta"] > ecart_type_alti * factor:
                liste_points_a_supprimer.append(point["nom"])
                compte_alti += 1
    logger.info("Points plani supprimés : ", compte_plani)
    logger.info("Points alti supprimés : ", compte_alti)
    logger.info("Points supprimés : ", len(liste_points_a_supprimer))
    with open(os.path.join("reports", "rapport_complet.txt"), 'a') as f:
        f.write("Points plani supprimés : {}\n".format(compte_plani))
        f.write("Points alti supprimés : {}\n".format(compte_alti))
        f.write("Points supprimés : {}\n".format(len(liste_points_a_supprimer)))
        f.write("\n\n\n")


    return liste_points_a_supprimer


def delete_GCP(liste_points_a_supprimer, path_appuis, path_appuis_save):
    tree = etree.parse(path_appuis)
    root = tree.getroot()
    liste_appuis = root.findall(".//OneAppuisDAF")
    
    #On supprime les points d'appuis qui sont dans la liste des points à supprimer
    for appui in liste_appuis:
        if appui.find("NamePt").text in liste_points_a_supprimer:
            appui.getparent().remove(appui)

    #On sauvegarde le fichier
    with open(path_appuis_save, "w") as f:
        f.write("<?xml version=\"1.0\" ?>\n")
        f.write(str(etree.tostring(tree, encoding='unicode')))

def delete_GCP_S2D(liste_points_a_supprimer, path_S2D, path_S2D_save):
    #On supprime les points d'appuis qui ont été supprimés dans GCP.xml
    tree = etree.parse(path_S2D)
    root = tree.getroot()

    for appui in root.findall(".//OneMesureAF1I"):
        nom_point = appui.find("NamePt").text
        if nom_point in liste_points_a_supprimer:
            appui.getparent().remove(appui)

    logger.info("Nombre de points d'appuis restants : ")
    for mesureImage in root.findall(".//MesureAppuiFlottant1Im"):
        image = mesureImage.find(".//NameIm").text
        nb_points = len(mesureImage.findall(".//OneMesureAF1I"))
        logger.info("{} : {}".format(image, nb_points))

    #On sauvegarde le fichier
    with open(path_S2D_save, "w") as f:
        f.write("<?xml version=\"1.0\" ?>\n")
        f.write(str(etree.tostring(tree, encoding='unicode')))


path_appuis_xml = args.GCP
path_appuis_save = args.GCP_save
path_rapport_residus = args.report_residuals
path_S2D = args.S2D
path_S2D_save = args.S2D_save

factor = float(args.factor)

#On parcourt la liste des points d'appuis et on les sépare en deux catégories : ceux qui sont dépondérés en plani et les autres
liste_alti, liste_plani = read_GCP(path_appuis_xml)
logger.info("Nombre de points alti : {}".format(len(liste_alti)))
logger.info("Nombre de points plani : {}".format(len(liste_plani)))

#On calcule les résidus pour chaque point d'appui
dict_appuis, delta_plani, delta_alti = read_report_residuals(path_rapport_residus, liste_plani)

#On calcule les écart-types pour les points plani et les points alti
ecart_type_plani = compute_std(delta_plani)
ecart_type_alti = compute_std(delta_alti)
logger.info("Ecart-type des points plani : {} mètres".format(ecart_type_plani))
logger.info("Ecart-type des points alti : {} mètres".format(ecart_type_alti))

with open(os.path.join("reports", "rapport_complet.txt"), 'a') as f:
    f.write("Nombre de points plani : {}\n".format(len(liste_plani)))
    f.write("Nombre de points alti : {}\n".format(len(liste_alti)))
    f.write("Ecart-type des points plani : {} mètres\n".format(ecart_type_plani))
    f.write("Ecart-type des points alti : {} mètres\n".format(ecart_type_alti))


if args.delete:
    #On établit la liste des points d'appuis à supprimer 
    liste_points_a_supprimer = define_deleted_GCP(dict_appuis, ecart_type_plani, ecart_type_alti, factor)

    #On supprime les points d'appuis du fichier GCP.xml
    delete_GCP(liste_points_a_supprimer, path_appuis_xml, path_appuis_save)

    #On supprime les points d'appuis du fichier GCP-S2D.xml
    delete_GCP_S2D(liste_points_a_supprimer, path_S2D, path_S2D_save)