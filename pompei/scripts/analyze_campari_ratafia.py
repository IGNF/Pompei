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
    if os.path.isdir(ori):
        xml_calib = [i for i in os.listdir(ori) if i[:7]=="AutoCal" and i[-4:]==".xml"]
        if len(xml_calib)==1:
            tree = etree.parse(os.path.join(ori, xml_calib[0]))
            root = tree.getroot()
            F_balise = root.find(".//F")
            return float(F_balise.text)
        logger.warning(f"{len(xml_calib)} fichiers de calibrations ont été trouvés dans {ori}")
    return None

foc_before = get_focale(input_ratafia_before)
foc_after = get_focale(input_ratafia_after)

if foc_before is None:
    logger.warning(f"La focale n'a pas été trouvée dans {input_ratafia_before}")
    sys.exit(1)


if foc_before < 0:
    logger.warning(f"La focale dans {input_ratafia_before} est négative : {foc_before}")
    sys.exit(1)
    
error = False
        
if foc_after is None:
    # cas probable d'un Distortion Inversion  by finite difference do not converge (probably ill-conditioned canvas) : aucun répertoire n'a été créé
    logger.warning(f"La focale n'a pas été trouvée dans {input_ratafia_after}")
    error = True

if foc_after is not None and foc_after < 0:
    logger.warning(f"La focale dans {input_ratafia_after} est négative : {foc_after}")
    error = True
    
# la focale n'est pas censée avoir trop bougé
if foc_after is not None:
    rapport = max(foc_before, foc_after)/min(foc_before, foc_after)
    if rapport > 1.3:
        logger.debug(f"foc_before : {foc_before}")
        logger.debug(f"foc_after : {foc_after}")
        logger.warning(f"Le rapport entre les deux focales est supérieur à 1.3 : {rapport}")
        error = True

# Si la focale a trop changé, alors on utilise l'orientation précédente
# L'aéro devrait pouvoir se débrouiller ensuite
if error:
    logger.warning("mm3d Campari OIS.*tif Abs-Ratafia Abs-Ratafia-AllFree AllFree=true ne s'est pas bien passé : on supprime cette étape")
    shutil.rmtree(input_ratafia_after)
    shutil.copytree(input_ratafia_before, input_ratafia_after)

