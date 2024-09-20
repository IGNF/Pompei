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
import shutil
import log # Chargement des configurations des logs
import logging


logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Analyse du rapport de Tapas ou de Campari. Pour Tapas, on vérifie qu'il n'y a pas de problèmes lors du calcul de l'orientation relative. Si des images posent problème, alors on les supprime et on relance Tapas.")
parser.add_argument('--input_report', help='Rapport Tapas ou Campari')
parser.add_argument('--scripts_dir', help='Répertoire des scripts', default=None)
args = parser.parse_args()



def remove_images_without_homol(dictionnaire):
    images = [i for i in os.listdir() if i[-4:]==".tif" and i[:9]=="OIS-Reech"]
    for image in images:
        if image not in dictionnaire.keys():
            logger.warning("On retire l'image {} car elle n'a plus de points de liaisons avec des images encore existantes".format(image))
            shutil.move(image, "Poubelle_Tapas")



def find_problem(chemin_rapport, chemin_scripts):
    dictionnaire = {}

    with open(chemin_rapport, "r") as f:
        fatal_error = False
        for line in f:
            if "RES" in line and "ER2" in line:
                # Si c'est une ligne avec les informations concernant les résidus d'une image
                # nom de l'image
                line_replaced = line.replace("]", "[")
                line_splitted = line_replaced.split("[")
                nom_image = line_splitted[1]

                # proportion de points de liaisons conservés
                line_splitted_space = line.split()
                proportion = line_splitted_space[4]
                if proportion == "-nan":
                    proportion = 0


                # Résidus
                residus = line_splitted_space[2]
                dictionnaire[nom_image] = {"residus":residus, "proportion":proportion}

            if "NON INIT" in line:
                line_splitted = line.split(" ")
                nom_image = line_splitted[6][:-1]
                dictionnaire[nom_image] = {"residus":0, "proportion":0}
            
            # Ligne avec les résidus moyens
            if "Residual =" in line:
                line_residual = line
            # Ligne avec les moins bons résultats 
            if "Worst" in line:
                line_worst = line
            
            # Erreurs diverses
            if "Sorry, the following FATAL ERROR happened" in line:
                logger.warning(f"{line}")
                fatal_error = True
            if "Warn tape enter to continue" in line:
                logger.warning(f"{line}")
                fatal_error = True

    if "Tapas" in os.path.basename(chemin_rapport):
        algo="Tapas"
    else:
        algo = "Campari"

    
    # On récupère l'image qui a la proportion de points de liaisons conservés la plus faible
    image_min = None
    val_min = 100.00
    for image in dictionnaire:
        logger.debug(f"Image : {image}, points de liaisons conservés : {dictionnaire[image]['proportion']}, résidus : {dictionnaire[image]['residus']}")
        if float(dictionnaire[image]["proportion"]) < val_min:
            val_min = float(dictionnaire[image]["proportion"])
            image_min = image
    
    logger.info(line_residual)
    logger.info(line_worst)

    # Si on est dans le premier calcul d'orientation relative
    if algo=="Tapas":
        recommencer_Tapas = False
        # Si le calcul n'a pas abouti ou que la proportion minimale de points de liaisons utilisés est inférieure à 60, on supprime la moins bonne image
        if fatal_error or val_min <= 60.0:
            recommencer_Tapas = True
            logger.warning("L'image {} est retirée du jeu de données car Tapas n'est pas parvenu à déterminer son orientation relative".format(image_min))
            if not os.path.exists("Poubelle_Tapas"):
                os.mkdir("Poubelle_Tapas")
            shutil.move(image_min, "Poubelle_Tapas")
        
        # Supprime les images qui ne sont pas apparues dans le rapport de Tapas car elle n'ont pas de points de liaisons avec les autres images
        remove_images_without_homol(dictionnaire)   
        
        # Si une image a été supprimée, alors on recommence le calcul (sauf si l'image n'apparaît pas dans le rapport Tapas et dans ce cas elle n'avait déjà pas été prise en compte dans le calcul)
        if recommencer_Tapas:
            logger.info("On recommence un calcul d'orientation relative avec Tapas")     
            os.system("rm -r Ori-Rel")
            os.system("rm -r reports/report_Tapas.txt")
            os.system("mm3d Martini \"OIS-Reech_.*tif\" OriCalib=CalibNum >> logfile")
            os.system("mm3d Tapas FraserBasic \"OIS-Reech_.*tif\" InOri=MartiniCalibNum InCal=CalibNum Out=Rel @ExitOnWarn | tee reports/report_Tapas.txt >> logfile")
            os.system("python {}/analyze_Tapas.py --input_report reports/report_Tapas.txt --scripts_dir {}".format(chemin_scripts, chemin_scripts))

    


if __name__ == "__main__":

    find_problem(args.input_report, args.scripts_dir)


    