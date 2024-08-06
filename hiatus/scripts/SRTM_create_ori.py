import argparse
from osgeo import gdal
import numpy as np

parser = argparse.ArgumentParser(description="Crée le fichier ori pour une image tif. Utilisé dans l'appariement avec le SRTM")
parser.add_argument('--input_image', default='', help='Image dont il faut créer le fichier ori')
parser.add_argument('--output_ori', default='', help='Chemin où sauvegarder le fichier ori')
args = parser.parse_args()



inputds = gdal.Open(args.input_image)
geoTransform = inputds.GetGeoTransform()
image = inputds.GetRasterBand(1).ReadAsArray()

with open(args.output_ori, 'w') as out:
    out.write("CARTO\n")
    out.write("{} {}\n".format(geoTransform[0]*1000, geoTransform[3]*1000))
    out.write("0\n")
    out.write("{} {}\n".format(image.shape[1], image.shape[0]))
    out.write("{} {}\n".format(np.abs(geoTransform[1])*1000, np.abs(geoTransform[5])*1000))