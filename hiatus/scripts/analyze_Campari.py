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
import os
from lxml import etree

parser = argparse.ArgumentParser(description="Analyse du rapport de Campari pour vérifier qu'il n'y a pas de problèmes lors du calcul de l'orientation absolue")

parser.add_argument('--input_report', help='Rapport Campari')
args = parser.parse_args()



def find_problem(chemin_rapport):
    line_residual = ""
    line_worst = ""   

    with open(chemin_rapport, "r") as f:
        for line in f:
            if "Residual" in line:
                line_residual = line
            if "Worst" in line:
                line_worst = line

    print(line_residual)
    print(line_worst)


    with open(os.path.join("reports", "rapport_complet.txt"), 'a') as f:
        f.write("Analyse de Campari\n")
        f.write(line_residual)
        f.write(line_worst)
        f.write("\n\n\n")


if __name__ == "__main__":

    print("")
    print("Analyse du rapport Campari")

    find_problem(args.input_report)
    print("")


    