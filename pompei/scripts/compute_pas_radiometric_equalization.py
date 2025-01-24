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

"""
Calcule le pas pour le calcul des paramètres de l'égalisation radiométrique.

Le pas est en mètres. Le risque, c'est que ce soit interminable pour des chantiers avec une résolution de l'ordre de 2 mètres, ou que même le calcul n'ait pas assez de points pour des chantiers à haute résolution.
"""

import os
from tools import getResolution, load_bbox
from math import sqrt

resolution = getResolution()
bbox = load_bbox("metadata")

points_max = 20000

H = bbox[3] - bbox[1]
W = bbox[2] - bbox[0]
pas_min = int(sqrt(H*W/(2*points_max))) # On contraint d'avoir au plus 50000 points
pas_ideal = int(resolution*100/0.5)  # le pas d'un chantier à 50 centimètres de résolution est de 100 mètres, puis on applique une proportionnalité

with open(os.path.join("metadata", "pas_egalisation_radiometrique.txt"), "w") as f:
    f.write(str(max(pas_min, pas_ideal)))