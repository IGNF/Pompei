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
from equations import Shot, Calibration
import numpy as np
from multiprocessing import Pool
from tools import load_bbox, getResolution, getEPSG, loadShots
import logging
from tqdm import tqdm
from shapely import Point, voronoi_polygons, MultiPoint, Polygon, LineString, intersection, MultiLineString, polygonize_full, make_valid, difference, within
from shapely.geometry import box
from shapely.ops import split
import geopandas as gpd
import rasterio
from rasterio import Affine
from scipy.signal import convolve
import skimage
from typing import List, Tuple
import argparse

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Calcul automatique des lignes de mosaïquages optimisées")
parser.add_argument('--ori', help="Répertoire contenant les fichiers orientations")
parser.add_argument('--cpu', help="Nombre de cpus à utiliser", type=int)
parser.add_argument('--metadata', help="Répertoire contenant les métadonnées")
parser.add_argument('--mosaic', help="Fichier où sauvegarder la mosaïque")
parser.add_argument('--ortho', help="Répertoire où sauvegarder les orthos")
args = parser.parse_args()

ori_path = args.ori
nb_cpus = args.cpu
metadata = args.metadata
mosaic_path = args.mosaic
ortho_path = args.ortho


def voronoi(shots:List[Shot], emprise:Polygon)->List[LineString]:
    """
    Construit le diagramme de Voronoï à partir des sommets de prise de vue
    """
    
    # On récupère les positions des sommets de prise de vue des clichés
    points:List[Point] = []
    for shot in shots:
        points.append(Point(shot.x_pos, shot.y_pos))

    # On calcule le diagramme de Voronoï. On récupère le résultat sous forme de lignes
    lines = voronoi_polygons(MultiPoint(points), extend_to=emprise, only_edges=True)
    
    # On découpe le résultat selon l'emprise du chantier (extend_to ne semble pas fonctionner...)
    lines = intersection(lines, emprise)

    gpd.GeoDataFrame({"geometry":lines.geoms}).set_crs(epsg=2154).to_file("voronoi.gpkg")

    return lines.geoms



def get_two_shots(line:LineString, shots:List[Shot])->List[Shot]:
    """
    Récupère les deux images qui sont séparées par la ligne de mosaïquage
    """
    # pour chaque image, on calcule sa distance au centre de la ligne
    center = line.centroid
    distances = {}
    for shot in shots:
        distance = np.sqrt((shot.x_pos-center.x)**2 + (shot.y_pos-center.y)**2)
        distances[shot.imagePath] = {"distance":distance, "shot":shot}

    # On renvoie les deux images pour lesquelles la distance est la plus courte 
    # (et, comme ils s'agit de diagramme de Voronoï, les deux distances sont égales)
    two_shots = [v["shot"] for k, v in sorted(distances.items(), key=lambda item: item[1]["distance"])][:2]
    return two_shots

def get_image_box(image:str, ortho_path:str)->Polygon:
    """
    Renvoie l'emprise au sol de l'image
    """
    path = os.path.join(ortho_path, f"Ort_{image}")
    ds = rasterio.open(path)
    bounds = ds.bounds
    return box(*bounds)



def get_intersection(two_shots:List[Shot], line:LineString, ortho_path:str) ->Tuple[Polygon, LineString, LineString]:
    """
    Renvoie l'intersection entre :
    - l'image 1
    - l'image 2
    - la boîte englobante de la ligne avec un buffer de 300 pixels

    Renvoie également :
    - le morceau de ligne à l'intérieur de l'intersection
    - le morceau de ligne à l'extérieur de l'intersection
    """
    
    # On récupère les emprises des deux images
    image_1_box = get_image_box(two_shots[0].imagePath, ortho_path)
    image_2_box = get_image_box(two_shots[1].imagePath, ortho_path)

    # On veut un buffer de 300 pixels
    resolution = getResolution()
    buffer_size = 300*resolution
    
    # On récupère la boîte englobante de la ligne, avec un buffer de 300 pixels
    # Dans le cas, d'une ligne parfaitement verticale, sans buffer, on n'aurait aucun choix pour calculer une nouvelle ligne de mosaïquage
    line_bounds = line.bounds
    line_box = box(*line_bounds).buffer(buffer_size)
    
    # On calcule l'intersection des trois polygones
    geom_intersect = intersection(line_box, intersection(image_1_box, image_2_box))

    if geom_intersect.is_empty:
        return geom_intersect, None, line
    
    
    # On réduit la ligne de mosaïquage au résultat de l'intersection et on recommence
    # En effet, cela permet de réduire la surface de recherche au strict minimum. 
    line_reduce = intersection(line, geom_intersect)
    line_bounds = line_reduce.bounds
    line_box = box(*line_bounds).buffer(buffer_size)

    # On calcule la nouvelle intersection
    geom_intersect = intersection(line_box, intersection(image_1_box, image_2_box))
    # On récupère la partie de la ligne contenue dans l'intersection
    line_reduce = intersection(line, geom_intersect)
    # On récupère la partie de la ligne qui n'est pas dans l'intersection.
    line_remove = difference(line, geom_intersect)
    return geom_intersect, line_reduce, line_remove


def open_image(shot:Shot, geom_intersect:Polygon, ortho_path:str)->Tuple[np.ndarray, Affine]:
    """
    Renvoie le morceau d'image contenu dans geom_intersect et le transformation correspondante 
    """
    
    # Ouverture de l'image
    path = os.path.join(ortho_path, f"Ort_{shot.imagePath}")
    ds = rasterio.open(path)

    # Calcule de la fenêtre pour sélectionner le morceau voulu de l'image
    transform = ds.transform
    bounds = geom_intersect.bounds
    x_min, y_min, x_max, y_max = bounds
    transformer = rasterio.transform.AffineTransformer(transform)
    i_min, j_min = transformer.rowcol(x_min, y_max)
    i_max, j_max = transformer.rowcol(x_max, y_min)
    window = rasterio.windows.Window(j_min, i_min, j_max-j_min+1, i_max-i_min+1)
    
    # Calcule la transformation correspondante
    new_transform = Affine(transform.a, 0, x_min, 0, transform.e, y_max)
    # Lit l'image
    array = ds.read(window=window)
    array = array.astype(np.int16) #nécessaire lorsque l'on fera des calculs dessus ensuite (abs(im1-im2))
    array = np.mean(array, axis=0)
    array = np.expand_dims(array, 0)
    return array, new_transform


def adjust_image_size(image_1:np.ndarray, image_2:np.ndarray)->Tuple[np.ndarray, np.ndarray]:
    """
    Les deux images n'ont pas la même origine. Il peut y avoir une différence d'un pixel après avoir découpé la surface nécessaire  
    """
    i_max = min(image_1.shape[1], image_2.shape[1])
    j_max = min(image_1.shape[2], image_2.shape[2])
    image_1 = image_1[:,:i_max,:j_max]
    image_2 = image_2[:,:i_max,:j_max]
    return image_1, image_2


def convolution(image_diff:np.ndarray)->np.ndarray:
    """
    On applique un filtre de convolution sur image_diff
    """
    kernel = np.ones((1, 2, 2))/4
    return convolve(image_diff, kernel, mode="same")


def compute_line_distance(line:LineString, transform:Affine, shape:Tuple[int, int])->np.ndarray:
    """
    Construit une image géoréférencée de taille shape et dont la localisation est définie par transform
    Chaque pixel contient la distance en pixel par rapport à la droite
    """
    
    # On calcule les coordonnées dans le monde des pixels dans la grille
    endpoint_x = transform.c + shape[2]*transform.a
    x = np.arange(start=transform.c, stop=endpoint_x, step=transform.a)
    x = x[:shape[2]]

    endpoint_y = transform.f + shape[1]*transform.e
    y = np.arange(start=transform.f, stop=endpoint_y, step=transform.e)
    y = y[:shape[1]]

    xx, yy = np.meshgrid(x, y)

    # On calcule les paramètres de la droite
    p1 = Point(line.coords[0])
    p2 = Point(line.coords[1])
    a = (p2.y-p1.y) / (p2.x-p1.x)
    b = -1
    c = p1.y - a*p1.x

    x = xx.reshape((-1,))
    y = yy.reshape((-1,))

    # On calcule la distance à la droite
    quotient = np.sqrt(a**2+b**2)
    distances = np.abs(a*x + b*y + c) / quotient
    distances = distances.reshape(shape)
    
    # On convertit les distances en pixel
    resolution = getResolution()
    distances = distances / resolution
    return distances


class PixelCarto:

    def __init__(self, ligne, colonne, temps=0, precedent=None, iter=0, sum=0) -> None:
        self.ligne = ligne
        self.colonne = colonne
        self.temps = temps #en heures
        self.precedent:PixelCarto = precedent
        self.iter = iter
        self.sum = sum

    def __eq__(self, value: object) -> bool:
        return self.ligne==value.ligne and self.colonne==value.colonne
    
    def __str__(self):
        return f"{self.ligne}, {self.colonne}, {self.temps}"
    
    def set_temps(self, temps):
        self.temps = temps

    def get_voisins(self, carte:np.ndarray, limite_recherche=None):
        """
        Renvoie les voisins
        """
        voisins = []
        i_j_list = [[i,j] for i in range(-1,2) for j in range(-1,2) if i!=0 or j!=0]
        for elem in i_j_list:
            i, j = elem
            distance = np.sqrt(i**2+j**2)
        
            ligne_voisin = self.ligne+j
            colonne_voisin = self.colonne+i
            # On vérifie que le pixel ajouté n'est pas en-dehors de la carte
            if ligne_voisin>=0 and ligne_voisin<carte.shape[0] and colonne_voisin>=0 and colonne_voisin<carte.shape[1]:
                if limite_recherche is None or (ligne_voisin>=limite_recherche[2] and ligne_voisin<limite_recherche[3] and colonne_voisin>=limite_recherche[0] and colonne_voisin<limite_recherche[1]):
                    penalite = carte[ligne_voisin, colonne_voisin]
                    duree = penalite*distance
                    #duree = penalite
                    voisins.append(PixelCarto(ligne_voisin, colonne_voisin, self.temps+duree, self))
        return voisins


def deja_visite(deja_visite_list, pixel):
    for p in deja_visite_list:
        if pixel==p:
            return True
    return False 


def update_a_visiter(a_visiter, pixel):
    ajouter_pixel = True
    for p in a_visiter:
        if pixel==p:
            if p.temps > pixel.temps:
                p.temps = pixel.temps
                p.precedent = pixel.precedent
            ajouter_pixel = False
    if ajouter_pixel:
        a_visiter.append(pixel)
    return a_visiter


def get_pixel_suivant(a_visiter):
    minimum = a_visiter[0].temps
    pixel_min = a_visiter[0]
    for pixel in a_visiter:
        if pixel.temps < minimum:
            pixel_min = pixel
            minimum = pixel.temps
    return pixel_min


def dikjstra(depart:PixelCarto, arrivee:List[PixelCarto], carte:np.ndarray, limite_recherche=None)->List[PixelCarto]:
    """
    Calcule le plus court chemin entre depart et arrivee sur la carte
    """

    a_visiter = []
    deja_visite_list = []
    pixel = depart

    while pixel not in arrivee:
        # On ajoute le pixel à la liste des pixels déjà visités
        deja_visite_list.append(pixel)
        # On récupère la liste des pixels voisins
        voisins = pixel.get_voisins(carte, limite_recherche)
        for voisin in voisins:
            # Si le pixel voisin ne se trouve pas déjà dans la liste des déjà visités, on l'ajoute
            if not deja_visite(deja_visite_list, voisin):
                a_visiter = update_a_visiter(a_visiter, voisin)

        pixel = get_pixel_suivant(a_visiter)
        a_visiter.remove(pixel)
      
    trajet = [pixel]
    if pixel!=depart:
        while pixel.precedent != depart:
            pixel = pixel.precedent
            trajet.append(pixel)
    trajet.reverse()
    return trajet

def reduire_carte(carte:np.ndarray, facteur:int, transform_init)->Tuple[np.ndarray, Affine]:
    """
    Réduit la carte d'un facteur
    """
    carte_reduite = skimage.measure.block_reduce(carte, (facteur,facteur), np.mean, cval=np.max(carte))
    transform = rasterio.transform.Affine(
        transform_init.a*facteur, 
        transform_init.b*facteur, 
        transform_init.c, 
        transform_init.d*facteur,
        transform_init.e*facteur,
        transform_init.f)
    return carte_reduite, transform


def arrivees_facteur4(pixel:PixelCarto, facteur:int):
    arrivees = []
    for i in range(pixel.ligne*facteur, (pixel.ligne+1)*facteur):
        for j in range(pixel.colonne*facteur, (pixel.colonne+1)*facteur):
            arrivees.append(PixelCarto(i, j))
    return arrivees


def get_limites_recherche(depart:PixelCarto, arrivee:PixelCarto, facteur:int):
    depart_colonne = depart.colonne//facteur
    depart_ligne = depart.ligne//facteur
    min_colonne = min(depart_colonne*facteur, arrivee.colonne*facteur)
    max_colonne = max((depart_colonne+1)*facteur, (arrivee.colonne+1)*facteur)
    min_ligne = min(depart_ligne*facteur, arrivee.ligne*facteur)
    max_ligne = max((depart_ligne+1)*facteur, (arrivee.ligne+1)*facteur)
    return [min_colonne, max_colonne, min_ligne, max_ligne]


def trouverTrajet(depart:PixelCarto, arrivee:PixelCarto, carte_penalite:np.ndarray, transform, EPSG, i)->List[PixelCarto]:

    carte_penalite = np.squeeze(carte_penalite)

    
    # On réduit la carte d'un facteur 32 en gardant à chaque endroit la moyenne des 32**2 cases
    carte_reduite, transform_32 = reduire_carte(carte_penalite, 32, transform)

    depart_32 = PixelCarto(depart.ligne//32, depart.colonne//32)
    arrivee_32 = PixelCarto(arrivee.ligne//32, arrivee.colonne//32)
    # On cherche l'itinéraire sur la carte réduite d'un facteur 32
    # Renvoie tous les pixels par lesquels il faut passer, sans compter le pixel où se trouve l'unité
    trajet_32 = dikjstra(depart_32, [arrivee_32], carte_reduite)


    carte_reduite, transform_16 = reduire_carte(carte_penalite, 16, transform)
    depart_16 = PixelCarto(depart.ligne//16, depart.colonne//16)
    trajet_16 = []
    for arrivee_16 in trajet_32:
        limite_recherche = get_limites_recherche(depart_16, arrivee_16, int(32/16))
        arrivees_16 = arrivees_facteur4(arrivee_16, int(32/16))
        trajet_16 += dikjstra(depart_16, arrivees_16, carte_reduite, limite_recherche)
        depart_16 = trajet_16[-1]

    # Cette fois, on cherche l'itinéraire sur la carte réduite d'un facteur 4
    carte_reduite, transform_4 = reduire_carte(carte_penalite, 4, transform)
    depart_4 = PixelCarto(depart.ligne//4, depart.colonne//4)
    trajet_4 = []
    for arrivee_4 in trajet_16:
        limite_recherche = get_limites_recherche(depart_4, arrivee_4, int(16/4))
        arrivees_4 = arrivees_facteur4(arrivee_4, int(16/4))
        trajet_4 += dikjstra(depart_4, arrivees_4, carte_reduite, limite_recherche)
        depart_4 = trajet_4[-1]

    trajet_1 = []
    depart_1 = depart
    # Puis on cherche l'itinéraire sur la carte à pleine résolution
    for arrivee_1 in trajet_4:
        limite_recherche = get_limites_recherche(depart_1, arrivee_1, int(4/1))
        arrivees_1 = arrivees_facteur4(arrivee_1, int(4/1))
        trajet_1 += dikjstra(depart_1, arrivees_1, carte_penalite, limite_recherche)
        depart_1 = trajet_1[-1]
    limites = [arrivee_16.colonne*32, (arrivee_16.colonne+1)*32, arrivee_16.ligne*32, (arrivee_16.ligne+1)*32]
    trajet_1 += dikjstra(depart_1, [arrivee], carte_penalite, limites)
    return trajet_1


def convert_point_to_pixel_carto(point:Point, transform:Affine, size:Tuple[int])->PixelCarto:
    """
    Convertit un objet de type Point en un objet PixelCarto
    """
    colonne = int((point.x - transform.c) / transform.a)
    ligne = int((point.y - transform.f) / transform.e)
    
    # On vérifie que l'arrivée ne se trouve pas en-dehors de la carte
    if ligne >= size[1]:
        ligne = size[1]-1
    
    if colonne >= size[2]:
        colonne = size[2]-1
    return PixelCarto(ligne, colonne)


def trajet_to_proj(trajet:List[PixelCarto], transform:Affine, p1:Point, p2:Point, line_remove:LineString)->LineString:
    """
    Transforme une liste de PixelCarto en une LineString
    """
    points = [p1]
    for pixelCarto in trajet[4:-4]:# On supprime les quatre premiers et les quatre derbiers éléments pour éviter les problèmes de géométrie
        x = pixelCarto.colonne * transform.a + transform.c
        y = pixelCarto.ligne * transform.e + transform.f
        points.append(Point(x,y))
    points.append(p2)

    # Si une partie de la ligne avait été retirée car en dehors de l'intersection des deux images, alors on l'ajoute ici. 
    # Ainsi, la ligne de mosaïquage parvient jusqu'à l'emprise 
    if not line_remove.is_empty:
        if isinstance(line_remove, LineString):
            lines_remove = [line_remove]
        else:# Si les deux extrémités de la ligne ont été coupées
            lines_remove = line_remove.geoms
        
        for line_remove in lines_remove:
            p_remove_1 = Point(line_remove.coords[0])
            p_remove_2 = Point(line_remove.coords[1])
            p1 = points[0]
            p2 = points[-1]

            if p_remove_1==p1:
                points = [p_remove_2] + points
            elif p_remove_1==p2:
                points.append(p_remove_2)
            elif p_remove_2==p1:
                points = [p_remove_1] + points
            elif p_remove_2==p2:
                points.append(p_remove_1)

    linestring = LineString(points)
    return linestring


def optimize_line(args:Tuple[LineString, Shot, int, int, str])->Tuple[LineString, List[Shot]]:
    line, shots, EPSG, i, ortho_path = args

    # On récupère les deux images qui sont séparées par la ligne
    two_shots:List[Shot] = get_two_shots(line, shots)

    # On récupère :
    # - l'intersection entre la ligne et les emprises des deux images
    # - le morceau de la ligne dans l'intersection
    # - le morceau de la ligne en-dehors de l'intersection
    geom_intersect, line, line_remove = get_intersection(two_shots, line, ortho_path)

    if line is None:# Cas où il n'y a pas d'intersection entre les deux images. C'est possible au bord des chantiers dans les angles
        return line_remove, two_shots


    # On ouvre dans les deux images la partie correspondant à l'intersection calculée ci-dessus
    image_1, transform_1 = open_image(two_shots[0], geom_intersect, ortho_path)
    image_2, _ = open_image(two_shots[1], geom_intersect, ortho_path)
    
    # Si force les deux images à avoir les mêmes tailles
    image_1, image_2 = adjust_image_size(image_1, image_2)


    # A présent, on calcule la carte de pénalité. Elle comprend deux composantes :
    # - la différence de radiométrie entre les deux images
    # - une distance à la ligne calculée dans le diagramme de Voronoï

    # On calcule la différence de radiométrie entre les deux images 
    image_diff = np.abs(image_1-image_2)**2

    # On applique un filtre pass-bas sur la différence entre les deux images
    # L'idée, c'est qu'à présent, chaque cellule du tableau numpy représente la différence moyenne sur chaque intersection de image_diff
    # Est-ce que c'est vraiment utile ? Bonne question...
    image_diff_conv = convolution(image_diff)
    
    # On calcule la distance à la ligne de Voronoï
    distances = compute_line_distance(line, transform_1, image_diff.shape)

    # Coefficient de l'importance de la distance à la droite initiale par rapport à la différence de radiométrie
    # Il faut aussi avoir en tête que plus la ligne sera loin de la ligne initiale, plus le nombre de pixels 
    # parcourus (et donc la distance) sera élevée. Un seuil assez faible suffit.
    seuil = 0.005
    carte_poids = seuil * distances + image_diff_conv

    # On convertit en objet PixelCarto les deux extrémités de la ligne
    p1 = Point(line.coords[0])
    p2 = Point(line.coords[1])
    depart = convert_point_to_pixel_carto(p1, transform_1, image_1.shape)
    arrivee = convert_point_to_pixel_carto(p2, transform_1, image_1.shape)
    
    # On cherche le trajet le plus court dans la carte de pénalité entre les deux extrémités de la droite
    trajet = trouverTrajet(depart, arrivee, carte_poids, transform_1, EPSG, i)

    # On récupère sous forme de LineString le trajet auquel on ajoute la partie de la ligne qui est en-dehors de l'intersection des images
    line_optimized = trajet_to_proj(trajet, transform_1, p1, p2, line_remove)
    return line_optimized, two_shots

def polygon_to_linestring(emprise:Polygon)->LineString:
    """
    On récupère le contour du Polygone sous forme de LineString
    """
    lines = []
    boundary = emprise.boundary
    if boundary.geom_type == 'MultiLineString':
        for line in boundary:
            lines.append(line)
    else:
        lines.append(boundary)
    return lines
    

def getCalibrationFile(path):
    files = os.listdir(path)
    for file in files:
        if file[:11] == "AutoCal_Foc":
            return os.path.join(path, file)
    raise Exception("No calibration file in {}".format(path))



# On charge l'EPSG et la boîte englobante du chantier
EPSG:int = getEPSG(metadata)
bbox:List[float] = load_bbox(metadata)

# On crée un polygone qui contient la boîte englobante du projet
emprise = Polygon([[bbox[0], bbox[1]], [bbox[2], bbox[1]], [bbox[2], bbox[3]], [bbox[0], bbox[3]]])

# On récupère les paramètres de calibration de la caméra
calibrationFile = getCalibrationFile(ori_path)
calibration = Calibration.createCalibration(calibrationFile)

# On récupère les images et leurs orientations
shots:List[Shot] = loadShots(ori_path, EPSG, calibration)

# On crée une première approximation des lignes de mosaïquage en utilisant le diagramme de Voronoï
lines = voronoi(shots, emprise)


# On parallélise les calculs de ligne de mosaïquage : chaque ligne est calculée en parallèle
arguments = []
for i, line in enumerate(lines):
    arguments.append([line, shots, EPSG, i, ortho_path])

lignes_optimisees : List[LineString] = [] # Contient les lignes optimisées

# shot1 et shot2 : pour chaque ligne, contient les deux images que la ligne sépare
shot1:List[str] = []
shot2:List[str] = []
with Pool(processes=nb_cpus) as pool:
    with tqdm(total=len(arguments), desc="Calcul des lignes de mosaïquages") as pbar:
        for line, two_shots in pool.imap_unordered(optimize_line, arguments):
            lignes_optimisees.append(line)
            shot1.append(two_shots[0].imagePath)
            shot2.append(two_shots[1].imagePath)
            pbar.update()

# On récupère le contour du polygone sous forme de LineString
emprise_lines = polygon_to_linestring(emprise)
# On rend la géométrie valide
lignes_optimisees = list(make_valid(lignes_optimisees))
# On divise les lignes de l'emprise pour qu'on ait un tronçon entre deux lignes de mosaïquages
emprise_lines = list(split(MultiLineString(emprise_lines), MultiLineString(lignes_optimisees)).geoms)


# On dispose de lignes de mosaïquages et des lignes délimitant le contour
# Il faut à présent reconstruire des polygones et indiquer en tout point du chantier quelle image utiliser pour reconstruire l'ortho

polygones = []
shot_names = []
# On parcourt toutes les images
for shot in shots:
    all_polygones = []
    # On récupère les trois lignes de bordure du chantier les plus proches du sommet de prise de vue de l'image
    lignes = [i for i in emprise_lines]
    
    # On récupère toutes les lignes de mosaïquages optimisées qui délimitent l'image
    for i in range(len(lignes_optimisees)):
        if shot1[i]==shot.imagePath or shot2[i]==shot.imagePath:
            lignes.append(lignes_optimisees[i])
    
    # On recherche les polygones parmi ces lignes
    valid, _, _, not_valid = polygonize_full(lignes)
    for poly in valid.geoms:
        all_polygones.append(poly)

    for poly in not_valid.geoms:
        all_polygones.append(Polygon(poly.coords))

    centre = Point(shot.x_pos, shot.y_pos)
    for poly in all_polygones:
        if within(centre, poly):
            polygones.append(poly)
            shot_names.append(shot.imagePath)

gpd.GeoDataFrame({"shot":shot_names, "geometry":polygones}).set_crs(epsg=EPSG).to_file(mosaic_path)