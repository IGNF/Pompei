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

import rasterio.crs
from equations import Shot, MNT, DistorsionCorrection, Mask
import numpy as np
import rasterio
from scipy import ndimage
from multiprocessing import Pool, Process
from tqdm import tqdm
from tools import getEPSG, load_bbox, getNbCouleurs, getResolution, read_ori
import log # Chargement des configurations des logs
import logging

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Crée une ortho pour chaque image")

parser.add_argument('--mnt', help="MNT sous format vrt")
parser.add_argument('--ori', help="Répertoire contenant les fichiers orientations")
parser.add_argument('--outdir', help="Répertoire où sauvegarder les orthos")
parser.add_argument('--cpu', help="Nombre de cpus à utiliser", type=int)
parser.add_argument('--mask', help="Masque où calculer les orthos", default=None)
parser.add_argument('--ta', help="Fichier TA")
args = parser.parse_args()

mnt_path = args.mnt
ori_path = args.ori
outdir = args.outdir
nb_cpus = args.cpu
mask_path = args.mask
ta_path = args.ta

# Une dalle : 2000 pixels
tileSize = 2000
  

def saveImage(image, path, x0, y0, resolution, EPSG, create_ori=False):
    dictionnaire = {
            'interleave': 'Band',
            'tiled': True
        }
    with rasterio.open(
        path, "w",
        driver = "GTiff",
        dtype = rasterio.uint8,
        count = image.shape[0],
        width = image.shape[2],
        height = image.shape[1],
        crs = EPSG,
        transform = rasterio.Affine(resolution, 0.0, x0, 0.0, -resolution, y0),
        **dictionnaire
        ) as dst:
        dst.write(image)

    if create_ori:
        path_ori = path.replace(".tif", ".tfw")
        with open(path_ori, "w") as f:
            f.write("{}\n".format(resolution))
            f.write("{}\n".format(0))
            f.write("{}\n".format(0))
            f.write("{}\n".format(-resolution))
            f.write("{}\n".format(x0))
            f.write("{}\n".format(y0))

def createOrthoImage(shot:Shot, x_min, x_max, y_min, y_max, mnt:MNT, resolution, nbCouleurs):
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

    # On récupère le masque des pixels qui ne sont pas dans la zone où le MNS a été calculé
    if mask_path is not None:
        mask_value = mask.get(xx, yy).reshape((1, y.shape[0], x.shape[0]))
    
    if z is None:
        return None
    
    # On récupère les coordonnées images
    c, l = shot.world_to_image(xx, yy, z)

    # On applique la correction de la distorsion
    dc = DistorsionCorrection(shot.calibration)
    c_corr, l_corr = dc.compute(c, l)

    RasterXSize = array_ortho.shape[2]
    RasterYSize = array_ortho.shape[1]
    min_c = int(np.floor(np.min(c_corr)))
    max_c = int(np.ceil(np.max(c_corr)))
    min_l = int(np.floor(np.min(l_corr)))
    max_l = int(np.ceil(np.max(l_corr)))

    # Coordonnées pour lire une partie de l'image même si dans l'idéal on a besoin d'une partie en-dehors de l'image
    min_c_read = max(0, min_c)
    max_c_read = min(RasterXSize-1, max_c)
    min_l_read = max(0, min_l)
    max_l_read = min(RasterYSize-1, max_l)

    # Si les coordonnées demandées sont en dehors de l'image, on renvoie None
    if min_l > RasterYSize or min_c > RasterXSize or max_l < 0 or max_c < 0:
        finalImage = None
    # Si on veut une image trop grande, on renvoie None par sécurité
    elif max_l-min_l+1 > 30000 or max_c-min_c+1 > 30000:
        finalImage = None
    else:
        image = array_ortho[:,min_l_read:max_l_read+1, min_c_read:max_c_read+1]
        image = image.reshape((nbCouleurs, max_l_read-min_l_read+1, max_c_read-min_c_read+1))
        
        finalImage = np.zeros((nbCouleurs, max_l-min_l+1, max_c-min_c+1), dtype=np.uint8)
        finalImage[:,min_l_read-min_l:max_l_read-min_l+1, min_c_read-min_c:max_c_read-min_c+1] = image

    # On récupère les points de l'image
    if finalImage is not None:
        list_bands = []
        for i in range(nbCouleurs):
            value_band = ndimage.map_coordinates(finalImage[i,:,], np.vstack([l_corr-min_l, c_corr-min_c])).reshape((1, y.shape[0], x.shape[0]))
            # On applique le masque
            if mask_path is not None:
                value_band = value_band*mask_value
            list_bands.append(value_band)
        ortho = np.concatenate(list_bands, axis=0)
    else:
        ortho = None
    return ortho


def getEmpriseSol(shot:Shot, mnt:MNT):
    points = [[0, 0],[0, shot.Y_size],[shot.X_size, 0],[shot.X_size, shot.Y_size]]
    worldExtend_x = []
    worldExtend_y = []
    for point in points:
        x_p, y_p, _ = shot.image_to_world(np.array([point[0]]), np.array([point[1]]), mnt)
        worldExtend_x.append(x_p)
        worldExtend_y.append(y_p)
    worldExtend_x = np.array(worldExtend_x)
    worldExtend_y = np.array(worldExtend_y)
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
    mnt = MNT(mnt_path)
    orthoImage = createOrthoImage(shot, x0, x1, y1, y0, mnt, resolution, nbCouleurs)
    if orthoImage is not None:
        mask = np.where(orthoImage==0, 255, 0)
        nb_bands, n_temp, m_temp = orthoImage.shape
        return (orthoImage, i, i+n_temp, j, j+m_temp, mask)
    else:
        return None


def write_image(bigOrtho, path_ortho, x_min, y_max, resolution, EPSG, bigMask, path_mask):
    saveImage(bigOrtho, path_ortho, x_min, y_max, resolution, EPSG, create_ori=True)
    saveImage(bigMask, path_mask, x_min, y_max, resolution, EPSG, create_ori=True)


def createShotOrtho(shot, resolution, nbCouleurs, EPSG):
    global array_ortho
    
    path_ortho = os.path.join(outdir, "Ort_{}.tif".format(shot.nom))
    path_mask = os.path.join(outdir, "Incid_{}.tif".format(shot.nom))
    x_min, x_max, y_min, y_max = getEmpriseSol(shot, mnt)
    n, m, bigOrtho = initImage(x_min, x_max, y_min, y_max, shot.nom, nbCouleurs)
    bigMask = np.zeros(bigOrtho.shape)
    if n is not None:
        inputds = rasterio.open(shot.imagePath)
        array_ortho = inputds.read()
        work_data = []
        for i in range(0, n, 1000):
            for j in range(0, m, 1000):
                x0 = x_min + j*resolution
                y0 = y_max - i*resolution
                x1 = min(x_max, x0 + 1000*resolution)
                y1 = max(y_min, y0 - 1000*resolution)
                work_data.append([x0, y0, x1, y1, shot, i, j, nbCouleurs])

        with Pool(nb_cpus) as pool:
            for result in pool.map(poolProcess, work_data):
                if result is not None:
                    orthoImage = result[0]
                    i_min = result[1]
                    i_max = result[2]
                    j_min = result[3]
                    j_max = result[4]
                    mask = result[5]

                    bigOrtho[:,i_min:i_max, j_min:j_max] = orthoImage
                    bigMask[:,i_min:i_max, j_min:j_max] = mask
        
        p = Process(target=write_image, args=([bigOrtho, path_ortho, x_min, y_max, resolution, EPSG, bigMask, path_mask]))
        p.start()
        


def createShotOrthos(shots, resolution, nbCouleurs, EPSG):
    for shot in tqdm(shots):
        createShotOrtho(shot, resolution, nbCouleurs, EPSG)
            
            

os.makedirs(outdir, exist_ok=True)

if mask_path is not None:
    mask = Mask(mask_path)

mnt = MNT(mnt_path)
# On charge la boite englobante du chantier
bbox = load_bbox("metadata")

#On récupère l'EPSG du chantier
EPSG = getEPSG("metadata")

resolution = getResolution()
nbCouleurs = getNbCouleurs("metadata")


# On crée un objet shot par image
shots = read_ori(ori_path, ta_path, EPSG)

# Crée les tuiles d'ortho
createShotOrthos(shots, resolution, nbCouleurs, EPSG)