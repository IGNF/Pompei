import os
import argparse
from osgeo import gdal
import numpy as np

parser = argparse.ArgumentParser(description="Supprime les dalles noires pour éviter d'y faire la recherche de points d'appuis")

parser.add_argument('--path', help="Répertoire contenant les dalles")
parser.add_argument('--seuil_value', help="Valeur maximale d'un pixel pour qu'il soit considéré comme sans information")
parser.add_argument('--seuil_prop', help="Proportion de pixels sans informations au-delà de laquelle l'image est supprimée")
args = parser.parse_args()

liste_images = os.listdir(args.path)
compte = 0
for image in liste_images:
    if image[-4:] == ".tif":
        inputds = gdal.Open(os.path.join(args.path, image))
        inputlyr = np.array(inputds.GetRasterBand(1).ReadAsArray())
        array_count = np.zeros(inputlyr.shape)
        array_count[inputlyr<=float(args.seuil_value)] = 1
        if np.sum(array_count) / (inputlyr.shape[0] * inputlyr.shape[1]) >= float(args.seuil_prop):
            os.remove(os.path.join(args.path, image))
            compte += 1
print("{} dalles ont été supprimées".format(compte))