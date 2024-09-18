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

logger = logging.getLogger("root")

parser = argparse.ArgumentParser(description="Analyse du rapport de Tapas pour vérifier qu'il n'y a pas de problèmes lors du calcul de l'orientation relative. Si des images posent problème, alors on les supprime et on relance Tapas")

parser.add_argument('--input_report', help='Rapport Tapas')
parser.add_argument('--scripts_dir', help='Rapport Tapas')
args = parser.parse_args()



def remove_images_without_homol(dictionnaire):
    images = [i for i in os.listdir() if i[-4:]==".tif" and i[:9]=="OIS-Reech"]
    for image in images:
        if image not in dictionnaire.keys():
            logger.warning("On retire l'image {} car elle n'a plus de points de liaisons avec des images encore existantes".format(image))
            shutil.move(image, "Poubelle_Tapas")



def find_problem(chemin_rapport, chemin_scripts):
    dictionnaire = {}  

    logger.info("Analyse du rapport Tapas")

    with open(chemin_rapport, "r") as f:
        fatal_error = False
        for line in f:
            if "RES" in line and "ER2" in line:
                line_replaced = line.replace("]", "[")
                line_splitted = line_replaced.split("[")
                nom_image = line_splitted[1]

                line_splitted_space = line.split()
                valeur = line_splitted_space[4]
                if valeur == "-nan":
                    valeur = 0

                dictionnaire[nom_image] = valeur
            if "NON INIT" in line:
                line_splitted = line.split(" ")
                nom_image = line_splitted[6][:-1]
                dictionnaire[nom_image] = "-nan"
            
            if "Residual" in line:
                line_residual = line
            if "Worst" in line:
                line_worst = line
            if "Sorry, the following FATAL ERROR happened" in line:
                fatal_error = True
            if "Warn tape enter to continue" in line:
                fatal_error = True

    
    Recommencer_Tapas = False
    compte_images_retirees = 0
    image_min = None
    val_min = 100.00
    for image in dictionnaire:
        if float(dictionnaire[image]) < val_min:
            val_min = float(dictionnaire[image])
            image_min = image
    
    if fatal_error or val_min <= 60.0:
        Recommencer_Tapas = True
        logger.warning("L'image {} est retirée du jeu de données car Tapas n'est pas parvenu à déterminer son orientation relative".format(image_min))
        if not os.path.exists("Poubelle_Tapas"):
            os.mkdir("Poubelle_Tapas")
        shutil.move(image_min, "Poubelle_Tapas")
        compte_images_retirees += 1

    with open(os.path.join("reports", "rapport_complet.txt"), 'a') as f:
        f.write("Analyse de Tapas\n")
        f.write(line_residual)
        f.write(line_worst)
        f.write("{} images ont été retirées".format(compte_images_retirees))
        f.write("\n\n\n")

    remove_images_without_homol(dictionnaire)
    
    if Recommencer_Tapas:        
        os.system("rm -r Ori-Rel")
        os.system("rm -r reports/report_Tapas.txt")
        os.system("mm3d Martini \"OIS-Reech_.*tif\" OriCalib=CalibNum >> logfile")
        os.system("mm3d Tapas FraserBasic \"OIS-Reech_.*tif\" InOri=MartiniCalibNum InCal=CalibNum Out=Rel @ExitOnWarn | tee reports/report_Tapas.txt >> logfile")
        os.system("python {}/analyze_Tapas.py --input_report reports/report_Tapas.txt --scripts_dir {}".format(chemin_scripts, chemin_scripts))

    


if __name__ == "__main__":

    find_problem(args.input_report, args.scripts_dir)


    