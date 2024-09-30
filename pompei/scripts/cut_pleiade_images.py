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
from osgeo import gdal, osr
import os
import numpy as np
from tools import getEPSG

parser = argparse.ArgumentParser(description="Découpage des images Pléiades en tuiles de 2000 pixels")
parser.add_argument('--input', help='Répertoire ortho_temp contenant les images Pléiades sous format jp2')
parser.add_argument('--metadata', help='Répertoire des métadonnées')
parser.add_argument('--output', help='Répertoire ortho où écrire les fichiers tfw')
args = parser.parse_args()



"""
Il est nécessaire de découper les dalles de Pléiades, sinon l'ordinateur peut ramer lors de la recherche de points d'appuis.
On découpe ici les images en dalles de 2000 pixels de côté
"""


def save_hdr(name, e_min_dalle, n_max_dalle, height, width, resolution_X, resolution_Y):
    with open(os.path.join(args.metadata, "mns", name), 'w') as out:
        out.write(" // Convention de georeferencement : angle noeud (Geoview)\n")
        out.write("!+\n!+--------------------------\n!+ HDR/A : Image Information\n!+--------------------------\n!+\n")
        out.write("ULXMAP  {}\n".format(e_min_dalle))
        out.write("ULYMAP  {}\n".format(n_max_dalle))
        out.write("XDIM    {}\n".format(resolution_X))
        out.write("YDIM    {}\n".format(resolution_Y))
        out.write("NROWS  {}\n".format(height))
        out.write("NCOLS  {}\n".format(width))
        out.write("NBANDS   1\n")
        out.write("!+\n!+--------------------------\n!+ HDR/B : Frame Corner Support\n!+--------------------------\n!+\n")
        out.write("!+\n!+--------------------------\n!+ HDR/C : File Encoding\n!+--------------------------\n!+\n")
        out.write("!+\n!+--------------------------\n!+ HDR/E : More Parameters\n!+--------------------------\n!+\n")
        out.write("COSINUS 1.00\n")
        out.write("SINUS 0.00\n")
        out.write("SIGNE	1\n")
        out.write("BAND_NAMES	Z\n")
        out.write("PROJECTION    LAMBERT93\n")



if not os.path.exists(args.output):
    os.makedirs(args.output)

images_Pleiades = [i for i in os.listdir(args.input) if i[-4:]==".jp2" or i[-4:]==".tif"]

compte = 0
for image in images_Pleiades:
    input_ds = gdal.Open(os.path.join(args.input, image))
    inputlyr = np.array(input_ds.ReadAsArray())
    for i in range(0, inputlyr.shape[1], 2000):
        for j in range(0, inputlyr.shape[2], 2000):
            imagette = inputlyr[:, i:i+2000, j:j+2000]
            if np.max(imagette != 0):
                driver = gdal.GetDriverByName('GTiff')
                outRaster = driver.Create(os.path.join(args.output, "ORTHO_dalle_{}.tif".format(compte)), imagette.shape[2], imagette.shape[1], 3, gdal.GDT_Byte)
                geotransform = list(input_ds.GetGeoTransform())
                geotransform[0] = geotransform[0] + j * geotransform[1]
                geotransform[3] = geotransform[3] + i * geotransform[5]
                outRaster.SetGeoTransform(tuple(geotransform))
                for k in range(3):
                    outband = outRaster.GetRasterBand(k+1)
                    outband.WriteArray(imagette[k, :, :])

                outSpatialRef = osr.SpatialReference()
                outSpatialRef.ImportFromEPSG(getEPSG(args.metadata))
                outRaster.SetProjection(outSpatialRef.ExportToWkt())
                outband.FlushCache()


                with open(os.path.join(args.output, "ORTHO_dalle_{}.tfw".format(compte)), 'w') as out:
                    out.write("{}\n".format(geotransform[1]))
                    out.write("0.00\n")
                    out.write("0.00\n")
                    out.write("{}\n".format(geotransform[5]))
                    out.write("{}\n".format(geotransform[0]))
                    out.write("{}\n".format(geotransform[3]))
                compte += 1


#On construit le fichier hdr du MNS
chemin_mns = os.path.join(args.metadata, "mns_temp", "MNS.tif")
                                

inputds = gdal.Open(chemin_mns)
                         
geotransform = inputds.GetGeoTransform()
e_min_mns = geotransform[0]
n_max_mns = geotransform[3]
resolution = geotransform[1]
save_hdr("MNS.hdr", e_min_mns, n_max_mns, inputds.RasterXSize, inputds.RasterYSize, resolution, abs(geotransform[5]))