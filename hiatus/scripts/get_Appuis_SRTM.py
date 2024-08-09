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

import argparse
from osgeo import gdal


parser = argparse.ArgumentParser(description="Convertit les coordonnées des points d'appuis du repère image au repère terrain")
parser.add_argument('--input_points', default='', help='Points trouvés dans PastisMEC_SRTM/MEC-Malt-Abs-Ratafia')
parser.add_argument('--output_points', default='', help='Fichier TraitementAPP/resultpi')
parser.add_argument('--input_image', default='', help="image du SRTM pour récupérer le géoréférencement des points")
args = parser.parse_args()



def get_georeferencement(path):
    inputds = gdal.Open(path)
    geoTransform = inputds.GetGeoTransform()
    E0 = geoTransform[0]
    N0 = geoTransform[3]
    resE = geoTransform[1]/2 #On divise par deux car il s'agit ici de la résolution avant le rééchantillonnage à 15 mètres
    resN = geoTransform[5]/2 
    return E0, N0, resE, resN

def reprojeter(input, output, E0, N0, resE, resN):
    with open(input, "r") as points_image:
        with open(output, "w") as points_terrain:
            for line in points_image:
                line_splitted = line.split()
                point0_E = float(line_splitted[0])
                point0_N = float(line_splitted[1])
                point1_E = float(line_splitted[2])
                point1_N = float(line_splitted[3])
                point0_E = E0 + resE * point0_E
                point0_N = N0 + resN * point0_N
                point1_E = E0 + resE * point1_E
                point1_N = N0 + resN * point1_N
                points_terrain.write("{0:.3f} {1:.3f} {2:.3f} {3:.3f}\n".format(point0_E, point0_N, point1_E, point1_N))


E0, N0, resE, resN = get_georeferencement(args.input_image)
reprojeter(args.input_points, args.output_points, E0, N0, resE, resN)