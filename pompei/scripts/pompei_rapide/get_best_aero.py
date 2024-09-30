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

import shutil
import os



"""
Sur les chantiers un peu compliqués, il est possible de ne pas pouvoir réussir à faire toutes les aéros.

Chaque aéro étant en théorie un peu plus précise, on récupère pour la suite la dernière aéro calculée avec succès
"""



for i in range(8, -1, -1):
    ori_dir = "Ori-Aero_{}".format(i)
    if os.path.isdir(ori_dir):
        if os.path.exists("Ori-TerrainFinal_10_10_0.5_AllFree_Final/"):
            shutil.rmtree("Ori-TerrainFinal_10_10_0.5_AllFree_Final/")
        shutil.copytree(ori_dir, "Ori-TerrainFinal_10_10_0.5_AllFree_Final/")
        break