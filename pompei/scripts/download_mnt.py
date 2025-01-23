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

import math
import os
import shutil
import argparse
from download_ortho_MNS_wms import download_data
from download_SRTM import transform_Points_WGS84, download
from osgeo import gdal
import gzip
from tools import getEPSG, load_bbox
import log # Chargement des configurations des logs
import logging

logger = logging.getLogger()


parser = argparse.ArgumentParser(description="Récupère le MNT de la zone")
parser.add_argument('--ortho', help="Manière de récupérer le MNT (storeref, wms, histo, dalles)")
args = parser.parse_args()


def create_ascii(path, e, n):
    with open(path, "w") as f:
        f.write("ncols        10000\n")
        f.write("nrows        10000\n")
        f.write("xllcorner    {}\n".format(e))
        f.write("yllcorner    {}\n".format(n))
        f.write("cellsize     1.000000000000\n")
        f.write("NODATA_value  -99999.00\n")
        string = "0.00 "*10000 + "\n"
        for i in range(10000):
            f.write(string)



def get_dalle_MNT(bbox):
    os.makedirs(os.path.join("metadata", "mnt"), exist_ok=True)
    n_max = int(math.ceil(bbox[3]/10000)*10000)
    e_min = int(math.floor(bbox[0]/10000)*10000)
    for e in range(e_min, int(bbox[2]), 10000):
        for n in range(n_max, int(bbox[1]), -10000):

            chemin = os.path.join("/media", 'store-ref', "modeles-numeriques-3D", "RGEAlti", "2024", "RGEALTI_MNT_1M00_ASC_RGF93LAMB93_FXX")
            nom_fichier = "{}-{}.asc.gz".format(e, n)
            chemin_fichier = os.path.join(chemin, nom_fichier)
            if os.path.exists(chemin_fichier):
                if not os.path.exists(nom_fichier):
                    shutil.copy(chemin_fichier, os.path.join("metadata", "mnt", nom_fichier))
            else:
                logger.warning("Impossible de trouver : {}. On utilise le SRTM".format(chemin_fichier))

                #On utilise le SRTM si la dalle n'existe pas (souvent le cas sur les zones frontalières) 
                points = [(e, n), (e+10000, n), (e+10000, n-10000), (e, n-10000)]
                points_WGS84 = transform_Points_WGS84(EPSG, points)
                temp_filename = os.path.join("metadata", "mnt", nom_fichier.replace(".asc.gz", "_temp.tif"))
                print("temp_filename : ", temp_filename)
                download(points_WGS84, temp_filename)
                filename = os.path.join("metadata", "mnt", nom_fichier.replace(".gz", ""))
                print(f"gdalwarp {temp_filename} {filename} -s_srs EPSG:4326 -t_srs EPSG:{EPSG}")
                os.system(f"gdalwarp {temp_filename} {filename} -s_srs EPSG:4326 -t_srs EPSG:{EPSG}")
                os.remove(temp_filename)


#On récupère l'EPSG du chantier
EPSG = getEPSG("metadata")

bbox = load_bbox("metadata")
if args.ortho == "storeref" and EPSG==2154:
    get_dalle_MNT(bbox)
    tiles = [i for i in os.listdir(os.path.join("metadata", "mnt")) if i[-3:]==".gz"]
    for tile in tiles:   
        tile_asc = tile[:-3]
        path_out = os.path.join("metadata", "mnt", tile_asc)
        with gzip.open(os.path.join("metadata", "mnt", tile), 'rb') as f_in:
            with open(path_out, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.system(f"gdal_edit.py -a_srs EPSG:{EPSG} {path_out}")
        os.remove(os.path.join("metadata", "mnt", tile))
    commande = "gdalbuildvrt {} {}".format(os.path.join("metadata", "mnt", "mnt.vrt"), os.path.join("metadata", "mnt", "*.asc"))
    os.system(commande)
else:
    download_data(bbox, "MNT", "metadata", EPSG)
    images = [i for i in os.listdir(os.path.join("metadata", "mnt_temp")) if i[-4:]==".tif"]
    for image in images:
        ds = gdal.Open(os.path.join("metadata", "mnt_temp", image))
        ds = gdal.Translate(os.path.join("metadata", "mnt", image), ds)
    commande = "gdalbuildvrt {} {}".format(os.path.join("metadata", "mnt", "mnt.vrt"), os.path.join("metadata", "mnt", "*.tif"))
    os.system(commande)
    shutil.rmtree(os.path.join("metadata", "mnt_temp"))


