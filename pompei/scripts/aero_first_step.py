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
from math import sqrt
import os
import log # Chargement des configurations des logs
import logging
import shutil

logger = logging.getLogger()


parser = argparse.ArgumentParser(description="Suppression des points d'appuis les moins bons")
parser.add_argument('--scripts', help="Répertoire contenant les scripts")
parser.add_argument('--facteur', help="Facteur déterminant les points d'appuis faux à supprimer")
args = parser.parse_args()

scripts_dir = args.scripts
facteur = args.facteur

def analyze_result(path):
    echec = False
    with open(path, "r") as f:
        for line in f:
            if "Warn tape enter to continue" in line:
                echec = True
            if "Sorry, the following FATAL ERROR happened" in line:
                echec = True
    return echec






echec = True
compte = 0
while echec and compte < 5:
    compte += 1

    logger.debug("On essaye de lancer une aéro allFree")
    # On lance l'aéro allFree
    cmd = f"timeout 30s mm3d Campari OIS.*tif TerrainFinal_10_10_10 TerrainFinal_10_10_10_AllFree_temp GCP=[GCP_{compte}.xml,10,GCP-S2D_{compte}.xml,10]  SigmaTieP=10 AllFree=true RapTxt=ResidualsReport_allFree_temp_{compte}.txt| tee reports/rapport_CampariAero_temp_{compte}.txt >> logfile "
    os.system(cmd)

    # On regarde les résultats
    logger.debug(f"Analyse de reports/rapport_CampariAero_temp_{compte}.txt")
    echec = analyze_result(f"reports/rapport_CampariAero_temp_{compte}.txt")

    # Si les résultats ne sont pas corrects, alors on fait un campari temporaire avec suppression des points d'appuis
    if echec:
        
        logger.info("L'aéro AllFree a été un échec. On supprime les points d'appuis les plus faux")
        cmd = f"mm3d Campari OIS.*tif Abs-Ratafia-AllFree TerrainFinal_10_10_10 GCP=[GCP_{compte}.xml,10,GCP-S2D_{compte}.xml,10]  SigmaTieP=10 RapTxt=ResidualsReport_suppression_{compte}.txt| tee reports/rapport_CampariAero_suppression_{compte}.txt >> logfile"
        os.system(cmd)
        cmd = f"python {scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_suppression_{compte}.txt"
        os.system(cmd)
        cmd = f"python {scripts_dir}/delete_GCP.py --factor {facteur} --GCP GCP_{compte}.xml --S2D GCP-S2D_{compte}.xml --GCP_save GCP_{compte+1}.xml --S2D_save GCP-S2D_{compte+1}.xml --report_residuals ResidualsReport_suppression_{compte}.txt"
        os.system(cmd)
    else:
        shutil.copyfile(f"GCP_{compte}.xml", "GCP_AF_0.xml")
        shutil.copyfile(f"GCP-S2D_{compte}.xml", "GCP-S2D_AF_0.xml")