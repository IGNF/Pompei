#Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/
#
#File main authors:
#- Célestin Huet
#This file is part of Pompei: https://github.com/IGNF/Pompei
#
#Pompei is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#Pompei is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#You should have received a copy of the GNU General Public License along with Pompei. If not, see <https://www.gnu.org/licenses/>.

import os
import rasterio
import numpy as np



files = [i for i in os.listdir() if i[-4:]==".tif"]

for filename in files:
    image_src = rasterio.open(filename)
    array = image_src.read()
    array = array[0,:,:]
    array = np.where(array < 20, 0, 255)
    array = np.expand_dims(array, axis=0)

    with rasterio.open(
            "filtre_FFTKugelHupf_"+filename, "w",
            driver = "GTiff",
            dtype = rasterio.uint8,
            count = array.shape[0],
            width = array.shape[2],
            height = array.shape[1]) as dst:
        dst.write(array)





