"""
Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/

File main authors:
- Célestin Huet
- Arnaud Le Bris

This file is part of Pompei: https://github.com/IGNF/Pompei

Pompei is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Pompei is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Pompei. If not, see <https://www.gnu.org/licenses/>.
"""

import argparse
import os
from osgeo import gdal

parser = argparse.ArgumentParser(description='Construction des tfw des fichiers Z Num Max')
parser.add_argument('--input_Malt', default='', help='Dossier MEC-Malt')
args = parser.parse_args()

def read_tfw(path):
    with open(path, "r") as f:
        compte = 0
        for line in f:
            if compte==0:
                dX = float(line)
            if compte==3:
                dY = float(line)
            if compte==4:
                X0 = float(line)
            if compte==5:
                Y0 = float(line)
            compte += 1
    return X0, Y0, dX, dY

def write_tfw(path, x, y, dX, dY):
    with open(path, "w") as f:
        f.write("{}\n0\n0\n{}\n{}\n{}\n".format(dX, dY, x, y))


def get_znum_tfw(folder, level):
    prefixe = f"Z_Num{level}_DeZoom"
    suffixe = ".tfw"
    files = [i for i in os.listdir(folder) if i[:len(prefixe)]==prefixe and i[-len(suffixe):]==suffixe and not "Tile" in i]
    if len(files)==0:
        return None
    return os.path.join(folder, files[0])


def create_tfw(folder, radical):
    Z_Nums = [i for i in os.listdir(folder) if radical in i and i[-4:]==".tif"]

    Z_Nums_Tile = sorted([i for i in Z_Nums if "Tile" in i])
    Z_Nums_not_Tile = [i for i in Z_Nums if not "Tile" in i]


    if len(Z_Nums_not_Tile)>=1:
        if "Correl_STD-MALT" in radical:
            level = radical.split("_")[-1]
            filename = get_znum_tfw(folder, level)
            X0, Y0, res_X, res_Y = read_tfw(filename)
            for f in Z_Nums_not_Tile:
                write_tfw(os.path.join(folder, f.replace(".tif", ".tfw")), X0, Y0, res_X, res_Y)
        else:
            X0, Y0, res_X, res_Y = read_tfw(os.path.join(folder, Z_Nums_not_Tile[0].replace(".tif", ".tfw")))


        for compte, tile in enumerate(Z_Nums_Tile):
            if radical == "Orthophotomosaic":
                j_tile = int(tile.split(".")[0].split("_")[2])
            else:
                j_tile = int(tile.split(".")[0].split("_")[5])
            if compte==0:
                x = X0
                y = Y0
            else:
                if j_tile > j:
                    #On passe à la colonne d'après
                    x = x + res_X * dx
                    y = Y0
                else:
                    y = y + res_Y * dy

            write_tfw(os.path.join(folder, tile.replace(".tif", ".tfw")), x, y, res_X, res_Y)
            
            input_ds = gdal.Open(os.path.join(folder, tile))
            dx = input_ds.RasterXSize
            dy = input_ds.RasterYSize
            j = j_tile



for indice in range(1, 10):
    create_tfw(args.input_Malt, "Z_Num{}".format(indice))
    create_tfw(args.input_Malt, f"Correl_STD-MALT_Num_{indice}")

create_tfw("Ortho-"+args.input_Malt, "Orthophotomosaic")

    

            



