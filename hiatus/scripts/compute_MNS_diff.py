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

from osgeo import gdal, osr
import numpy as np
import os
import cv2
import argparse
from tools import getEPSG

parser = argparse.ArgumentParser(description="Effectue la différence entre le MNS actuel et celui issu de l'orthomosaïque")

parser.add_argument('--mnsHistoPath', help="Dossier MEC-Malt-Final contenant le MNS final")
parser.add_argument('--mnsPath', help='Dossier contenant le MNS actuel')
parser.add_argument('--masque', help="Masque du MNS issu de l'orthomosaïque")
parser.add_argument('--metadata', help="Répertoire contenant EPSG.txt")
args = parser.parse_args()



def open_MNS(path):
    #On ouvre le MNS
    inputds = gdal.Open(path)

    #On récupère l'footprintet la résolution du MNS
    geoTransform = inputds.GetGeoTransform()
    e_min = geoTransform[0]
    n_max = geoTransform[3]
    res_col = int(geoTransform[1]*1000)/1000
    res_ligne = int(geoTransform[5]*1000)/1000
    inputlyr = np.array(inputds.GetRasterBand(1).ReadAsArray())
    e_max = e_min + res_col * inputlyr.shape[1]
    n_min = n_max + res_ligne * inputlyr.shape[0]
    return inputlyr, [e_min, e_max, n_min, n_max, res_col, res_ligne]


def get_MNS(mnsPath):
    #On récupère la liste des dalles du MNS
    liste_files = os.listdir(mnsPath)
    listeMNS = [os.path.join(mnsPath, i) for i in liste_files if i[-4:]==".tif"]
    return listeMNS

def compute_intersection_footprint(coordsMNSHisto, coordsMNS):
    #On récupère la plus petite footprintcommune aux deux images
    e_min = max(coordsMNSHisto[0], coordsMNS[0])
    e_max = min(coordsMNSHisto[1], coordsMNS[1])
    n_min = max(coordsMNSHisto[2], coordsMNS[2])
    n_max = min(coordsMNSHisto[3], coordsMNS[3])
    return [e_min, e_max, n_min, n_max]

def compute_extraction(coordsMNSHisto, footprint_commune):
    #On calcule les coordonnées en pixel de l'image correspondant à l'footprint
    colonne_min = int((footprint_commune[0] - coordsMNSHisto[0]) / coordsMNSHisto[4])
    colonne_max = int((footprint_commune[1] - coordsMNSHisto[0]) / coordsMNSHisto[4])
    ligne_max = int((footprint_commune[2] - coordsMNSHisto[3]) / coordsMNSHisto[5])
    ligne_min = int((footprint_commune[3] - coordsMNSHisto[3]) / coordsMNSHisto[5])
    return [colonne_min, colonne_max, ligne_min, ligne_max]

def save(array, path, output):
    #On sauvegarde l'image
    inputds = gdal.Open(path)

    driver = gdal.GetDriverByName('GTiff')
    outRaster = driver.Create(output, array.shape[1], array.shape[0], 1, gdal.GDT_Float32)
    outRaster.SetGeoTransform(inputds.GetGeoTransform())
    outband = outRaster.GetRasterBand(1)
    outband.WriteArray(array)

    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(EPSG)
    outRaster.SetProjection(outSpatialRef.ExportToWkt())
    outband.FlushCache()


def process(mnsHisto, coordsMNSHisto, MNSFiles):
    #On calcule la différence dalle par dalle

    mnsDiff = np.zeros(mnsHisto.shape)

    #On parcourt toutes les dalles du MNS
    for mns_dalle in MNSFiles:
        #On ouvre une dalle du MNS
        mns, coordsMNS = open_MNS(mns_dalle)
        #On calcule son footprintcommune avec le MNS historique
        footprint_commune = compute_intersection_footprint(coordsMNSHisto, coordsMNS)
        
        #On vérifie qu'il existe bien une surface commune
        if footprint_commune[0] < footprint_commune[1] and footprint_commune[2] < footprint_commune[3]:
            #On calcule les coordonnées en pixel de l'footprintcommune sur le MNS historique
            extractionMNSHisto = compute_extraction(coordsMNSHisto, footprint_commune) 
            #On calcule les coordonnées en pixel de l'footprintcommune sur la dalle du MNS actuel
            extractionMNS= compute_extraction(coordsMNS, footprint_commune)
            #On extrait l'footprintcommune du MNS historique et de la dalle du MNS actuel
            MNSHisto_extracted = mnsHisto[extractionMNSHisto[2]:extractionMNSHisto[3], extractionMNSHisto[0]:extractionMNSHisto[1]]
            MNS_extracted = mns[extractionMNS[2]:extractionMNS[3], extractionMNS[0]:extractionMNS[1]]
            
            #On rééchantillonne l'extraction du MNS actuel
            MNS_extracted_resized = cv2.resize(MNS_extracted, dsize=(MNSHisto_extracted.shape[1],MNSHisto_extracted.shape[0]) )

            #On calcule la différence
            difference = MNS_extracted_resized - MNSHisto_extracted
            mnsDiff[extractionMNSHisto[2]:extractionMNSHisto[3], extractionMNSHisto[0]:extractionMNSHisto[1]] = difference
    return mnsDiff


def get_MNS_histo(path):
    #On récupère la liste des tuiles du MNS historique
    liste = []
    for file in os.listdir(path):
        if ("MNS_Final_Num8_DeZoom2_STD-MALT" in file or "MNS_Final_Num9_DeZoom2_STD-MALT" in file) and file[-4:] == ".tif":
            liste.append(file)
    #On trie la liste pour que la tuile la plus au nord-ouest se trouve en premier
    return sorted(liste)


def get_mask(masque, coordsMNSHisto, coordsChantier):

    #On ouvre le masque
    masque_array, coords_masque = open_MNS(masque)

    #On modifie coordsChantier pour obtenir les métadonnées correspondant à l'ensemble du chantier
    coordsChantier[1] = masque_array.shape[1] * coordsChantier[4] + coordsChantier[0]
    coordsChantier[2] = masque_array.shape[0] * coordsChantier[5] + coordsChantier[3]

    #On calcule l'footprintcommune entre le chantier et la tuile du MNS Histo
    footprint_commune = compute_intersection_footprint(coordsMNSHisto, coordsChantier)

    if footprint_commune[0] < footprint_commune[1] and footprint_commune[2] < footprint_commune[3]:
            #On calcule les coordonnées en pixel de l'footprintcommune sur le MNS historique
            extractionMasque = compute_extraction(coordsChantier, footprint_commune) 
            masque_extracted = masque_array[extractionMasque[2]:extractionMasque[3], extractionMasque[0]:extractionMasque[1]]
    else:
        print("Pas d'footprintcommune !")
        print(footprint_commune)
    
    return masque_extracted


mnsHistoPath = args.mnsHistoPath
mnsPath = args.mnsPath
masque = args.masque
metadata = args.metadata


#On récupère l'EPSG du chantier
EPSG = getEPSG(metadata)

#On récupère toutes les tuiles du MNS historique
liste_MNS_histo = get_MNS_histo(mnsHistoPath)

#On parcourt chaque tuile du MNS historique
for i in range(len(liste_MNS_histo)):
    MNSHistoFile = liste_MNS_histo[i]

    basename = MNSHistoFile.split(".")[0]

    #On ouvre le MNS issu de l'orthomosaïque
    mnsHisto, coordsMNSHisto = open_MNS(os.path.join(mnsHistoPath, MNSHistoFile))

    #On conserve les coordonnées de la dalle la plus au nord-ouest
    if i == 0:
        coordsChantier = coordsMNSHisto.copy()
        
    #On récupère la liste des dalles du MNS actuel
    MNSFiles = get_MNS(mnsPath)

    #On calcule la différence entre le MNS issu de l'orthomosaïque et le MNS actuel
    mnsHisto = process(mnsHisto, coordsMNSHisto, MNSFiles)

    #On récupère la partie du masque qui correspond à la tuile du MNS historique
    masque_array = get_mask(masque, coordsMNSHisto, coordsChantier)

    #On rééchantillonne le masque
    masque_array_resized = cv2.resize(masque_array, dsize=(mnsHisto.shape[1],mnsHisto.shape[0]))

    #On applique le masque sur le calcul de différence
    mnsHisto[masque_array_resized==0] = np.nan

    #On sauvegarde le résultat
    save(mnsHisto, os.path.join(mnsHistoPath, MNSHistoFile), os.path.join(mnsHistoPath, basename + "_difference.tif"))
