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
from equations import MNT, Calibration
import numpy as np
from osgeo import gdal, osr
from multiprocessing import Pool
from tools import getEPSG, load_bbox, getNbCouleurs, getResolution, loadShots
import log # Chargement des configurations des logs
import logging
from tqdm import tqdm
import geopandas as gpd
import rasterio
from rasterio import Affine
import rasterio.features
from shapely import Polygon, intersects, intersection, make_valid

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Crée un nouveau fichier TA avec les valeurs déterminées pendant le chantier (orientation, position...")

parser.add_argument('--ori', help="Répertoire contenant les fichiers orientations")
parser.add_argument('--cpu', help="Nombre de cpus à utiliser", type=int)
parser.add_argument('--mnt', help="MNT sous format vrt")
parser.add_argument('--radiom', help="Répertoire avec les images égalisées")
parser.add_argument('--mosaic', help="Fichier avec la mosaïque")
parser.add_argument('--outdir', help="Répertoire contenant les fichiers orientations")
args = parser.parse_args()

ori_path = args.ori
nb_cpus = args.cpu
mnt_path = args.mnt
outdir = args.outdir
radiom = args.radiom
mosaic_file = args.mosaic

# Une dalle : 2000 pixels
tileSize = 2000


def computeMosaic(x0, y0, shots):
    """
    Pour chaque pixel de la tuile, on cherche le sommet de prise de vue qui lui est le plus proche
    """
    shots_filtered = []
    transform = Affine(resolution, 0, x0, 0, -resolution, y0)
    x_max = x0+2000*resolution
    y_min = y0-2000*resolution
    polygone = Polygon([[x0, y0], [x_max, y0], [x_max, y_min], [x0, y_min]])
    mosaique_extraction = []
    compte = 0
    for element in mosaique:
        if intersects(element[0], polygone):
            try:
                geom_valid = make_valid(element[0])
                geom = intersection(geom_valid, polygone)
            except:
                geom = element[0]
            
            mosaique_extraction.append([geom, compte])
            shots_filtered.append(shots[element[1]])
            compte += 1

    mosaic = rasterio.features.rasterize(mosaique_extraction, out_shape=(2000,2000), transform=transform)
    return mosaic, shots_filtered

    

def saveImage(image, path, x0, y0, EPSG):
    if image.ndim == 2:
        image = image[np.newaxis,:,:]
    nb_bands = image.shape[0]
    driver = gdal.GetDriverByName('GTiff')
    outRaster = driver.Create(path, image.shape[2], image.shape[1], nb_bands, gdal.GDT_Byte)
    outRaster.SetGeoTransform((x0, resolution, 0, y0, 0, -resolution))
    for i in range(nb_bands):
        outband = outRaster.GetRasterBand(i+1)
        outband.WriteArray(image[i,:,:])
    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(EPSG)
    outRaster.SetProjection(outSpatialRef.ExportToWkt())


def getOrthoImage(shot, x0, y0, nbCouleurs, path_ortho):
    path = os.path.join(outdir, "Ort_{}.tif".format(shot.nom))
    inputds = gdal.Open(path)
    geotransform = inputds.GetGeoTransform()

    j = (x0-geotransform[0])/resolution
    i = (geotransform[3]-y0)/resolution

    min_c = int(np.floor(j))
    max_c = min_c+tileSize
    min_l = int(np.floor(i))
    max_l = min_l+tileSize

    path2 = os.path.join(path_ortho, "Ort_{}.tif".format(shot.nom))
    inputds = gdal.Open(path2)

    # Coordonnées pour lire une partie de l'image même si dans l'idéal on a besoin d'une partie en-dehors de l'image
    min_c_read = max(0, min_c)
    max_c_read = min(inputds.RasterXSize-1, max_c)
    min_l_read = max(0, min_l)
    max_l_read = min(inputds.RasterYSize-1, max_l)

    if min_l > inputds.RasterYSize or min_c > inputds.RasterXSize or max_l < 0 or max_c < 0:
        return None

    if max_c_read-min_c_read < 0 or max_l_read-min_l_read < 0:
        return None

    image = inputds.ReadAsArray(min_c_read, min_l_read, max_c_read-min_c_read, max_l_read-min_l_read)
    finalImage = np.zeros((nbCouleurs, tileSize, tileSize), dtype=np.uint8)
    finalImage[:,min_l_read-min_l:max_l_read-min_l, min_c_read-min_c:max_c_read-min_c] = image

    return finalImage


def get_path_ortho():
    """
    S'il y a trop de trous dans les orthos, il est possible que la correction radiométrique n'ait pas fonctionné.
    En effet, elle se base sur des points qui se recouvrent entre les images
    Dans ce cas, on utilise les images sans correction radiométrique
    """
    with open(os.path.join(radiom, "ini", "coef_reetal_walis.txt"), "r") as f:
        for line in f:
            if "nan" in line or "Exception" in line:
                logger.warning("Attention, la correction radiométrique a échoué ! L'ortho n'utilisera donc pas la correction radiométrique")
                return outdir
    return os.path.join(radiom, "ini", "corr")


def createOrthoTile(mosaic, shotsFiltered, x0, y0, nbCouleurs, path_ortho):
    orthosImages = []
    # Pour chaque image, on crée une ortho
    for shot in shotsFiltered:
        orthoImage = getOrthoImage(shot, x0, y0, nbCouleurs, path_ortho)
        orthosImages.append(orthoImage)

    # Si une des orthos est None, alors on la remplace par une autre
    aNoneOrtho = []
    aNotNoneortho = None
    for i, o in enumerate(orthosImages):
        if o is None:
            aNoneOrtho.append(i)
        else:
            aNotNoneortho = o
    
    # S'il y a au moins une ortho None et une ortho qui n'est pas None
    if len(aNoneOrtho) > 0 and aNotNoneortho is not None:
        # On remplace les orthos None par une ortho qui n'est pas None
        for i in aNoneOrtho:
            orthosImages[i] = aNotNoneortho
    # S'il n'y a que des orthos None, on renvoie None
    elif len(aNoneOrtho) > 0 and aNotNoneortho is None:
        return None

    # S'il y a qu'une seule ortho, on la renvoie
    if len(orthosImages) == 1:
        return orthosImages[0]
    elif len(orthosImages) >= 2:
        # S'il y en a plusieurs, alors on utilise le graphe de mosaïquage pour faire la reconstruction
        orthoFinale = np.zeros(orthosImages[0].shape)
        for i in range(len(orthosImages)):
            orthoFinale = np.where(mosaic==i, orthosImages[i], orthoFinale)
        return orthoFinale
    return None


def createOrthoProcess(work_data):
    x0 = work_data[0]
    y0 = work_data[1]
    nbCouleurs = work_data[2]
    EPSG = work_data[3]
    path_ortho = work_data[4]
    shots = work_data[5]

    # On calcule la mosaïque
    mosaic, shots_filtered = computeMosaic(x0, y0, shots)
    
    # On crée l'ortho pour la tuile
    ortho = createOrthoTile(mosaic, shots_filtered, x0, y0, nbCouleurs, path_ortho)
    if ortho is not None:
        # On sauvegarde l'ortho
        saveImage(ortho, os.path.join(outdir, "{}_{}_ortho.tif".format(x0, y0)), x0, y0, EPSG)
    


def createTiles(bbox, shots, nbCouleurs, EPSG, path_ortho):
    work_data = []
    # On crée un tableau numpy qui contient les positions des sommets de prise de vue pour tous les clichés
    pas = int(tileSize*resolution)
    # Pour chaque tuile, on remplit work_data avec les paramètres pour le traitement
    for x0 in range(int(bbox[0]), int(bbox[2]), pas):
        for y0 in range(int(bbox[3]), int(bbox[1]), -pas):
            work_data.append([x0, y0, nbCouleurs, EPSG, path_ortho, shots])
    
    # On parallélise le traitement
    with Pool(processes=nb_cpus) as pool:
        with tqdm(total=len(work_data), desc="Calcul de l'ortho") as pbar:
            for i in pool.map(createOrthoProcess, work_data):
                pbar.update()

def getCalibrationFile(path):
    files = os.listdir(path)
    for file in files:
        if file[:11] == "AutoCal_Foc":
            return os.path.join(path, file)
    raise Exception("No calibration file in {}".format(path))

def read_mosaique(shots, mosaic_file):
    mosaique = []
    emprises_mosaique = gpd.read_file(mosaic_file)
    for i in range(emprises_mosaique.shape[0]):
        raw = emprises_mosaique.iloc[i]
        geometry = raw.geometry
        for j in range(len(shots)):
            if shots[j].imagePath==raw["shot"]:
                mosaique.append((geometry, j))
    return mosaique


os.makedirs(outdir, exist_ok=True)

mnt = MNT(mnt_path)

# On charge la boite englobante du chantier
bbox = load_bbox("metadata")

resolution = getResolution()
nbCouleurs = getNbCouleurs("metadata")
EPSG = getEPSG("metadata")


# On récupère les paramètres de calibration de la caméra
calibrationFile = getCalibrationFile(ori_path)
calibration = Calibration.createCalibration(calibrationFile)

# On crée un objet shot par image
shots = loadShots(ori_path, EPSG, calibration)
mosaique = read_mosaique(shots, mosaic_file)

# On récupère le réeprtoire où se trouvent les orthos pour chaque image
# Si la correction radiométrique n'a pas fonctionné, alors on prend celles sans correction radiométrique
path_ortho = get_path_ortho()

# Crée les tuiles d'ortho
createTiles(bbox, shots, nbCouleurs, EPSG, path_ortho)