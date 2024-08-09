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
import shutil

parser = argparse.ArgumentParser(description="Suppression d'un point sur quatre")
parser.add_argument('--input_resultpifreproj', default='', help='Dossier MEC-Malt')
args = parser.parse_args()

shutil.copy(args.input_resultpifreproj, "resultpifreproj_save")

with open("resultpifreproj_save", "r") as f:
    with open(args.input_resultpifreproj, "w") as f2:
        compte = 0
        for line in f:
            if compte%4==0:
                f2.write(line)
            compte += 1

