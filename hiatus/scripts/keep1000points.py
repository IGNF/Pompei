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

import argparse
import random

parser = argparse.ArgumentParser(description="On conserve seulement 1000 points d'appuis aléatoirement, sinon le Ransac qui suit est interminable")
parser.add_argument('--file', help="Fichier contenant les points d'appuis")
args = parser.parse_args()

with open(args.file, "r") as f:
    points = []
    for line in f:
        points.append(line)

random.shuffle(points)

with open(args.file, "w") as f:
    for i in range(min(1000, len(points))):
        f.write(points[i])
