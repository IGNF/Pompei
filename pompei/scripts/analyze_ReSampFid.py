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

import argparse
import os
import log # Chargement des configurations des logs
import logging

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Analyse du rapport de ReSampFid pour vérifier qu'il n'y a pas de problèmes lors du rééchantillonnage des images")

parser.add_argument('--input_report', help='Rapport ReSampFid')
args = parser.parse_args()



def find_problem(chemin_rapport):

    with open(chemin_rapport, "r") as f:
        residu_max = 0
        image_residu_max = ""
        for line in f:
            if "RESIDU" in line:
                line_splitted = line.split()
                residu = float(line_splitted[3])
                if residu > residu_max:
                    residu_max = residu
                    image_residu_max = line_splitted[1]
    logger.info("Le résidu le plus élevé est celui de l'image {} : {}".format(image_residu_max, residu_max))

if __name__ == "__main__":

    find_problem(args.input_report)


    