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
import numpy as np
from lxml import etree
import rasterio.transform
import rasterio
import log # Chargement des configurations des logs
import logging

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Script permettant de créer les imagettes pour Aubry dans pompei_rapide.sh")
parser.add_argument('--metadata', help="Répertoire contenant les métadonnées")
parser.add_argument('--ta_xml', help="Fichier TA.xml")
parser.add_argument('--factor', help="factor pour le sous-échantillonage", type=int)
parser.add_argument('--workdir', help="Répertoire où écrire les imagettes")
parser.add_argument('--decalage', help="Appliquer un décalage")
args = parser.parse_args()

metadata = args.metadata
ta_xml_path = args.ta_xml
factor_sous_ech = args.factor
workdir = args.workdir
decalage = True
if args.decalage=="False":
    decalage = False

def convert_geotransform_to_array(gt):
    """
    It is faster to convert xy to row column (and inversally) with a numpy array rather than rasterio.Affine object
    """
    return np.array([[gt.a, gt.b, gt.c], [gt.d, gt.e, gt.f], [0, 0, 1]])

def read_ortho(metadata):
    src_image = rasterio.open(os.path.join(metadata, "ortho", "ORTHO.vrt"))
    geoTransform = src_image.transform
    ortho = src_image.read()
    crs = src_image.crs
    return ortho, geoTransform, crs


def open_image(image_name):
    src_image = rasterio.open(image_name)
    image_array = src_image.read()
    return image_array


def read_ta(ta_xml):
    tree = etree.parse(ta_xml)
    root = tree.getroot()
    return root


def save_image(path, image, crs, transform):
    with rasterio.open(
            path, "w",
            driver = "GTiff",
            crs = crs,
            transform = transform,
            dtype = rasterio.uint8,
            count = image.shape[0],
            width = image.shape[2],
            height = image.shape[1]) as dst:
        dst.write(image)

def get_footprint(ta_xml, image_name, image):
    """
    Get approximation of image_name geotransform

    """
    # Find in TA_xml the image
    _, l_image, c_image = image.shape
    image_name_not_OIS = image_name.replace("OIS-Reech_", "").replace(".tif", "")
    for cliche in ta_xml.getiterator("cliche"):
        if cliche.find("image").text.strip() == image_name_not_OIS:
            # get footprint
            polygon2d = cliche.find("polygon2d")
            x = polygon2d.findall("x")
            y = polygon2d.findall("y")
            points = [(float(x[i].text), float(y[i].text)) for i in range(len(x))]
            
            # create geotransform object 
            c = points[0][0]
            f = points[0][1]
            a = (points[2][0]-points[0][0])/c_image
            b = (points[2][1]-points[0][1])/c_image
            d = (points[-2][0]-points[0][0])/l_image
            e = (points[-2][1]-points[0][1])/l_image
            geotransform = rasterio.Affine(a, b, c, d, e, f)
            
            # Convert geotransform in array
            gt_array = convert_geotransform_to_array(geotransform)
            
            # save image
            save_image(os.path.join(workdir, image_name_not_OIS+"_rectifiee.tif"), image, crs, geotransform)#Pour contrôle
            
            return gt_array
    raise ValueError("Emprise de l'image {} non trouvée dans le fichier ta_xml".format(image_name_not_OIS))


def get_decalage(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            for line in f:
                line_splitted = line.split()
                return float(line_splitted[0]), float(line_splitted[1])
    else:
        logger.warning(f"Pas trouvé : {path}")
        return 0, 0


def one_image(path_appuis, image_name, factor_sous_ech, ta_xml, gt_ortho_array, ortho, crs, decalage):

    # Open image
    image = open_image(image_name)

    # Get image footprint from ta_xml (approximation of around 100 meters)
    gt_image = get_footprint(ta_xml, image_name, image)
    _, l_image, c_image = image.shape

    # Cut in tiles of 1000*factor_sous_ech pixels
    for l_count, l in enumerate(range(0, l_image, 1000*factor_sous_ech)):
        for c_count, c in enumerate(range(0, c_image, 1000*factor_sous_ech)):
            
            # get row column coordinates of each pixel
            max_l = min(l+1000*factor_sous_ech, l_image)
            max_c = min(c+1000*factor_sous_ech, c_image)
            lignes = np.arange(l, max_l, factor_sous_ech)
            colonnes = np.arange(c, max_c, factor_sous_ech)
            size_l = lignes.shape[0]
            size_c = colonnes.shape[0]
            ll, cc = np.meshgrid(lignes, colonnes)
            cc_reshaped = cc.reshape((1, -1))
            ll_reshaped = ll.reshape((1, -1))
            ones = np.ones(cc_reshaped.shape)
            coords_lc = np.concatenate((cc_reshaped, ll_reshaped, ones))

            # get xy coordinates
            coords_xy = gt_image @ coords_lc # C'est interminable si on passe par l'objet Affine de rasterio, donc autant le faire à la main

            delta_x = 0
            delta_y = 0
            if decalage:
                decalage_name = "{}--{}_{}.T.txt".format(image_name.replace(".tif", ""), l_count, c_count)
                delta_x, delta_y = get_decalage(os.path.join(workdir, "dallage", decalage_name))
                coords_xy += np.array([[delta_x], [delta_y], [0]])

                if max_l-l != 1000 or max_c-c != 1000:
                    continue
                
            
            
            # get row column coordinates in BD ortho
            coords_lc_ortho = gt_ortho_array @ coords_xy
            coords_lc_ortho = coords_lc_ortho.astype(np.uint32)

            # save histo tile image
            extract_image = image[:,ll_reshaped[0,:], cc_reshaped[0:]].reshape((1, size_c, size_l))
            extract_image = np.transpose(extract_image, axes=(0,2,1))
            geotransform_extract_image = rasterio.Affine(gt_image[0,0]*factor_sous_ech, gt_image[0,1]*factor_sous_ech, coords_xy[0,0], gt_image[1,0]*factor_sous_ech, gt_image[1,1]*factor_sous_ech, coords_xy[1,0])
            
            try:# Il risque d'y avoir un problème si le décalage est important et qu'il n'y a pas une marge suffisante sur la BD Ortho
                histo_name = "{}--{}_{}.tif".format(image_name.replace(".tif", ""), l_count, c_count)
                path_extract_image = os.path.join(path_appuis, histo_name)
                save_image(path_extract_image, extract_image, crs, geotransform_extract_image)
                # save BD Ortho tile image
                extract_ortho = ortho[:,coords_lc_ortho[1,:], coords_lc_ortho[0,:]].reshape((3, size_c, size_l))
                extract_ortho = np.transpose(extract_ortho, axes=(0,2,1))
                ortho_name = "bdortho_{}--{}_{}.tif".format(image_name.replace(".tif", ""), l_count, c_count)
                path_extract_ortho = os.path.join(path_appuis, ortho_name)
                save_image(path_extract_ortho, extract_ortho, crs, geotransform_extract_image)
            except:
                pass



# read ta.xml
ta_xml = read_ta(ta_xml_path)

# Open ortho
ortho, gt_ortho, crs = read_ortho(metadata)

# get inverse transformation of geotransform (xy to row column)
gt_ortho_array = np.linalg.inv(convert_geotransform_to_array(gt_ortho))

# Create dir appuis
path_appuis = os.path.join(workdir, "dallage")
os.makedirs(path_appuis, exist_ok=True)

# Get images name
images_names = [i for i in os.listdir() if i[:10]=="OIS-Reech_" and i[-4:]==".tif"]
for image_name in images_names:
    # For each image, cut in small tiles and get the equivalent from the BD Ortho
    one_image(path_appuis, image_name, factor_sous_ech, ta_xml, gt_ortho_array, ortho, crs, decalage)
