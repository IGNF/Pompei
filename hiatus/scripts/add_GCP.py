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
import fiona


parser = argparse.ArgumentParser(description="Ajoute des points d'appuis saisis à la main et présents dans des fichiers shapefile")

parser.add_argument('--appuis_BDOrtho_existants', help="Fichier contenant les points d'appuis déjà existants pour la BD Ortho")
parser.add_argument('--appuis_histo_existants', help="Fichier contenant les points d'appuis déjà existants pour l'ortho historique")
parser.add_argument('--appuis_BDOrtho_ajout', help="Fichier shapefile contenant les points d'appuis de la BD Ortho à ajouter")
parser.add_argument('--appuis_histo_ajout', help="Fichier shapefile contenant les points d'appuis de l'ortho historique à ajouter")
args = parser.parse_args()


def check_conditions(appuis_BDOrtho_ajout, appuis_histo_ajout):
    if not os.path.exists(appuis_BDOrtho_ajout):
        return False
    if not os.path.exists(appuis_histo_ajout):
        return False
    
    with fiona.open(appuis_BDOrtho_ajout, 'r') as appuis_BDOrtho: 
        with fiona.open(appuis_histo_ajout, 'r') as appuis_histo:
            if len(appuis_BDOrtho) != len(appuis_histo):
                return False
    return True


def add_points(appuis_ajout_path, appuis_existants_path):
    with fiona.open(appuis_ajout_path, 'r') as appuis_ajout: 
        with open(appuis_existants_path, 'a') as appuis_existants:
            for point_appui in appuis_ajout:
                coords = point_appui["geometry"]["coordinates"]
                appuis_existants.write("{} {}\n".format(coords[0], coords[1]))




if check_conditions(args.appuis_BDOrtho_ajout, args.appuis_histo_ajout):
    add_points(args.appuis_BDOrtho_ajout, args.appuis_BDOrtho_existants)
    add_points(args.appuis_histo_ajout, args.appuis_histo_existants)
