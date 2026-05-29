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
from epipolarGeometry import EpipolarGeometry
from shapely import Polygon, Point
from typing import List, Tuple, Dict
import json
import geopandas as gpd
from pathlib import Path
from scipy.interpolate import griddata

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Crée une ortho pour chaque image")
parser.add_argument('--ori', help="Répertoire contenant les fichiers orientations")
parser.add_argument('--ta', help="Fichier TA")
args = parser.parse_args()

ori_path = args.ori
ta_path = args.ta

epipDir = Path("epipDir")
mnsDir = Path("mns_ia")
os.makedirs(mnsDir, exist_ok=True)


def build_index_shot(shots:List[Shot], EPSG):
    geometry = []
    indice = []
    for i, shot in enumerate(shots):
        geometry.append(Point(shot.x_pos, shot.y_pos))
        indice.append(i)
    return gpd.GeoDataFrame({"geometry":geometry, "indice":indice}).set_crs(epsg=EPSG)


def get_shot_from_nom(shots, nom):
    for shot in shots:
        if shot.nom==nom:
            return shot

def get_shots(tile_dir, shots)->Tuple[Shot, Shot, Dict]:
    with open(epipDir/tile_dir/"info.json", "r") as f:
        infos = json.load(f)

    shot1 = get_shot_from_nom(shots, infos["image_left"])
    shot2 = get_shot_from_nom(shots, infos["image_right"])
    return shot1, shot2, infos



def load_images(tile_dir):
    
    c1_im = rasterio.open(epipDir/tile_dir/"c1_im.tif").read()
    disparity = rasterio.open(epipDir/tile_dir/"disparity.tif").read()
    disparity = disparity[:,:c1_im.shape[1], :c1_im.shape[2]].reshape((-1))
    c1_im = c1_im.reshape((-1))
    l1_im = rasterio.open(epipDir/tile_dir/"l1_im.tif").read().reshape((-1))
    return disparity, c1_im, l1_im


def find_pseudo_intersections(S1, S2, D1, D2):
    """
    Calcule les pseudo-intersections pour n paires de droites.
    
    S1, S2 : array_like de forme (3,) ou (3, 1) -> Les deux sommets de prise de vue.
    D1, D2 : ndarray de forme (3, n) -> Les n coefficients directeurs (vecteurs directeurs).
    
    Retourne :
    P : ndarray de forme (3, n) -> Les coordonnées des n pseudo-intersections.
    """
    # S'assurer que les sommets sont des vecteurs colonnes (3, 1)
    S1 = np.array(S1).reshape((3, 1))
    S2 = np.array(S2).reshape((3, 1))
    
    # 1. Normalisation des vecteurs directeurs pour éviter les biais d'échelle
    D1 = D1 / np.linalg.norm(D1, axis=0)
    D2 = D2 / np.linalg.norm(D2, axis=0)
    
    # Le vecteur reliant les deux sommets
    dS = S2 - S1  # Forme (3, 1)
    
    # On va résoudre un système 2x2 pour chaque n : A * [t1, t2]^T = B
    # Pour chaque colonne i, on cherche les coefficients t1 et t2 tels que :
    # S1 + t1*D1 et S2 + t2*D2 soient les points les plus proches.
    
    # Construction des coefficients de la matrice A (taille n,)
    # Produit scalaire de D1 et D2 pour chaque colonne
    dot_d1_d2 = np.einsum('ij,ij->j', D1, D2) 
    
    # Matrice A pour les n systèmes : shape (n, 2, 2)
    # [[ 1,       -dot_d1_d2],
    #  [ dot_d1_d2,       -1]]
    n = D1.shape[1]
    A = np.zeros((n, 2, 2))
    A[:, 0, 0] = 1.0
    A[:, 0, 1] = -dot_d1_d2
    A[:, 1, 0] = dot_d1_d2
    A[:, 1, 1] = -1.0
    
    # Construction du second membre B : shape (n, 2)
    # B[0] = dot(dS, D1), B[1] = dot(dS, D2)
    B = np.zeros((n, 2))
    B[:, 0] = np.sum(dS * D1, axis=0)
    B[:, 1] = np.sum(dS * D2, axis=0)
    
    # Résolution simultanée des n systèmes 2x2
    # t shape: (n, 2) -> contient [t1, t2] pour chaque paire
    B = B[:,:,None]
    t = np.linalg.solve(A, B)
    
    t1 = t[:, 0] # Shape (n,)
    t2 = t[:, 1] # Shape (n,)
    
    # Calcul des points les plus proches sur la droite 1 et la droite 2
    # shape (3, n)
    t1 = t1.reshape((-1))
    t2 = t2.reshape((-1))
    P1 = S1 + t1 * D1  
    P2 = S2 + t2 * D2  
    
    # La pseudo-intersection est le milieu du segment joignant les deux points les plus proches
    P = (P1 + P2) / 2.0
    
    return P


def interpolate_to_grid(P, x_min, x_max, y_min, y_max, resolution):
    """
    Interpole des points 3D irréguliers sur une grille 2D régulière.
    
    P : ndarray de forme (3, n) -> Les n pseudo-intersections (X, Y, Z).
    x_min, x_max : Limites en X de la grille.
    y_min, y_max : Limites en Y de la grille.
    resolution : Taille de la maille (ex: 0.5 pour un point tous les 50cm).
    
    Retourne :
    grid_x : ndarray 2D -> Coordonnées X de la grille.
    grid_y : ndarray 2D -> Coordonnées Y de la grille.
    grid_z : ndarray 2D -> Valeurs Z interpolées sur la grille.
    """
    # 1. Extraction des coordonnées de tes points (3, n) -> (n,)
    x_points = P[0, :]
    y_points = P[1, :]
    z_points = P[2, :]
    
    # 2. Création des axes réguliers en fonction des limites et de la résolution
    # On ajoute "resolution" à la fin pour être sûr d'inclure la borne max
    x_axis = np.arange(x_min, x_max + resolution, resolution)
    y_axis = np.flip(np.arange(y_min, y_max + resolution, resolution))
    
    # 3. Génération de la grille 2D (matrices de coordonnées)
    grid_x, grid_y = np.meshgrid(x_axis, y_axis)
    
    # 4. Interpolation
    # 'linear' est souvent le meilleur compromis. 
    # Tu peux aussi tester 'cubic' (plus lisse) ou 'nearest' (pas de trous).
    points_coordonnees = np.vstack((x_points, y_points)).T  # Shape (n, 2)
    
    grid_z = griddata(
        points=points_coordonnees, 
        values=z_points, 
        xi=(grid_x, grid_y), 
        method='nearest'
    )

    grid_z = grid_z.reshape((grid_y.shape[0], grid_x.shape[0]))
    
    return grid_z


def run_one_tile(tile_dir, shots):
    shot1, shot2, infos = get_shots(tile_dir, shots)
    disparity, c1_im, l1_im = load_images(tile_dir)
    r1e = np.load(epipDir/tile_dir/"r1e.npy")
    r2e = np.load(epipDir/tile_dir/"r2e.npy")
    epipolarGeometry = EpipolarGeometry.load(shot1, shot2, r1e, r2e)
    c1_epip, l1_epip = epipolarGeometry.image_to_epip(c1_im, l1_im, shot1, r1e)
    c2_epip = c1_epip - infos["diff_c"] - disparity
    l2_epip = l1_epip - infos["diff_l"]

    c2_im, l2_im = epipolarGeometry.epip_to_image(c2_epip, l2_epip, shot2, r2e)

    dc_image1 = DistorsionCorrection(shot1.calibration)
    c1_corr, l1_corr = dc_image1.reverse_distorsion(c1_im, l1_im)

    dc_image2 = DistorsionCorrection(shot2.calibration)
    c2_corr, l2_corr = dc_image2.reverse_distorsion(c2_im, l2_im)

    vec1 = shot1.get_vect_unitaire(c1_corr, l1_corr)
    vec2 = shot2.get_vect_unitaire(c2_corr, l2_corr)


    S1 = shot1.get_sommet()
    S1 = np.array(shot1.world_to_euclidean(S1[0], S1[1], S1[2]))

    S2 = shot2.get_sommet()
    S2 = np.array(shot2.world_to_euclidean(S2[0], S2[1], S2[2]))


    P = find_pseudo_intersections(S1, S2, vec1, vec2)

    P = shot1.euclidean_to_world(P[0], P[1], P[2])
    P = np.array(P)
    with open(epipDir/tile_dir/"nuage.xyz", "w") as f:
        for i in range(P.shape[1]):
            f.write(f"{P[0,i]},{P[1,i]},{P[2,i]}\n")

    resolution = infos["resolution"]
    size = int(infos["tile_size"])
    x_min = infos["x0"]
    x_max = x_min+size
    y_min = infos["y0"]-size
    y_max = infos["y0"]
    
    mns = interpolate_to_grid(P, x_min, x_max, y_min, y_max, resolution)
    mns = mns[None,:,:]
    
    transform = rasterio.Affine(resolution, 0, x_min, 0, -resolution, y_max)
    save_image(mns, mnsDir/f"mnsIA_{int(x_min)}_{int(y_max)}.tif", transform, np.float32)

def run_tiles(shots):
    tiles_dir = [i for i in os.listdir(epipDir) if os.path.isdir(epipDir/i)]
    for tile_dir in tqdm(tiles_dir):
        run_one_tile(tile_dir, shots)


def save_image(image, path, transform, encoding):
    dictionnaire = {
            'interleave': 'Band',
            'tiled': True
        }
    with rasterio.open(
        path, "w",
        driver = "GTiff",
        transform = transform,
        dtype = encoding,
        count = image.shape[0],
        width = image.shape[2],
        height = image.shape[1],
        **dictionnaire) as dst:
        dst.write(image)

#On récupère l'EPSG du chantier
EPSG = getEPSG("metadata")

resolution = getResolution()
nbCouleurs = getNbCouleurs("metadata")


# On crée un objet shot par image
shots = read_ori(ori_path, ta_path, EPSG)

index_shots = build_index_shot(shots, EPSG)
run_tiles(shots)