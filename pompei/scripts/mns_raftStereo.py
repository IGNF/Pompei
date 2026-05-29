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
from lxml import etree

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
from epipolarGeometry import EpipolarGeometry
from shapely import Polygon, Point
from typing import List, Tuple
import geopandas as gpd
from pathlib import Path
import json

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Crée une ortho pour chaque image")
parser.add_argument('--mnt', help="MNT sous format vrt")
parser.add_argument('--ori', help="Répertoire contenant les fichiers orientations")
parser.add_argument('--ta', help="Fichier TA")
parser.add_argument('--homolDir', help="Répertoire contenant les points homologues")
args = parser.parse_args()

mnt_path = args.mnt
ori_path = args.ori
ta_path = args.ta
homol_dir = Path(args.homolDir)
epipDir = Path("epipDir")
os.makedirs(epipDir, exist_ok=True)

def build_index_shot(shots:List[Shot], EPSG):
    geometry = []
    indice = []
    number = []
    for i, shot in enumerate(shots):
        geometry.append(Point(shot.x_pos, shot.y_pos))
        indice.append(i)
        number.append(shot.number)
    return gpd.GeoDataFrame({"geometry":geometry, "indice":indice, "number":number}).set_crs(epsg=EPSG)

def save_image(image, path, encoding):
    dictionnaire = {
            'interleave': 'Band',
            'tiled': True
        }
    with rasterio.open(
        path, "w",
        driver = "GTiff",
        dtype = encoding,
        count = image.shape[0],
        width = image.shape[2],
        height = image.shape[1],
        **dictionnaire) as dst:
        dst.write(image)

def get_shots(centroid:Point, shots:List[Shot], index_shots:gpd.GeoDataFrame)->Tuple[Shot, Shot]:
    """
    Renvoie les deux images les plus proches de centroid
    """
    distances = index_shots.distance(centroid)
    nearest_idx = distances.nsmallest(1).index
    nearest_shot = shots[nearest_idx[0]]
    index_shots_bande = index_shots[abs(index_shots["number"]-nearest_shot.number)<=2]
    if index_shots_bande.shape[0]==1:
        return None, None
    distances = index_shots_bande.distance(centroid)
    nearest_idx = distances.nsmallest(2).index
    return nearest_shot, shots[nearest_idx[1]]



def run_tile(emprise:Polygon, shots:List[Shot], index_shots:gpd.GeoDataFrame, mnt:MNT, homol_dir:Path, x0, y0, resolution, tile_size):
    
    # On récupère les deux images les plus proches du centre de l'emprise
    shot1, shot2 = get_shots(emprise.centroid, shots, index_shots)
    if shot1 is None:
        return

    # On calcule les géométries épipolaires entre les deux images
    epipolarGeometry = EpipolarGeometry(shot1, shot2, mnt, homol_dir)
    epipolarGeometry.compute()

    
    # On construit un maillage (x,y,z) des points terrains de l'emprise qui nous intéresse
    x_min, y_min, x_max, y_max = emprise.bounds
    x = np.arange(x_min, x_max, resolution)
    y = np.flip(np.arange(y_min, y_max, resolution))
    xx, yy = np.meshgrid(x, y)
    xx = xx.reshape((-1, ))
    yy = yy.reshape((-1, ))
    if xx.shape[0] == 0 or yy.shape == 0:
        return None
    # On récupère l'altitude des pixels
    z = mnt.get(xx, yy)

    # On calcule la paire d'images en géométrie épipolaire
    image_epip_1, image_epip_2, c1_im, l1_im, diff_c, diff_l = epipolarGeometry.compute_epip_images(xx, yy, z, x.shape[0], y.shape[0])

    
    # On sauvegarde les informations nécessaires pour la suite du traitement
    identifiant = str(len(os.listdir(epipDir)))

    output_dir = epipDir/identifiant
    os.makedirs(output_dir, exist_ok=True)

    c1_im = c1_im.reshape(image_epip_1.shape)
    l1_im = l1_im.reshape(image_epip_1.shape)

    save_image(image_epip_1, output_dir/"epip_left.tif", np.uint8)
    save_image(image_epip_2, output_dir/"epip_right.tif", np.uint8)
    save_image(c1_im, output_dir/"c1_im.tif", np.float32)
    save_image(l1_im, output_dir/"l1_im.tif", np.float32)
    np.save(output_dir/"r1e.npy", epipolarGeometry.r1e)
    np.save(output_dir/"r2e.npy", epipolarGeometry.r2e)
    with open(output_dir/"info.json", "w") as f:
        json.dump(
            {
                "image_left":shot1.nom,
                "image_right":shot2.nom,
                "diff_c":diff_c,
                "diff_l": diff_l,
                "x0":x0,
                "y0":y0,
                "resolution":resolution,
                "tile_size":tile_size
            }, f
        )



def run_tiles(bbox, shots, index_shots, mnt:MNT, homol_dir:Path):
    
    #tileSize_px = 5000 # pixels
    pas_px = 440
    recouvrement_px = 100
    # On crée un tableau numpy qui contient les positions des sommets de prise de vue pour tous les clichés
    pas = int(pas_px*resolution)
    recouvrement = int(recouvrement_px*resolution)
    # Pour chaque tuile, on remplit work_data avec les paramètres pour le traitement
    for x0 in range(int(bbox[0]), int(bbox[2]), pas):
        for y0 in range(int(bbox[3]), int(bbox[1]), -pas):
            emprise = Polygon.from_bounds(x0-recouvrement, y0-(pas+recouvrement), x0+(pas+recouvrement), y0+recouvrement)
            gpd.GeoDataFrame({"geometry":[emprise]}).set_crs(epsg=2154).to_file("emprise.gpkg")
            try:
                run_tile(emprise, shots, index_shots, mnt, homol_dir, x0, y0, resolution, pas)
            except:
                pass




def get_nb_bandes(shots, ta_path):
    tree = etree.parse(ta_path)
    root = tree.getroot()

    for bande in root.findall(".//bande"):
        for cliche in bande.findall(".//cliche"):
            cliche_nom = cliche.find("image").text.strip()
            for shot in shots:
                if shot.nom.replace("OIS-Reech_", "")==cliche_nom:
                    shot.number = int(cliche.find("number").text)
                    break




# On charge la boite englobante du chantier
bbox = load_bbox("metadata")

#bbox = [614600, 6245800, 615600, 6246800]
bbox = [613000, 6245800, 616300, 6247900] # Ville complète
#bbox = [615300, 6242800, 617300, 6245000] # Zone complète

#bbox = [614650, 6246900, 614800, 6247100]

#On récupère l'EPSG du chantier
EPSG = getEPSG("metadata")

resolution = getResolution()
nbCouleurs = getNbCouleurs("metadata")


mnt = MNT(mnt_path)


# On crée un objet shot par image
shots = read_ori(ori_path, ta_path, EPSG)

get_nb_bandes(shots, ta_path)

index_shots = build_index_shot(shots, EPSG)
print(index_shots)
index_shots.to_file("index.gpkg")
run_tiles(bbox, shots, index_shots, mnt, homol_dir)




