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
from lxml import etree
import sys
import shutil

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Analyse du rapport de Campari FocFree=true après Ratafia. Le risque est que la focale change beaucoup trop")

parser.add_argument('--input_ratafia_before', help='Orientation avant mm3d Campari OIS.*tif Abs-Ratafia Abs-Ratafia-AllFree AllFree=true ')
parser.add_argument('--input_ratafia_after', help='Orientation après mm3d Campari OIS.*tif Abs-Ratafia Abs-Ratafia-AllFree AllFree=true ')
args = parser.parse_args()

input_ratafia_before = args.input_ratafia_before
input_ratafia_after = args.input_ratafia_after


def get_focale(ori):
    dict_foc = {}
    if os.path.isdir(ori):
        
        xml_calib_files = [i for i in os.listdir(ori) if i[:7]=="AutoCal" and i[-4:]==".xml"]
        for xml_calib_file in xml_calib_files:
            tree = etree.parse(os.path.join(ori, xml_calib_file))
            root = tree.getroot()
            F_balise = root.find(".//F")
            focale = float(F_balise.text)
            dict_foc[xml_calib_file] = focale
    return dict_foc

foc_before = get_focale(input_ratafia_before)
foc_after = get_focale(input_ratafia_after)

if len(foc_before)==0:
    logger.warning(f"Aucune focale n'a pas été trouvée dans {input_ratafia_before}")
    sys.exit(1)


error = False
for file in foc_before.keys():
    
    focale_before = foc_before[file]

    if focale_before < 0:
        logger.error(f"La focale dans {input_ratafia_before} est négative : {focale_before}")
        sys.exit(1)
    focale_after = None
    if file not in list(foc_after.keys()):
        # cas probable d'un Distortion Inversion  by finite difference do not converge (probably ill-conditioned canvas) : aucun répertoire n'a été créé
        logger.warning(f"La focale n'a pas été trouvée dans {input_ratafia_after}")
        error = True
    else:
        focale_after = foc_after[file]        

    if focale_after is not None and focale_after < 0:
        logger.warning(f"La focale dans {input_ratafia_after} est négative : {focale_after}")
        error = True
        
    # la focale n'est pas censée avoir trop bougé
    if focale_after is not None:
        rapport = max(focale_before, focale_after)/min(focale_before, focale_after)
        if rapport > 1.3:
            logger.debug(f"focale_before : {focale_before}")
            logger.debug(f"focale_after : {focale_after}")
            logger.warning(f"Le rapport entre les deux focales est supérieur à 1.3 : {rapport}")
            error = True

# Si la focale a trop changé, alors on utilise l'orientation précédente
# L'aéro devrait pouvoir se débrouiller ensuite
if error:
    logger.warning("mm3d Campari OIS.*tif Abs-Ratafia Abs-Ratafia-AllFree AllFree=true ne s'est pas bien passé : on supprime cette étape")
    if os.path.isdir(input_ratafia_after):
        shutil.rmtree(input_ratafia_after)
    shutil.copytree(input_ratafia_before, input_ratafia_after)

