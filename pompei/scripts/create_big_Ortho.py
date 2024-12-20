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
from equations import Shot, MNT 
from lxml import etree
import numpy as np
from osgeo import gdal, osr
from multiprocessing import Pool
from tools import getEPSG, load_bbox, getNbCouleurs, getResolution, get_resol_scan
import log # Chargement des configurations des logs
import logging
from tqdm import tqdm

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Crée un nouveau fichier TA avec les valeurs déterminées pendant le chantier (orientation, position...")

parser.add_argument('--ta_xml', help="Fichier TA avec les positions mises à jour")
parser.add_argument('--ori', help="Répertoire contenant les fichiers orientations")
parser.add_argument('--cpu', help="Nombre de cpus à utiliser", type=int)
parser.add_argument('--mnt', help="MNT sous format vrt")
parser.add_argument('--radiom', help="Répertoire avec les images égalisées")
parser.add_argument('--outdir', help="Répertoire contenant les fichiers orientations")
args = parser.parse_args()

ta_xml = args.ta_xml
ori_path = args.ori
nb_cpus = args.cpu
mnt_path = args.mnt
outdir = args.outdir
radiom = args.radiom

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
    pixel_size = get_resol_scan(os.path.join(os.path.dirname(ta_xml), "metadata"))
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


def createSommetsArray(shots, nb_points):
    m = len(shots)
    array = np.zeros((m, 2))
    for i, shot in enumerate(shots):
        x_nadir, y_nadir, z_nadir = shot.image_to_world(shot.x_ppa, shot.y_ppa, mnt)
        array[i,0] = x_nadir
        array[i,1] = y_nadir
    finalArray = np.tile(array, (nb_points, 1))
    return finalArray

def createCornerArray(m, x0, y0):
    """
    Crée un tableau numpy qui contient un sous-échantillonnage de points de la tuile
    """
    size = int(resolution*tileSize)
    pas = int(size / 10)
    
    points = []
    for x in range(0, size+pas, pas):
        for y in range(0, size+pas, pas):
            points.append([x0+x, y0-y])
    n = len(points)
    array = np.zeros((n*m, 2))
    for i, point in enumerate(points):
        for k in range(m):
            array[i*m+k, 0] = point[0]
            array[i*m+k, 1] = point[1]
    return array


def createPixelsArray(m, xx, yy):
    array = np.zeros((xx.shape[0], 2))
    for i in range(xx.shape[0]):
        array[i, 0] = xx[i, 0]
        array[i, 1] = yy[i, 0]
    finalArray = np.repeat(array, m, axis=0)
    return finalArray


def determineShots(sommetsArray, x0, y0, shots):
    # On crée un tableau numpy qui contient un sous-échantillonnage de points de la tuile
    cornerArray = createCornerArray(len(shots), x0, y0)
    
    # On calcule la distance entre les points de la tuile et les sommets de prises de vue
    distances = (cornerArray[:,0]-sommetsArray[:,0])**2 + (cornerArray[:,1]-sommetsArray[:,1])**2
    distances_reshaped = distances.reshape((121, -1))
    
    # On récupère les images pour lesquelles les distances sont minimales
    argmin = np.argmin(distances_reshaped, axis=1)
    uniques = np.unique(argmin)
    shotsFiltered = []
    indicesShotsFiltered = []
    for i in range(uniques.shape[0]):
        shotsFiltered.append(shots[uniques[i]])
        indicesShotsFiltered.append(uniques[i])
    return shotsFiltered, indicesShotsFiltered


def computeMosaic(x0, y0, shots, indicesShotsFiltered):
    """
    Pour chaque pixel de la tuile, on cherche le sommet de prise de vue qui lui est le plus proche
    """
    # S'il n'y a qu'une seule image, alors inutile de faire des calculs
    if len(shots)==1:
        return np.zeros((2000, 2000)), np.ones((2000, 2000))*indicesShotsFiltered[0]
    
    
    x = np.linspace(x0, x0+(tileSize-1)*resolution, tileSize)
    y = np.flip(np.linspace(y0-(tileSize-1)*resolution, y0, tileSize))
    xx, yy = np.meshgrid(x, y)
    xx = xx.reshape((-1, 1))
    yy = yy.reshape((-1, 1))
    pixelsArray = createPixelsArray(len(shots), xx, yy)
    sommetsArray = createSommetsArray(shots, xx.shape[0])

    # On calcule les distances
    distances = (pixelsArray[:,0]-sommetsArray[:,0])**2 + (pixelsArray[:,1]-sommetsArray[:,1])**2
    distances_reshaped = distances.reshape((xx.shape[0], -1))
    
    # On récupère les sommets de prises de vue les plus proches
    argmin = np.argmin(distances_reshaped, axis=1)
    mosaic = argmin.reshape((y.shape[0], x.shape[0]))


    indices = np.zeros((tileSize, tileSize))
    for i in range(len(indicesShotsFiltered)):
        indices = np.where(mosaic==i, np.ones(indices.shape)*indicesShotsFiltered[i], indices)
    # mosaic contient l'indice du sommet de prise de vue dans shots (uniquement les images pour lesquelles au moins un pixel de la tuile est le plus proche)
    # indices contient l'indice pour toutes les images. Sert à la visualisation du graphe de mosaïquage
    return mosaic, indices

    

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
    sommetsArray = work_data[2]
    nbCouleurs = work_data[3]
    EPSG = work_data[4]
    path_ortho = work_data[5]
    
    # On cherche les images à utiliser pour crée l'ortho sur la tuile
    shotsFiltered, indicesShotsFiltered = determineShots(sommetsArray, x0, y0, shots)

    # On calcule la mosaïque
    mosaic, indices = computeMosaic(x0, y0, shotsFiltered, indicesShotsFiltered)
    
    # On sauvegarde la mosaïque
    saveImage(indices, os.path.join(outdir, "{}_{}_mosaic.tif".format(x0, y0)), x0, y0, EPSG)
    
    # On crée l'ortho pour la tuile
    ortho = createOrthoTile(mosaic, shotsFiltered, x0, y0, nbCouleurs, path_ortho)
    if ortho is not None:
        # On sauvegarde l'ortho
        saveImage(ortho, os.path.join(outdir, "{}_{}_ortho.tif".format(x0, y0)), x0, y0, EPSG)
    


def createTiles(bbox, shots, nbCouleurs, EPSG, path_ortho):
    work_data = []
    # On crée un tableau numpy qui contient les positions des sommets de prise de vue pour tous les clichés
    sommetsArray = createSommetsArray(shots, 121)
    pas = int(tileSize*resolution)
    # Pour chaque tuile, on remplit work_data avec les paramètres pour le traitement
    for x0 in range(int(bbox[0]), int(bbox[2]), pas):
        for y0 in range(int(bbox[3]), int(bbox[1]), -pas):
            work_data.append([x0, y0, sommetsArray, nbCouleurs, EPSG, path_ortho])
    
    # On parallélise le traitement
    p = Pool(nb_cpus)
    for i in tqdm(p.imap(createOrthoProcess, work_data), total=len(work_data)):
        pass
            

os.makedirs(outdir, exist_ok=True)

mnt = MNT(mnt_path)

# On charge la boite englobante du chantier
bbox = load_bbox("metadata")

resolution = getResolution()
nbCouleurs = getNbCouleurs("metadata")
EPSG = getEPSG("metadata")

# On crée un objet shot par image
shots = createShots(ta_xml, EPSG)

# On récupère le réeprtoire où se trouvent les orthos pour chaque image
# Si la correction radiométrique n'a pas fonctionné, alors on prend celles sans correction radiométrique
path_ortho = get_path_ortho()

# Crée les tuiles d'ortho
createTiles(bbox, shots, nbCouleurs, EPSG, path_ortho)