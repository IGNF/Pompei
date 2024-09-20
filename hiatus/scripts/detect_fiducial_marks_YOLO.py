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

from ultralytics import YOLO
import cv2
import numpy as np
from geojson import Point, Feature, FeatureCollection
import geojson
import os
from lxml import etree
import argparse
import log # Chargement des configurations des logs
import logging

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Recherche automatique des repères de fond de chambre qui sont sous forme de targets")
parser.add_argument('--nb_points', help='Nombre de repères de fond de chambre à trouver')
parser.add_argument('--scripts', help='Répertoire contenant les scripts')
args = parser.parse_args()


def detect_image_maitresse(nom_image, model):
    """
    On détecte les repères de fond de chambre sur l'ensemble de l'image en parcourant des dalles de 640x640 pixels 
    avec un recouvrement de 320 pixels entre chaque dalle.
    On ne conserve que les points pour lesquels la confiance est supérieure à 0.9.
    On ne conserve que les points dont la boîte englobante est pratiquement un carré 
    (pour éviter de garder les points qui ont été trouvés lorsque la cible se trouvait en bordure d'une dalle)
    """
    im2 = cv2.imread(nom_image)
    resultats = []
    for i in range(0, im2.shape[0], 320):
        for j in range(0, im2.shape[1], 320):
            image = im2[i:i+640, j:j+640, :]
            results = model.predict(source=image)

            for result in results:
                boite = result.boxes
                if boite.shape[0] != 0:
                    for k in range(boite.shape[0]):
                        confidence = float(boite.conf[k].squeeze())
                        boite_xywh = boite.xywh[k].squeeze()
                        w = float(boite_xywh[2])
                        h = float(boite_xywh[3])
                        colonne = float(boite_xywh[0])+j
                        ligne = float(boite_xywh[1])+i


                        if confidence >= 0.9 and np.abs(h-w) <= 5:
                            resultats.append({"confidence": confidence, "w":w, "h":h, "ligne":ligne, "colonne":colonne})  
    logger.debug(f"Détections sur l'image maîtresse : {resultats}")

    return resultats


def detect(nom_image, points_image_maitresse, model):
    """
    Pour chaque image, on détecte les repères de fond de chambre uniquement dans un carré de 640 pixels de côté autour de 
    l'endroit où les repères de fond de chambre ont été trouvés sur l'image maîtresse. 
    Cela permet d'éviter de parcourir toutes les images, mais seulement les parties intéressantes.
    On ne conserve que les points pour lesquels la confiance est supérieure à 0.8.
    On ne conserve que les points dont la boîte englobante est pratiquement un carré 
    (pour éviter de garder les points qui ont été trouvés lorsque la cible se trouvait en bordure d'une dalle)
    """
    im2 = cv2.imread(nom_image)
    resultats = []
    for point in points_image_maitresse:
        ligne_min = int(point["ligne"]-320)
        ligne_max = int(point["ligne"]+320)
        colonne_min = int(point["colonne"]-320)
        colonne_max = int(point["colonne"]+320)
        if ligne_min < 0:
            ligne_max = 640
            ligne_min = 0
        elif ligne_max >= im2.shape[0]:
            ligne_min = im2.shape[0]-640
            ligne_max = im2.shape[0]
        if colonne_min < 0:
            colonne_max = 640
            colonne_min = 0
        if colonne_max >= im2.shape[1]:
            colonne_min = im2.shape[1]-640
            colonne_max = im2.shape[1]
        image = im2[ligne_min:ligne_max, colonne_min:colonne_max]
        results = model.predict(source=image)
        for result in results:
            boite = result.boxes
            if boite.shape[0] != 0:
                for k in range(boite.shape[0]):
                    confidence = float(boite.conf[k].squeeze())
                    boite_xywh = boite.xywh[k].squeeze()
                    w = float(boite_xywh[2])
                    h = float(boite_xywh[3])
                    colonne = float(boite_xywh[0])+colonne_min
                    ligne = float(boite_xywh[1])+ligne_min

                    if confidence >= 0.8 and np.abs(h-w) <= 10:
                        resultats.append({"confidence": confidence, "w":w, "h":h, "ligne":ligne, "colonne":colonne})  
    return resultats


            

def trier_points(resultats):
    """
    Pour chaque point trouvé, on l'associe aux autres points qui sont à moins de 100 pixels.
    Cela permettra par la suite de n'en garder qu'un par zone
    """
    points_tries = []
    for point_detecte in resultats:
        trouve = False
        for id in points_tries:
            for point_trie in id:
                distance = np.sqrt((point_trie["colonne"]-point_detecte["colonne"])**2 + (point_trie["ligne"] - point_detecte["ligne"])**2)
                if distance < 100 and not trouve:
                    id.append(point_detecte)
                    trouve = True
        if not trouve:
            points_tries.append([point_detecte])
    return points_tries

def selectionner_points(points_tries):
    """
    Pour chaque zone, on conserve le point avec la confiance la plus élevée
    """
    points_conserves = []
    for id in points_tries:
        point_conserve = id[0]
        for point in id:
            if point["confidence"] >= point_conserve["confidence"]:
                point_conserve = point
        points_conserves.append(point_conserve)
    return points_conserves

def save_geojson(liste_points, chemin_sauvegarde):
    """
    Pour chaque image, on enregistre les points sous format geojson.
    Cette fonction n'a qu'un but de contrôle, elle est inutile pour le reste de la chaîne de traitement
    """
    for nom_image in liste_points.keys():
        points_conserves = liste_points[nom_image]
        liste_features = []
        nom_image_geojson = nom_image.replace("tif", "geojson")
        for point in points_conserves:
            my_point = Point((point["colonne"], -point["ligne"]))
            feature = Feature(geometry=my_point, properties={"confidence": point["confidence"], "w":point["w"], "h":point["h"]})
            liste_features.append(feature)
        feature_collection = FeatureCollection(liste_features)
        with open(os.path.join(chemin_sauvegarde, nom_image_geojson), "w") as f:
            f.write(geojson.dumps(feature_collection))

def save_xml(liste_points):
    """
    On sauvegarde les points sous format xml lisible par MicMac pour la commande ResampFid
    """

    liste_probleme = []
    for nom_image in liste_points.keys():
        root = etree.Element("root")
        MesureAppuiFlottant1Im = etree.SubElement(root, "MesureAppuiFlottant1Im")
        NameIm = etree.SubElement(MesureAppuiFlottant1Im, "NameIm")
        NameIm.text = nom_image

        PrecPointeByIm = etree.SubElement(MesureAppuiFlottant1Im, "PrecPointeByIm")
        PrecPointeByIm.text = "1"

        compte_point = 1
        for point in liste_points[nom_image]:
            OneMesureAF1I = etree.SubElement(MesureAppuiFlottant1Im, "OneMesureAF1I")
            NamePt = etree.SubElement(OneMesureAF1I, "NamePt")
            NamePt.text = str(compte_point)

            PtIm = etree.SubElement(OneMesureAF1I, "PtIm")
            PtIm.text = "{} {}".format(point["colonne"], point["ligne"])
            compte_point += 1

        logger.debug(f"Image {nom_image} : {liste_points[nom_image]}")

        #Si le nombre de points trouvés ne correspond à celui qui aurait dû être trouvé, alors l'utilisateur est invité à saisir les points avec Micmac
        if compte_point != int(args.nb_points)+1:
            logger.warning("{} points ont été trouvés sur l'image {}.".format(str(compte_point-1), nom_image))
            liste_probleme.append(nom_image)
        
        else:
            with open(os.path.join("Ori-InterneScan", "MeasuresIm-{}.xml".format(nom_image)), "w") as f:
                f.write('<?xml version="1.0" ?>')
                f.write(str(etree.tostring(MesureAppuiFlottant1Im,encoding='unicode')))
    return liste_probleme

def chercher_image_maitresse(model):
    """
    On parcourt toutes les images jusqu'à en trouver une pour laquelle YOLO trouve le bon nombre de repères de fond de chambre.
    Cette image devient l'image maîtresse pour la suite
    """
    liste_points = {}
    images = [i for i in os.listdir() if i[-4:]==".tif"]
    pas_trouve = True
    while pas_trouve and len(images) > 0:
        image_maitresse = images.pop()
        logger.info(f"Image maitresse : {image_maitresse}")

        # On détecte les repères de fond de chambre sur l'image maîtresse avec Yolo
        resultats = detect_image_maitresse(image_maitresse, model)

        # On trie les points trouvés afin de regrouper ceux qui correspondent au même repère de fond de chambre
        points_tries = trier_points(resultats)
        # Pour chaque repère de fond de chambre, on conserve le point qui a la probabilité la plus élevée
        points_image_maitresse = selectionner_points(points_tries)
        logger.debug(f"Détections sur l'image maîtresse après filtrage : {points_image_maitresse}")
        if len(points_image_maitresse) == int(args.nb_points):
            pas_trouve = False
            logger.debug(f"{len(points_image_maitresse)} ont été trouvés au lieu de {int(args.nb_points)}. On essaye avec une nouvelle image maîtresse")
        else:
            logger.debug(f"Le bon nombre de points ont été trouvés sur l'image maîtresse")

    if len(points_image_maitresse) != int(args.nb_points):
        logger.error("Erreur : sur aucune image, le nombre exact de repères de fond de chambre n'a été trouvé. Essayez avec la méthode par corrélation de MicMac")
    
    liste_points[image_maitresse] = points_image_maitresse

    return liste_points, points_image_maitresse, image_maitresse

def SaisieAppuisInit(liste_probleme):
    if len(liste_probleme) > 0:
        logger.warning(f"Sur les images suivantes, le bon nombre de repères de fond de chambre n'ont pas été trouvés. Vous devrez les saisir à la main : {liste_probleme}")
    for image in liste_probleme:
        commande = "mm3d SaisieAppuisInit {} NONE id_reperes.txt MeasuresIm-{}.xml Gama=2".format(image, image)
        os.system(commande)

def SaisieAppuisInit_to_InterneScan(liste_probleme):

    
    # Quand la détection a été faite par YOLO et qu'il faut repointer des repères de fond de chambre, l'opérateur ne 
    # sait pas forcément dans quel ordre repointer les points. Pour ne pas s'embêter avec cela, on associe à chaque point le point
    # le plus proche dans un fichier xml d'une image pour laquelle tous les repères ont été trouvés
    
    #On récupère la position des points dans un fichier xml pour lequel la détection a bien marché
    xml_ref_files = [i for i in os.listdir("Ori-InterneScan") if "MeasuresIm" in i]

    #Si les repères n'ont été trouvés sur aucune image, alors on prend comme référence l'une des images sur laquelle l'utilisateur a saisi la position des repères
    if len(xml_ref_files) == 0:
        xml_ref_files = [i for i in os.listdir() if "MeasuresIm" in i and "S2D.xml" in i]
        xml_ref_file = xml_ref_files[0]
        xml_ref_tree = etree.parse(xml_ref_file)
    else:
        xml_ref_file = xml_ref_files[0]
        xml_ref_tree = etree.parse(os.path.join("Ori-InterneScan", xml_ref_file))
    xml_ref_root = xml_ref_tree.getroot()
    points = {}
    for mesure in xml_ref_root.findall(".//OneMesureAF1I"):
        NamePt = mesure.find("NamePt").text
        PtIm = mesure.find("PtIm").text.split()
        points[NamePt] = [float(PtIm[0]), float(PtIm[1])]


    # On parcourt les images qui ont posé problème
    for image in liste_probleme:
        MesureAppui = etree.Element("MesureAppuiFlottant1Im")
        idReperes = etree.SubElement(MesureAppui, "NameIm")
        idReperes.text = image

        PrecPointeByIm = etree.SubElement(MesureAppui, "PrecPointeByIm")
        PrecPointeByIm.text = str(0.5)



        listRep=[]
        listPtImCoor=[]
        #On parcourt les fichiers contenant les positions des repères de fond de chambre
        xml_file = "MeasuresIm-{}-S2D.xml".format(image)
        tree = etree.parse(xml_file)
        root = tree.getroot()
        #On récupère la position des points
        for PtIm in root.getiterator("PtIm"):
            listPtImCoor.append(PtIm.text)

        
            #On recherche l'id du point le plus proche dans un fichier xml de référence 
            x = float(PtIm.text.split()[0])
            y = float(PtIm.text.split()[1])

            dist_min = 1e15
            id_min = 0
            for id in points.keys():
                distance = np.sqrt((x-points[id][0])**2 + (y-points[id][1])**2)
                if distance < dist_min:
                    id_min = id
                    dist_min = distance
            listRep.append(id_min)



        for i in range(len(listRep)):        
            OneMesure = etree.SubElement(MesureAppui, "OneMesureAF1I")
            NamePt = etree.SubElement(OneMesure, "NamePt")
            NamePt.text=listRep[i]
            PtIm = etree.SubElement(OneMesure, "PtIm")
            PtIm.text=listPtImCoor[i]


        with open("Ori-InterneScan/MeasuresIm-{}.xml".format(image),"w") as f:
            f.write("<?xml version=\"1.0\" ?>\n")
            f.write(str(etree.tostring(MesureAppui,encoding='unicode')))


def run(chemin_sauvegarde):
    """
    Fonction pour récupérer les repères de fond de chambre
    """

    
    # On charge le modèle YOLO entraîné
    model = YOLO(os.path.join(args.scripts, "best.pt"))

    # On recherche l'image maîtresse : la première pour laquelle on trouve le bon nombre de repères de fond de chambre
    liste_points, points_image_maitresse, image_maitresse = chercher_image_maitresse(model)
    
    

    # On parcourt les images secondaires
    images_secondaires = [i for i in os.listdir() if i[-4:]==".tif" and i!=image_maitresse]
    for image_secondaire in images_secondaires:
        logger.info(f"image_secondaire : {image_secondaire}")
        # On détecte les repères de fond de chambre sur l'image secondaire avec Yolo
        resultats = detect(image_secondaire, points_image_maitresse, model)
        # On trie les points trouvés afin de regrouper ceux qui correspondent au même repère de fond de chambre
        points_tries = trier_points(resultats)
        # Pour chaque repère de fond de chambre, on conserve le point qui a la probabilité la plus élevée
        points_image_secondaire = selectionner_points(points_tries)
        liste_points[image_secondaire] = points_image_secondaire
    
    # On sauvegarde les points sous format geojson (pour contrôler les résultats)
    save_geojson(liste_points, chemin_sauvegarde)
    # On sauvegarde les points sous format xml
    liste_probleme = save_xml(liste_points)
    SaisieAppuisInit(liste_probleme)
    SaisieAppuisInit_to_InterneScan(liste_probleme)


chemin_sauvegarde = "Ori-InterneScan_geojson"
if not os.path.exists(chemin_sauvegarde):
    os.makedirs(chemin_sauvegarde)

if not os.path.exists("Ori-InterneScan"):
    os.makedirs("Ori-InterneScan")
run(chemin_sauvegarde)
