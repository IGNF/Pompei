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



def openMNS(path):
    #On ouvre le MNS
    inputds = gdal.Open(path)

    #On récupère l'emprise et la résolution du MNS
    geoTransform = inputds.GetGeoTransform()
    e_min = geoTransform[0]
    n_max = geoTransform[3]
    res_col = int(geoTransform[1]*1000)/1000
    res_ligne = int(geoTransform[5]*1000)/1000
    inputlyr = np.array(inputds.GetRasterBand(1).ReadAsArray())
    e_max = e_min + res_col * inputlyr.shape[1]
    n_min = n_max + res_ligne * inputlyr.shape[0]
    return inputlyr, [e_min, e_max, n_min, n_max, res_col, res_ligne]


def getMNS(mnsPath):
    #On récupère la liste des dalles du MNS
    liste_files = os.listdir(mnsPath)
    listeMNS = [os.path.join(mnsPath, i) for i in liste_files if i[-4:]==".tif"]
    return listeMNS

def calculer_emprise_commune(coordsMNSHisto, coordsMNS):
    #On récupère la plus petite emprise commune aux deux images
    e_min = max(coordsMNSHisto[0], coordsMNS[0])
    e_max = min(coordsMNSHisto[1], coordsMNS[1])
    n_min = max(coordsMNSHisto[2], coordsMNS[2])
    n_max = min(coordsMNSHisto[3], coordsMNS[3])
    return [e_min, e_max, n_min, n_max]

def calculer_extraction(coordsMNSHisto, emprise_commune):
    #On calcule les coordonnées en pixel de l'image correspondant à l'emprise
    colonne_min = int((emprise_commune[0] - coordsMNSHisto[0]) / coordsMNSHisto[4])
    colonne_max = int((emprise_commune[1] - coordsMNSHisto[0]) / coordsMNSHisto[4])
    ligne_max = int((emprise_commune[2] - coordsMNSHisto[3]) / coordsMNSHisto[5])
    ligne_min = int((emprise_commune[3] - coordsMNSHisto[3]) / coordsMNSHisto[5])
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
        mns, coordsMNS = openMNS(mns_dalle)
        #On calcule son emprise commune avec le MNS historique
        emprise_commune = calculer_emprise_commune(coordsMNSHisto, coordsMNS)
        
        #On vérifie qu'il existe bien une surface commune
        if emprise_commune[0] < emprise_commune[1] and emprise_commune[2] < emprise_commune[3]:
            #On calcule les coordonnées en pixel de l'emprise commune sur le MNS historique
            extractionMNSHisto = calculer_extraction(coordsMNSHisto, emprise_commune) 
            #On calcule les coordonnées en pixel de l'emprise commune sur la dalle du MNS actuel
            extractionMNS= calculer_extraction(coordsMNS, emprise_commune)
            #On extrait l'emprise commune du MNS historique et de la dalle du MNS actuel
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


def get_masque(masque, coordsMNSHisto, coordsChantier):

    #On ouvre le masque
    masque_array, coords_masque = openMNS(masque)

    #On modifie coordsChantier pour obtenir les métadonnées correspondant à l'ensemble du chantier
    coordsChantier[1] = masque_array.shape[1] * coordsChantier[4] + coordsChantier[0]
    coordsChantier[2] = masque_array.shape[0] * coordsChantier[5] + coordsChantier[3]

    #On calcule l'emprise commune entre le chantier et la tuile du MNS Histo
    emprise_commune = calculer_emprise_commune(coordsMNSHisto, coordsChantier)

    if emprise_commune[0] < emprise_commune[1] and emprise_commune[2] < emprise_commune[3]:
            #On calcule les coordonnées en pixel de l'emprise commune sur le MNS historique
            extractionMasque = calculer_extraction(coordsChantier, emprise_commune) 
            masque_extracted = masque_array[extractionMasque[2]:extractionMasque[3], extractionMasque[0]:extractionMasque[1]]
    else:
        print("Pas d'emprise commune !")
        print(emprise_commune)
    
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
    mnsHisto, coordsMNSHisto = openMNS(os.path.join(mnsHistoPath, MNSHistoFile))

    #On conserve les coordonnées de la dalle la plus au nord-ouest
    if i == 0:
        coordsChantier = coordsMNSHisto.copy()
        
    #On récupère la liste des dalles du MNS actuel
    MNSFiles = getMNS(mnsPath)

    #On calcule la différence entre le MNS issu de l'orthomosaïque et le MNS actuel
    mnsHisto = process(mnsHisto, coordsMNSHisto, MNSFiles)

    #On récupère la partie du masque qui correspond à la tuile du MNS historique
    masque_array = get_masque(masque, coordsMNSHisto, coordsChantier)

    #On rééchantillonne le masque
    masque_array_resized = cv2.resize(masque_array, dsize=(mnsHisto.shape[1],mnsHisto.shape[0]))

    #On applique le masque sur le calcul de différence
    mnsHisto[masque_array_resized==0] = np.nan

    #On sauvegarde le résultat
    save(mnsHisto, os.path.join(mnsHistoPath, MNSHistoFile), os.path.join(mnsHistoPath, basename + "_difference.tif"))
