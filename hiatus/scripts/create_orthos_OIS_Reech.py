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

import os
import argparse
from equations import Shot, MNT, Calibration, DistorsionCorrection
from lxml import etree
import numpy as np
from osgeo import gdal, osr
from scipy import ndimage
from multiprocessing import Pool
from tqdm import tqdm
from tools import getEPSG, load_bbox, getNbCouleurs, getResolution
import log # Chargement des configurations des logs
import logging

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Crée une ortho pour chaque image")

parser.add_argument('--ta_xml', help="Fichier TA avec les positions mises à jour")
parser.add_argument('--mnt', help="MNT sous format vrt")
parser.add_argument('--ori', help="Répertoire contenant les fichiers orientations")
args = parser.parse_args()

ta_xml = args.ta_xml
mnt = args.mnt
ori_path = args.ori


# Une dalle : 2000 pixels
tileSize = 2000


def get_image(image):
    images = [i for i in os.listdir() if i[-4:]==".tif" and i[:9]=="OIS-Reech"]
    for imageName in images:
        if imageName == "OIS-Reech_{}.tif".format(image):
            return imageName
    return None


def getFocale(root):
    focal = root.find(".//focal")
    pixel_size = 0.021
    focale_x = float(focal.find(".//x").text) / pixel_size
    focale_y = float(focal.find(".//y").text) / pixel_size
    focale_z = float(focal.find(".//z").text) / pixel_size
    return [focale_x, focale_y, focale_z]


def createShots(ta_xml, EPSG):
    """
    Crée un objet Shot par image
    """
    tree = etree.parse(ta_xml)
    root = tree.getroot()
    focale = getFocale(root)
    shots = []
    for cliche in root.getiterator("cliche"):
        image = cliche.find("image").text.strip()
        imagePath = get_image(image)
        if imagePath is not None:
            shot = Shot.createShot(cliche, focale, imagePath, EPSG)
            shots.append(shot)
    return shots    

def saveImage(image, path, x0, y0, resolution, EPSG, create_ori=False):
    driver = gdal.GetDriverByName('GTiff')
    outRaster = driver.Create(path, image.shape[2], image.shape[1], image.shape[0], gdal.GDT_Byte)
    outRaster.SetGeoTransform((x0, resolution, 0, y0, 0, -resolution))
    for i in range(image.shape[0]):
        outband = outRaster.GetRasterBand(i+1)
        outband.WriteArray(image[i,:,:])
    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(EPSG)
    outRaster.SetProjection(outSpatialRef.ExportToWkt())

    if create_ori:
        path_ori = path.replace(".tif", ".tfw")
        with open(path_ori, "w") as f:
            f.write("{}\n".format(resolution))
            f.write("{}\n".format(0))
            f.write("{}\n".format(0))
            f.write("{}\n".format(-resolution))
            f.write("{}\n".format(x0))
            f.write("{}\n".format(y0))

def createOrthoImage(shot:Shot, x_min, x_max, y_min, y_max, mnt, resolution, nbCouleurs):
    # On crée un tableau numpy qui contient les coordonnées de tous les pixels
    x = np.arange(x_min, x_max, resolution)
    y = np.flip(np.arange(y_min, y_max, resolution))
    xx, yy = np.meshgrid(x, y)
    xx = xx.reshape((-1, ))
    yy = yy.reshape((-1, ))

    if xx.shape[0] == 0 or yy.shape == 0:
        return None

    
    # On récupère l'altitude des pixels
    z = mnt.get(xx, yy)
    if z is None:
        return None

    # On récupère les coordonnées images
    c, l = shot.world_to_image(xx, yy, z)

    # On applique la correction de la distorsion
    dc = DistorsionCorrection(calibration)
    c_corr, l_corr = dc.compute(c, l)

    inputds = gdal.Open(shot.imagePath)
    min_c = int(np.floor(np.min(c_corr)))
    max_c = int(np.ceil(np.max(c_corr)))
    min_l = int(np.floor(np.min(l_corr)))
    max_l = int(np.ceil(np.max(l_corr)))

    # Coordonnées pour lire une partie de l'image même si dans l'idéal on a besoin d'une partie en-dehors de l'image
    min_c_read = max(0, min_c)
    max_c_read = min(inputds.RasterXSize-1, max_c)
    min_l_read = max(0, min_l)
    max_l_read = min(inputds.RasterYSize-1, max_l)

    # Si les coordonnées demandées sont en dehors de l'image, on renvoie None
    if min_l > inputds.RasterYSize or min_c > inputds.RasterXSize or max_l < 0 or max_c < 0:
        finalImage = None
    # Si on veut une image trop grande, on renvoie None par sécurité
    elif max_l-min_l+1 > 30000 or max_c-min_c+1 > 30000:
        finalImage = None
    else:
        image = inputds.ReadAsArray(min_c_read, min_l_read, max_c_read-min_c_read+1, max_l_read-min_l_read+1)
        image = image.reshape((nbCouleurs, max_l_read-min_l_read+1, max_c_read-min_c_read+1))
        
        finalImage = np.zeros((nbCouleurs, max_l-min_l+1, max_c-min_c+1), dtype=np.uint8)
        finalImage[:,min_l_read-min_l:max_l_read-min_l+1, min_c_read-min_c:max_c_read-min_c+1] = image
        

    # On récupère les points de l'image
    if finalImage is not None:
        list_bands = []
        for i in range(nbCouleurs):
            value_band = ndimage.map_coordinates(finalImage[i,:,], np.vstack([l_corr-min_l, c_corr-min_c])).reshape((1, y.shape[0], x.shape[0]))
            list_bands.append(value_band)
        ortho = np.concatenate(list_bands, axis=0)
    else:
        ortho = None
    return ortho
            


def getCalibrationFile(path):
    files = os.listdir(path)
    for file in files:
        if file[:11] == "AutoCal_Foc":
            return os.path.join(path, file)
    raise Exception("No calibration file in {}".format(path))


def getEmpriseSol(shot:Shot, mnt:MNT):
    points = np.array([[0, 0],[0, shot.Y_size],[shot.X_size, 0],[shot.X_size, shot.Y_size]])
    worldExtend_x, worldExtend_y, _ = shot.image_to_world(points[:,0], points[:,1], mnt)
    x_min = np.min(worldExtend_x)
    y_min = np.min(worldExtend_y)
    x_max = np.max(worldExtend_x)
    y_max = np.max(worldExtend_y)
    return x_min, x_max, y_min, y_max


def initImage(x_min, x_max, y_min, y_max, image, nbCouleurs):
    x = np.arange(x_min, x_max, resolution)
    y = np.flip(np.arange(y_min, y_max, resolution))
    n = y.shape[0]
    m = x.shape[0]
    if n > 30000 or m > 30000:
        logger.warning("Attention, pour l'image {}, n vaut {} et m {}".format(image, n, m))
        logger.warning("x_min : {}, x_max : {}".format(x_min, x_max))
        logger.warning("y_min : {}, y_max : {}".format(y_min, y_max))
        logger.warning("Résolution : {}".format(resolution))
        return None, None, None
    else:
        array = np.zeros((nbCouleurs, n, m))
    return n, m, array
    

def poolProcess(work_data):
    x0 = work_data[0]
    y0 = work_data[1]
    x1 = work_data[2] 
    y1 = work_data[3] 
    shot = work_data[4]
    i = work_data[5]
    j = work_data[6]
    nbCouleurs = work_data[7]
    orthoImage = createOrthoImage(shot, x0, x1, y1, y0, mnt, resolution, nbCouleurs)
    if orthoImage is not None:
        nb_bands, n_temp, m_temp = orthoImage.shape
        return (orthoImage, i, i+n_temp, j, j+m_temp)
    else:
        return None


def createShotOrtho(shot, resolution, nbCouleurs, EPSG):
    path_ortho = os.path.join("ortho_mnt", "Ort_{}.tif".format(shot.nom))
    path_mask = os.path.join("ortho_mnt", "Incid_{}.tif".format(shot.nom))
    x_min, x_max, y_min, y_max = getEmpriseSol(shot, mnt)
    n, m, bigOrtho = initImage(x_min, x_max, y_min, y_max, shot.nom, nbCouleurs)
    if n is not None:
        work_data = []
        for i in range(0, n, 1000):
            for j in range(0, m, 1000):
                x0 = x_min + j*resolution
                y0 = y_max - i*resolution
                x1 = min(x_max, x0 + 1000*resolution)
                y1 = max(y_min, y0 - 1000*resolution)
                work_data.append([x0, y0, x1, y1, shot, i, j, nbCouleurs])

        with Pool(12) as pool:
            for result in pool.map(poolProcess, work_data):
                if result is not None:
                    orthoImage = result[0]
                    i_min = result[1]
                    i_max = result[2]
                    j_min = result[3]
                    j_max = result[4]

                    bigOrtho[:,i_min:i_max, j_min:j_max] = orthoImage
        
        saveImage(bigOrtho, path_ortho, x_min, y_max, resolution, EPSG, create_ori=True)
        mask = np.where(bigOrtho==0, 255, 0)
        saveImage(mask, path_mask, x_min, y_max, resolution, EPSG, create_ori=True)


def createShotOrthos(shots, resolution, nbCouleurs, EPSG):
    for shot in tqdm(shots):
        createShotOrtho(shot, resolution, nbCouleurs, EPSG)
            
            

os.makedirs("ortho_mnt", exist_ok=True)

mnt = MNT(os.path.join("metadata", "mnt", "mnt.vrt"))
# On charge la boite englobante du chantier
bbox = load_bbox("metadata")

#On récupère l'EPSG du chantier
EPSG = getEPSG("metadata")

resolution = getResolution()
nbCouleurs = getNbCouleurs("metadata")

# On récupère les paramètres de calibration de la caméra
calibrationFile = getCalibrationFile(ori_path)
calibration = Calibration.createCalibration(calibrationFile)

# On crée un objet shot par image
shots = createShots(ta_xml, EPSG)

# Crée les tuiles d'ortho
createShotOrthos(shots, resolution, nbCouleurs, EPSG)