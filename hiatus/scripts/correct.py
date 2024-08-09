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


parser = argparse.ArgumentParser(description="Correction du fichier coef_reetal_walis.txt")
parser.add_argument('--chemin', help="Répertoire du chantier")
args = parser.parse_args()



x0_float = None
x1_float = None
with open(args.chemin, "r") as f:
    for line in f:
        line_splitted = line.split()
        if len(line) ==2:
            x0 = line_splitted[0]
            x1 = line_splitted[1]
            try:
                x0_float = float(x0)
                x1_float = float(x1)
                break
            except:
                pass

if x0_float is not None and x1_float is not None:
    with open(args.chemin, "w") as f:
        f.write("{} {}".format(x0_float, x1_float))