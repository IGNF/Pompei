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
import os
from lxml import etree
from osgeo import gdal
import numpy as np
import shutil

parser = argparse.ArgumentParser(description='Construction du MNS à partir des Z Num Max')
parser.add_argument('--input_Malt', default='', help='Dossier MEC-Malt')
args = parser.parse_args()


def get_Z_Nums_max():
    Z_Nums = [i for i in os.listdir(args.input_Malt) if "Z_Num" in i and i[-4:]==".tif"]

    indice_max = 0
    for Z_Num in Z_Nums:
        indice_max = max(indice_max, int(Z_Num[5]))

    Z_Nums_max = [i for i in Z_Nums if int(i[5])==indice_max]

    Z_Nums_max_Tile = [i for i in Z_Nums_max if "Tile" in i]
    Z_Nums_max_not_Tile = [i for i in Z_Nums_max if not "Tile" in i]

    if len(Z_Nums_max_Tile)==0:
        Z_Nums_max_Tile = Z_Nums_max_not_Tile.copy()
    
    return Z_Nums_max_Tile, Z_Nums_max_not_Tile

def get_a_b(Z_Nums_max_not_Tile):
    xml_file = Z_Nums_max_not_Tile[0].replace(".tif", ".xml")

    xml_path = os.path.join(args.input_Malt, xml_file)

    if os.path.exists(xml_path):
        tree = etree.parse(xml_path)
        root = tree.getroot()
        OrigineAlti = float(root.find("OrigineAlti").text)
        ResolutionAlti = float(root.find("ResolutionAlti").text)
        return OrigineAlti, ResolutionAlti
    else:
        print("Impossible d'ouvrir le fichier {}".format(xml_path))

def create_MNS(Z_Nums_max_Tile, OrigineAlti, ResolutionAlti):
    for tile in Z_Nums_max_Tile:
        MNS_name = tile.replace("Z_", "MNS_Final_")
        input_ds = gdal.Open(os.path.join(args.input_Malt, tile))
        inputlyr = np.array(input_ds.ReadAsArray())
        inputlyr = OrigineAlti + inputlyr * ResolutionAlti

        driver = gdal.GetDriverByName('GTiff')
        outRaster = driver.Create(os.path.join(args.input_Malt, MNS_name), inputlyr.shape[1], inputlyr.shape[0], 1, gdal.GDT_Float32)
        outRaster.SetGeoTransform(input_ds.GetGeoTransform())
        outRaster.GetRasterBand(1).WriteArray(inputlyr)
        shutil.copy(os.path.join(args.input_Malt, tile.replace(".tif", ".tfw")), os.path.join(args.input_Malt, MNS_name.replace(".tif", ".tfw")))


Z_Nums_max_Tile, Z_Nums_max_not_Tile = get_Z_Nums_max()
OrigineAlti, ResolutionAlti = get_a_b(Z_Nums_max_not_Tile)
create_MNS(Z_Nums_max_Tile, OrigineAlti, ResolutionAlti)