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