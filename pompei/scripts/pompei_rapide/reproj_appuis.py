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

import os
import argparse
import rasterio
import rasterio.transform
from lxml import etree

parser = argparse.ArgumentParser(description="Récupère les positions des points d'appuis trouvés par Aubry")

parser.add_argument('--factor', help="Facteur de sous-échantillonnage", type=int)
parser.add_argument('--regrouper', help="Regroupe ou non les points d'appuis qui appartiennent à la même image", type=bool)
args = parser.parse_args()

factor = args.factor
regrouper = args.regrouper

def read_resultpi(path):
    """
    Récupère les points qui sont dans le fichier resultpi

    On ne prend qu'un point sur 4 car ils sont bizarrement dupliqués quatre fois chacun dans le fichier
    """
    points_histo = []
    points_ortho = []
    with open(path, "r") as f:
        for i, line in enumerate(f):
            if i%4==0:
                line_splitted = line.split()
                points_ortho.append([float(line_splitted[0]), float(line_splitted[1])])
                points_histo.append([float(line_splitted[2]), float(line_splitted[3])])
    return points_histo, points_ortho


def reproj_points_histo(points_histo, resultpi_name, factor):
    resultpi_name_splitted = resultpi_name.replace(".resultpi", "").split("--")[1].split("_")
    X0_histo = int(resultpi_name_splitted[1])*1000*factor
    Y0_histo = int(resultpi_name_splitted[0])*1000*factor

    resultpi_name_modif = resultpi_name.replace("OIS-Reech_", "").split("--")[0]
    ortho_name = "{}_rectifiee.tif".format(resultpi_name_modif)
    image_src = rasterio.open(ortho_name)
    gt = image_src.transform
    gt_factor = rasterio.Affine(gt.a*factor, gt.b*factor, gt.c, gt.d*factor, gt.e*factor, gt.f)
    

    points_histo_projected = []
    for point in points_histo:
        
        x_image = point[0]+X0_histo
        y_image = point[1]+Y0_histo
        x, y = rasterio.transform.xy(gt_factor, y_image, x_image)
        
        points_histo_projected.append([x,y])


    return points_histo_projected


def reproj_points_ortho(points_ortho, resultpi_name):
    ortho_name = "bdortho_"+resultpi_name.replace(".resultpi", ".tif")
    image_src = rasterio.open(os.path.join("dallage", ortho_name))
    gt = image_src.transform
    points_ortho_projected = []
    for point in points_ortho:
        x, y = rasterio.transform.xy(gt, point[1], point[0])
        points_ortho_projected.append([x,y])

    return points_ortho_projected


def save_appuis(points_histo, points_ortho, path):
    with open(path, "w") as f:
        for i in range(len(points_histo)):
            f.write("{} {} {} {}\n".format(points_ortho[i][0], points_ortho[i][1], points_histo[i][0], points_histo[i][1]))


def save_per_image(points_histo_dict, points_ortho_dict):
    images = list(points_histo_dict.keys())
    for image in images:
        points_histo = points_histo_dict[image]
        points_ortho = points_ortho_dict[image]
        with open(os.path.join("dallage", image+".imagereproj"), "w") as f:
            for i, point_histo in enumerate(points_histo):
                point_ortho = points_ortho[i]
                f.write("{} {} {} {}\n".format(point_ortho[0], point_ortho[1], point_histo[0], point_histo[1]))


points_histo_dict = {}
points_ortho_dict = {}

# On parcourt tous les fichiers .resultpi, contenant les positions des points trouvés par Aubry
resultpi_names = [i for i in os.listdir("dallage") if i[-9:]==".resultpi"]
for resultpi_name in sorted(resultpi_names):
    # On lit tous les points contenus dans le fichier. Ils sont en coordonnées image
    points_histo, points_ortho = read_resultpi(os.path.join("dallage", resultpi_name))
    # On reprojette les points qui sont sur l'ortho historique dans le système de coordonnées approché de l'ortho ancienne
    points_histo_projected = reproj_points_histo(points_histo, resultpi_name, factor)
    # On reprojette les points qui sont sur l'ortho de référence dans le système de projection de l'ortho de référence
    points_ortho_projected = reproj_points_ortho(points_ortho, resultpi_name)

    if len(points_histo_projected)!=len(points_ortho_projected):
        raise ValueError("Il n'y a pas le même nombre de points d'appuis sur l'ortho de référence et sur l'ortho historique")

    # On sauvegarde les points dans un fichier .resultpireproj
    save_appuis(points_histo_projected, points_ortho_projected, os.path.join("dallage", resultpi_name.replace(".resultpi", ".resultpireproj")))
    if regrouper:
        image_name = resultpi_name.split("--")[0]
        if image_name in list(points_histo_dict.keys()):
            points_histo_dict[image_name] += points_histo_projected
            points_ortho_dict[image_name] += points_ortho_projected
        else:
            points_histo_dict[image_name] = points_histo_projected
            points_ortho_dict[image_name] = points_ortho_projected

if regrouper:
    save_per_image(points_histo_dict, points_ortho_dict)