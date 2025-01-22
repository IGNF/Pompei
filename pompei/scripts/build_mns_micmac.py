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
import rasterio
from lxml import etree
import numpy as np
import argparse

import rasterio.windows
import log # Chargement des configurations des logs
import logging

logger = logging.getLogger()

parser = argparse.ArgumentParser(description='Construction du MNS à partir des Z Num Max')
parser.add_argument('--input_Malt', default='', help='Dossier MEC-Malt')
args = parser.parse_args()

"""
Malt construit le MNS niveau par niveau. Il commence d'abord avec un sous-échantillonage fort pour terminer à un niveau beaucoup plus fin.
A chaque niveau, il dispose d'une carte de corrélation qui indique les lieux où la corrélation fonctionne.
Si à un niveau la corrélation ne fonctionne pas, alros elle ne fonctionnera pas à un niveau plus précis.
L'idée est ici de récupérer pour chaque pixel la dernière altitude calculée avant que la corrélation ne fonctionne plus.
On produit également une carte indicateur.tif qui contient l'identifiant de la couche utilisée. 
"""


class LevelMNS:

    def __init__(self, image_path, first_level, bounds_required=None, dezoom=2) -> None:
        self.image_path = image_path
        self.bounds_required = bounds_required
        self.first_level = first_level
        self.level = int(os.path.basename(image_path)[5])
        self.dezoom = int(dezoom/2)
        self.origineAlti, self.resolutionAlti = self.read_xml()
        self.mns, self.transform, self.bounds = self.compute_mns()
        self.correlation = self.open_correlation()
        
    def open_mns(self):
        """
        Ouvre le MNS calculé par Micmac
        """
        input_dst = rasterio.open(self.image_path)
        transform = input_dst.transform
        if self.bounds_required is not None:
            transformer = rasterio.transform.AffineTransformer(transform)
            l_max, c_min = transformer.rowcol(self.bounds_required[0], self.bounds_required[1])
            l_min, c_max = transformer.rowcol(self.bounds_required[2], self.bounds_required[3])
            image = input_dst.read(window=rasterio.windows.Window(c_min, l_min, c_max-c_min+1, l_max-l_min+1))
        else:
            image = input_dst.read()
        return image, transform, input_dst.bounds
    
    def compute_mns(self):
        """
        Met en forme le MNS calculé par Micmac
        """
        #Ouverture du MNS
        mns, transform, bounds = self.open_mns()
        # Calcul le MNS à partir des métadonnées Micmac
        mns = self.compute_elevation(mns)
        mns = self.resample_image(mns)
        return mns, transform, bounds

    def read_xml(self):
        xml_path = os.path.join(input_Malt, f"Z_Num{self.level}_DeZoom{self.dezoom*2}_STD-MALT.xml")
        tree = etree.parse(xml_path)
        root = tree.getroot()
        origineAlti = float(root.find("OrigineAlti").text)
        resolutionAlti = float(root.find("ResolutionAlti").text)
        resolutionPlani = float(root.find("ResolutionPlani").text.split(" ")[0])
        logger.info(f"La résolution altimétrique du MNS pour l'identifiant {self.level} est de {resolutionAlti} mètres.")
        logger.info(f"La résolution planimétrique du MNS pour l'identifiant {self.level} est de {resolutionPlani} mètres.")
        return origineAlti, resolutionAlti

    
    def compute_elevation(self, mns):
        """
        Calcule le MNS à partir des métadonnées
        """
        mns = mns*self.resolutionAlti + self.origineAlti
        return mns

    
    def resample_image(self, mns):
        """
        Rééchantillonne le MNS de manière à ce que chaque couche soit à la même résolution 
        """
        mns = np.repeat(mns, self.dezoom, axis=1)
        mns = np.repeat(mns, self.dezoom, axis=2)
        return mns
    

    def open_correlation8(self):
        correlation_files = get_correlation(self.level-1)
        if len(correlation_files) > 1:
            os.system(f"gdalbuildvrt {input_Malt}/correlation_{self.level-1}.vrt {input_Malt}/Correl_STD-MALT_Num_{self.level-1}_Tile*tif")
        else:
            os.system(f"gdalbuildvrt {input_Malt}/correlation_{self.level-1}.vrt {input_Malt}/Correl_STD-MALT_Num_{self.level-1}.tif")
        filename = f"correlation_{self.level-1}.vrt"

        input_dst_correl = rasterio.open(os.path.join(input_Malt, filename))
        transform = input_dst_correl.transform
        transformer = rasterio.transform.AffineTransformer(transform)
        l_max, c_min = transformer.rowcol(self.bounds[0], self.bounds[1])
        l_min, c_max = transformer.rowcol(self.bounds[2], self.bounds[3])
        correlation = input_dst_correl.read(window=rasterio.windows.Window(c_min, l_min, c_max-c_min+1, l_max-l_min+1))
        return correlation
    
    def open_correlation(self):
        """
        Ouvre la carte de corrélation
        """
        if self.level != self.first_level:
            correlation_files = get_correlation(self.level)
            if len(correlation_files) > 1:
                os.system(f"gdalbuildvrt {input_Malt}/correlation_{self.level}.vrt {input_Malt}/Correl_STD-MALT_Num_{self.level}_Tile*tif")
            else:
                os.system(f"gdalbuildvrt {input_Malt}/correlation_{self.level}.vrt {input_Malt}/Correl_STD-MALT_Num_{self.level}.tif")
            
            filename = f"correlation_{self.level}.vrt"
            input_dst = rasterio.open(os.path.join(input_Malt, filename))
            transform = input_dst.transform
            transformer = rasterio.transform.AffineTransformer(transform)
            l_max, c_min = transformer.rowcol(self.bounds_required[0], self.bounds_required[1])
            l_min, c_max = transformer.rowcol(self.bounds_required[2], self.bounds_required[3])
            correlation = input_dst.read(window=rasterio.windows.Window(c_min, l_min, c_max-c_min+1, l_max-l_min+1))
        else:
            correlation = self.open_correlation8()
        
        correlation = correlation.astype(np.uint8)
        correlation = self.resample_image(correlation)
        return correlation
        
    def resize(self, l, c):
        """
        Redécoupe le mns et la carte de corrélation pour qu'elle ait la taille définie par c et l
        """
        mns = np.ones((1, l, c))
        correlation = np.ones((1, l, c), dtype=np.uint8)
        l_current, c_current = self.get_size()
        l_min = min(l, l_current)
        c_min = min(c, c_current)
        mns[0,:l_min,:c_min] = self.mns[0,:l_min,:c_min]
        correlation[0,:l_min,:c_min] = self.correlation[0,:l_min,:c_min]
        self.mns = mns
        self.correlation = correlation

    def get_size(self):
        _, l, c = self.mns.shape
        return l, c



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

def get_level(path, level):
    """
    Chaque niveau de la pyramide est soit en un seul fichier (exemple : Z_Num8_DeZoom2_STD-MALT.tif), 
    soit en plusieurs fichiers (Z_Num8_DeZoom2_STD-MALT_Tile_0_0.tif et Z_Num8_DeZoom2_STD-MALT_Tile_1_0.tif).
    S'il y a plusieurs fichiers, alors il ne faut renvoyer que les fichiers avec Tile.
    """
    level_tiles = [os.path.join(path, i) for i in os.listdir(path) if f"Z_Num{level}_DeZoom" in i and "Tile" in i and i[-4:]==".tif"]
    if len(level_tiles)==0:
        level_tiles = [os.path.join(path, i) for i in os.listdir(path) if f"Z_Num{level}_DeZoom" in i and i[-4:]==".tif"]
    if len(level_tiles)==0:
        raise ValueError(f"Il n'y a pas de fichier Z_Num{level}_DeZoomX_STD-MALT.tif")
    return level_tiles


def get_correlation(level):
    prefixe = f"Correl_STD-MALT_Num_{level}"
    suffixe = ".tif"
    level_tiles = [os.path.join(input_Malt, i) for i in os.listdir(input_Malt) if i[:len(prefixe)]==prefixe and i[-len(suffixe):]==suffixe]
    if len(level_tiles)==0:
        prefixe = f"Correl_STD-MALT_Num_{level}_Tile"
        level_tiles = [os.path.join(input_Malt, i) for i in os.listdir(input_Malt) if i[:len(prefixe)]==prefixe and i[-len(suffixe):]==suffixe]
    if len(level_tiles)==0:
        raise ValueError(f"Il n'y a pas de fichier Correl_STD-MALT_Num_{level}.tif dans {input_Malt}")
    return level_tiles

        
def compute_mns(input_Malt):

    # On récupère le niveau le plus élevé : 8 en général, 9 sur les très gros chantiers
    if os.path.isfile(os.path.join(input_Malt, "Z_Num9_DeZoom2_STD-MALT.tif")):
        first_level = 9
    else:
        first_level = 8

    # On récupère toutes les tuiles du niveau le plus précis
    higher_level_tiles = get_level(input_Malt, first_level)
    # On construit un vrt sur les tuiles de niveau le plus précis
    if len(higher_level_tiles) > 1:
        os.system(f"gdalbuildvrt {input_Malt}/Z_Num{first_level}.vrt {input_Malt}/Z_Num{first_level}*Tile*tif")
    else:
        os.system(f"gdalbuildvrt {input_Malt}/Z_Num{first_level}.vrt {input_Malt}/Z_Num{first_level}_DeZoom*_STD-MALT.tif")
    # On parcourt chaque tuile de niveau le plus précis
    for higher_level_filename in higher_level_tiles:
        higher_level = LevelMNS(higher_level_filename, first_level)
        l, c = higher_level.get_size()
        higher_level.resize(l, c)

        mns = higher_level.mns
        correlation = higher_level.correlation
        correlation = correlation.astype(np.uint8)
        indicateur = np.ones(mns.shape)*first_level
        indicateur = indicateur.astype(np.uint8)
        transform = higher_level.transform
        bounds = higher_level.bounds
        # On parcourt tous les niveaux de MNS (sauf celui juste en dessous car il a la même carte de corrélation que le niveau le plus élevé)
        for level in range(first_level-2, 0, -1):
            levels_filename = get_level(input_Malt, level)

            dezoom = int(levels_filename[0].split("_")[2].replace("DeZoom", ""))
            
            # S'il y a plusieurs tuiles, on construit un vrt
            # Ainsi, quelque soit le niveau de la pyramide, on n'a plus qu'un seul fichier à traiter
            if len(levels_filename)>1:
                os.system(f"gdalbuildvrt {input_Malt}/Z_Num{level}.vrt {input_Malt}/Z_Num{level}*Tile*tif")
                levels_filename = [f"{input_Malt}/Z_Num{level}.vrt"]

            level_filename = levels_filename[0]
            level = LevelMNS(level_filename, first_level, bounds_required=bounds, dezoom=dezoom)
            # On redécoupe le mns et la carte de corrélation pour qu'elle ait la même taille que celui de la couche 8
            level.resize(l, c)
            # On conserve les informations précédentes que pour les endroits où la corrélation 
            # est différente de 1 (1 faible corrélation, 255 très forte corrélation)

            mns = np.where(correlation>1, mns, level.mns)
            indicateur = np.where(correlation>1, indicateur, level.level)
            correlation = np.where(correlation>1, correlation, level.correlation)

        indicateur = np.where(correlation>1, indicateur, 0)

        if len(higher_level_tiles) > 1:
            mns_name = "MNS_pyramide_"+("_".join(higher_level_filename.split("_")[4:]))
        else:
            mns_name = "MNS_pyramide.tif"
        save_image(mns, os.path.join(input_Malt, mns_name), transform, rasterio.float32)
        
        # On sauvegarde le tfw, nécessaire pour POMPEI.LINUX AssocierZ_fichierpts2D:multiMNS
        with open(os.path.join(input_Malt, mns_name.replace(".tif", ".tfw")), "w") as f:
            f.write(f"{transform.a}\n")
            f.write("0\n")
            f.write("0\n")
            f.write(f"{transform.e}\n")
            f.write(f"{transform.c}\n")
            f.write(f"{transform.f}\n")
        
        save_image(indicateur, os.path.join(input_Malt, mns_name.replace("MNS_pyramide", "indicateur")), transform, rasterio.uint8)
        save_image(correlation, os.path.join(input_Malt, mns_name.replace("MNS_pyramide", "correlation")), transform, rasterio.uint8)
    


input_Malt = args.input_Malt 
compute_mns(input_Malt)