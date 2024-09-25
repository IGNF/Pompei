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
import rasterio
from lxml import etree
import numpy as np
import argparse
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

    def __init__(self, image_path) -> None:
        self.image_path = image_path
        self.level = int(os.path.basename(image_path)[5])
        self.dezoom = self.getDezoom()
        self.origineAlti, self.resolutionAlti = self.read_xml()
        self.mns, self.transform = self.compute_mns()
        self.correlation = self.open_correlation()

    def getDezoom(self):
        """
        Renvoie le niveau de dezoom de la couche
        """
        filename = os.path.basename(self.image_path)
        dezoom = int(int(filename.split("_")[2].replace("DeZoom", ""))/2)
        return dezoom
        
    def open_mns(self):
        """
        Ouvre le MNS calculé par Micmac
        """
        input_dst = rasterio.open(self.image_path)
        return input_dst.read(), input_dst.transform
    
    def compute_mns(self):
        """
        Met en forme le MNS calculé par Micmac
        """
        #Ouverture du MNS
        mns, transform = self.open_mns()
        # Calcul le MNS à partir des métadonnées Micmac
        mns = self.compute_elevation(mns)
        mns = self.resample_image(mns)
        return mns, transform

    def read_xml(self):
        xml_path = f"{self.image_path[:-4]}.xml"
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
    
    def open_correlation(self):
        """
        Ouvre la carte de corrélation
        """
        if self.level != 8:
            filename = f"Correl_STD-MALT_Num_{self.level}.tif"
        else:
            filename = "Correl_STD-MALT_Num_7.tif"
        input_dst = rasterio.open(os.path.join(input_Malt, filename))
        correlation = input_dst.read()
        correlation = self.resample_image(correlation)
        return correlation
        
    def resize(self, l, c):
        """
        Redécoupe le mns et la carte de corrélation pour qu'elle ait la taille définie par c et l
        """
        mns = np.ones((1, l, c))
        correlation = np.ones((1, l, c))
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
    with rasterio.open(
        path, "w",
        driver = "GTiff",
        transform = transform,
        dtype = encoding,
        count = image.shape[0],
        width = image.shape[2],
        height = image.shape[1]) as dst:
        dst.write(image)

        
def compute_mns(input_Malt):

    # On ouvre le MNS du niveau 8 (le plus fin)
    level8 = LevelMNS(os.path.join(input_Malt, "Z_Num8_DeZoom2_STD-MALT.tif"))
    l, c = level8.get_size()
    mns = level8.mns
    correlation = level8.correlation
    indicateur = np.ones(mns.shape)*8
    transform = level8.transform

    # On parcourt tous les niveaux de MNS (sauf le 7 car il a la même carte de corrélation que le 8)
    Z_Nums = [i for i in os.listdir(input_Malt) if "Z_Num" in i and i[-4:]==".tif" and "Z_Num8" not in i and "Z_Num7" not in i]
    for z_num in reversed(sorted(Z_Nums)):
        # On prépare mns et carte de corrélation
        level = LevelMNS(os.path.join(input_Malt, z_num))
        # On redécoupe le mns et la carte de corrélation pour qu'elle ait la même taille que celui de la couche 8
        level.resize(l, c)
        # On conserve les informations précédentes que pour les endroits où la corrélation 
        # est différente de 1 (1 faible corrélation, 255 très forte corrélation)
        mns = np.where(correlation!=1, mns, level.mns)
        indicateur = np.where(correlation!=1, indicateur, level.level)
        correlation = np.where(correlation!=1, correlation, level.correlation)

    indicateur = np.where(correlation!=1, indicateur, 0)
    save_image(mns, os.path.join(input_Malt, "MNS_Final_Num8_DeZoom2_STD-MALT.tif"), transform, rasterio.float32)
    save_image(indicateur, os.path.join(input_Malt, "indicateur.tif"), transform, rasterio.uint8)
    save_image(correlation, os.path.join(input_Malt, "correlation.tif"), transform, rasterio.uint8)
    


input_Malt = args.input_Malt 
compute_mns(input_Malt)