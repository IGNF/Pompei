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
import log # Chargement des configurations des logs
import logging

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Effectue la différence entre le MNS actuel et celui issu de l'orthomosaïque")

parser.add_argument('--orthoHistoPath', help="Dossier Ortho-MEC-Malt-Final-Corr/ortho_sans_masque contenant l'ortho finale")
parser.add_argument('--orthoHistoResultPath', help="Dossier Ortho-MEC-Malt-Final-Corr où il faudra mettre les orthos filtrées par le masque")
parser.add_argument('--masque', help="Masque de l'ortho issu de l'orthomosaïque")
parser.add_argument('--metadata', help="Répertoire contenant le fichier EPSG.txt")
args = parser.parse_args()



def open_ortho(path):
    #On ouvre le MNS
    inputds = gdal.Open(path)

    #On récupère l'footprintet la résolution du MNS
    geoTransform = inputds.GetGeoTransform()
    e_min = geoTransform[0]
    n_max = geoTransform[3]
    res_col = int(geoTransform[1]*1000)/1000
    res_ligne = int(geoTransform[5]*1000)/1000
    inputlyr = np.array(inputds.ReadAsArray())
    nb_bands = inputds.RasterCount
    if nb_bands == 1:
        inputlyr = np.reshape(inputlyr, (inputlyr.shape[0], inputlyr.shape[1], nb_bands))
    else:
        inputlyr = np.rollaxis(inputlyr, 0, 3)
    e_max = e_min + res_col * inputlyr.shape[1]
    n_min = n_max + res_ligne * inputlyr.shape[0]
    return inputlyr, [e_min, e_max, n_min, n_max, res_col, res_ligne]

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
    if array.dtype == np.float32:
        outRaster = driver.Create(output, array.shape[1], array.shape[0], 1, gdal.GDT_Float32)
    else:
        outRaster = driver.Create(output, array.shape[1], array.shape[0], array.shape[2], gdal.GDT_Byte)
    outRaster.SetGeoTransform(inputds.GetGeoTransform())
    for i in range(array.shape[2]):
        outband = outRaster.GetRasterBand(i+1)
        outband.WriteArray(array[:, :, i])

    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(getEPSG(metadata))
    outRaster.SetProjection(outSpatialRef.ExportToWkt())
    outband.FlushCache()


def get_ortho_histo(path):
    #On récupère la liste des tuiles de l'ortho historique
    liste = []
    for file in os.listdir(path):
        if ("Orthophotomosaic_Tile" in file or "MNS_Final_Num8_DeZoom2_STD-MALT" in file or "MNS_Final_Num9_DeZoom2_STD-MALT" in file) and file[-4:] == ".tif":
            liste.append(file)
    #On trie la liste pour que la tuile la plus au nord-ouest se trouve en premier
    return sorted(liste)


def get_mask(masque, coordsMNSHisto, coordsChantier):

    #On ouvre le masque
    masque_array, coords_masque = open_ortho(masque)

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
        logger.warning(f"Pas d'emprise commune : {footprint_commune} ! ")
    
    return masque_extracted


def apply_mask():
    liste_MNS_histo = get_ortho_histo(orthoHistoPath)
    for i in range(len(liste_MNS_histo)):
        OrthoHistoFile = liste_MNS_histo[i]

        #On ouvre l'ortho historique
        orthoHisto, coordsOrthoHisto = open_ortho(os.path.join(orthoHistoPath, OrthoHistoFile))

        #On conserve les coordonnées de la dalle la plus au nord-ouest
        if i == 0:
            coordsChantier = coordsOrthoHisto.copy()
            
        #On récupère la partie du masque qui correspond à la tuile de l'ortho historique
        masque_array = get_mask(masque, coordsOrthoHisto, coordsChantier)

        #On rééchantillonne le masque
        masque_array_resized = cv2.resize(masque_array, dsize=(orthoHisto.shape[1],orthoHisto.shape[0]))

        #On applique le masque sur l'ortho
        if orthoHisto.dtype == np.float32:#Cas du MNS
            orthoHisto[masque_array_resized==0] = np.nan
        else:#Cas de l'ortho car np.nan n'est pas autorisé pour sauvegarder en byte
            orthoHisto[masque_array_resized==0] = 0

        #On sauvegarde le résultat
        save(orthoHisto, os.path.join(orthoHistoPath, OrthoHistoFile), os.path.join(orthoHistoResultPath, OrthoHistoFile))

orthoHistoPath = args.orthoHistoPath
orthoHistoResultPath = args.orthoHistoResultPath
masque = args.masque
metadata = args.metadata

#On récupère toutes les tuiles du MNS historique
apply_mask()
