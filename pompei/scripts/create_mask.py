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

import rasterio
import os
import numpy as np

ois_images = [i for i in os.listdir() if i[:9]=="OIS-Reech" and i[-4:]==".tif"]

ois_image = ois_images[0]

ds = rasterio.open(ois_image)

x = ds.width
y = ds.height

array = np.zeros((y, x))

width_marge = int(0.05*x)
height_marge = int(0.05*y)

width_ones = int(0.9*x)
height_ones = int(0.9*y)

array_ones = np.ones((height_ones, width_ones))

array[height_marge:height_marge+height_ones, width_marge:width_marge+width_ones] = array_ones

array = np.expand_dims(array, 0)

meta_data_dict = {
        "TIFFTAG_XRESOLUTION": 1,
        "TIFFTAG_YRESOLUTION": 1,
        "TIFFTAG_MINSAMPLEVALUE": 0,
        "TIFFTAG_MAXSAMPLEVALUE": 1,
        "TIFFTAG_RESOLUTIONUNIT": 1
        }

with rasterio.open(
        "filtre.tif", "w",
        driver = "GTiff",
        dtype = rasterio.uint8,
        count = 1,
        width = x,
        height = y,
        tiled=True, blockxsize=2048, blockysize=2048, nbits=1) as dst:
        dst.write(array)
        dst.update_tags(**meta_data_dict)

