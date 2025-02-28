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
from lxml import etree
import os
import log # Chargement des configurations des logs
import logging
import json
from typing import List
from tools import Sensor, getSensors

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Préparation des différents fichiers pour le chantier")
parser.add_argument('--scripts', help='Répertoire du chantier')
parser.add_argument('--TA', help='Fichier TA du chantier')
parser.add_argument('--nb_fiducial_marks', help='Nombre de repères de fond de chambre')
parser.add_argument('--remove_artefacts', help="Présence d'artefacts")
parser.add_argument('--targets', help='Utiliser Yolo pour détecter les cibles')
parser.add_argument('--apply_threshold', help='faire la recherche de repères de fons de chambre sur les images seuillées')
args = parser.parse_args()

scripts_path = args.scripts
TA_path = args.TA
nb_fiducial_marks = int(args.nb_fiducial_marks)
remove_artefacts = int(args.remove_artefacts)
targets = int(args.targets)
apply_threshold = int(args.apply_threshold)


def get_resolution_scan():
    ta_basename = os.path.basename(TA_path)
    resol_scan = 0.021
    with open(os.path.join(scripts_path, "export_focales.json"), "r") as f:
        data = json.load(f)
        for chantier_dict in data:
            if chantier_dict["chantier"].replace(" ", "_") + ".xml" == ta_basename:
                resol_scan = float(chantier_dict["resol_scan"])
                break
    os.makedirs("metadata", exist_ok=True)
    with open(os.path.join("metadata", "resol.txt"), "w") as f:
        f.write(str(resol_scan))
    return resol_scan
    


def openXml(TA_path):
    tree = etree.parse(TA_path)
    root = tree.getroot()
    return root


def createOriCalibNum(scripts_path, sensors):
    Ori_CalibNum_dir = os.path.join("Ori-CalibNum")
    os.makedirs(Ori_CalibNum_dir, exist_ok=True)

    for sensor_dict in sensors:
        tree = etree.parse(os.path.join(scripts_path, "Autocal.xml"))
        root = tree.getroot()

        sensor:Sensor = sensor_dict["sensor"]
        identifiant = sensor_dict["identifiant"]

        root.find(".//PP").text = "{} {}".format(sensor.width/2, sensor.height/2)
        root.find(".//F").text = "{}".format(sensor.focale / get_resolution_scan())
        root.find(".//SzIm").text = "{} {}".format(sensor.width, sensor.height)
        root.find(".//CDist").text = "{} {}".format(sensor.width/2, sensor.height/2)

        AutoCal_Foc_path = os.path.join(Ori_CalibNum_dir, f"AutoCal_Foc-{int(sensor.focale * 1000)}_Cam-Argentique{identifiant}.xml")
        with open(AutoCal_Foc_path, "w") as f:
            f.write("<?xml version=\"1.0\" ?>\n")
            f.write(str(etree.tostring(root, encoding='unicode')))


def getKeyedNamesAssociations(root):
    CAM = None
    FOC = None
    MASK = None
    keyedNamesAssociations = root.findall(".//KeyedNamesAssociations")
    for keyed in keyedNamesAssociations:
        key = keyed.find(".//Key").text.strip()
        if key == "NKS-Assoc-STD-CAM":
            CAM = keyed
        if key == "NKS-Assoc-STD-FOC":
            FOC = keyed
        if key == "MyKeyCalculMasq":
            MASK = keyed
    for child in CAM.findall(".//Calcs"):
        CAM.remove(child)
    for child in FOC.findall(".//Calcs"):
        FOC.remove(child)
    for child in MASK.findall(".//Calcs"):
        MASK.remove(child)
    return CAM, FOC, MASK


def get_pattern(images):
    images_str = "|".join(images)
    return f'\"({images_str})\"'

def get_pattern_OIS(images):
    images_OIS = [f"OIS-Reech_{i}" for i in images]
    images_str = "|".join(images_OIS)
    return f"({images_str})"


def createLocalChantierDescripteur(scripts_path, sensors):
    tree = etree.parse(os.path.join(scripts_path, "MicMac-LocalChantierDescripteur.xml"))
    root = tree.getroot()

    locCamDataBase = root.find(".//LocCamDataBase")
    for child in list(locCamDataBase):
        locCamDataBase.remove(child)
    CAM, FOC, MASK = getKeyedNamesAssociations(root)

    for sensor_dict in sensors:
        sensor:Sensor = sensor_dict["sensor"]
        identifiant:int = sensor_dict["identifiant"]
        images:List[str] = sensor_dict["images"]

        # Ajout du nom de la caméra
        cameraEntry = etree.SubElement(locCamDataBase, "CameraEntry")
        name = etree.SubElement(cameraEntry, "Name")
        name.text = f"Argentique{identifiant}"
        szCaptMm = etree.SubElement(cameraEntry, "SzCaptMm")
        szCaptMm.text = f"{sensor.width} {sensor.height}"
        shortName = etree.SubElement(cameraEntry, "ShortName")
        shortName.text = "Arg"
        
        
        # Ajout de l'association nom_caméra - images 
        calcs = etree.SubElement(CAM, "Calcs")
        direct = etree.SubElement(calcs, "Direct")
        patternTransform = etree.SubElement(direct, "PatternTransform")
        patternTransform.text = get_pattern_OIS(images)
        calcName = etree.SubElement(direct, "CalcName")
        calcName.text = f"Argentique{identifiant}"

        # Ajout de l'association focale - images
        calcs = etree.SubElement(FOC, "Calcs")
        direct = etree.SubElement(calcs, "Direct")
        patternTransform = etree.SubElement(direct, "PatternTransform")
        patternTransform.text = get_pattern_OIS(images)
        calcName = etree.SubElement(direct, "CalcName")
        calcName.text = str(sensor.focale)

        # Ajout de l'association focale - images
        calcs = etree.SubElement(MASK, "Calcs")
        direct = etree.SubElement(calcs, "Direct")
        patternTransform = etree.SubElement(direct, "PatternTransform")
        patternTransform.text = get_pattern_OIS(images)
        calcName = etree.SubElement(direct, "CalcName")
        calcName.text = f"filtre{identifiant}.tif"



    Descripteur_path = os.path.join("MicMac-LocalChantierDescripteur.xml")
    with open(Descripteur_path, "w") as f:
        f.write(str(etree.tostring(root, encoding='unicode')))


def createSommetsNav(root):
    cliches = []
    with open(os.path.join("SommetsNav.csv"), "w") as f:
        f.write("#F=N X Y Z K W P\n")
        f.write("#\n")
        f.write("##image latitude longitude altitude Kappa Omega Phi\n")
        for cliche in root.findall(".//cliche"):
            image_path = os.path.join("{}.tif".format(cliche.find("image").text.strip()))
            if os.path.exists(image_path):
                cliches.append(cliche)
                image_name = "OIS-Reech_{}.tif".format(cliche.find("image").text.strip())
                model = cliche.find(".//model")
                x = model.find(".//x").text
                y = model.find(".//y").text
                z = model.find(".//z").text
                f.write("{} {} {} {} 0 0 0\n".format(image_name, x, y, z))
    return cliches


def case_0_fiduciaux(cliches, remove_artefacts):
    name_first_image = cliches[0].find("image").text.strip()
    base_name = name_first_image[:5]
    with open(os.path.join("correct_geometrically_images.sh"), "w") as f:
        f.write("set -e\n")
        f.write("scripts_dir=$1 \n\n")
        f.write("#On copie les images  : on fait comme si les images initiales sont les images rééchantillonnées \n")
        f.write("for f in "+base_name+"*.tif; do cp ${f} OIS-Reech_${f}; done \n\n")
        f.write("#Mise à jour du fichier de calibration \n")
        f.write("python ${scripts_dir}/maj_calibNum.py --input_micmac_folder=./ >> logfile \n\n")
        f.write("#Saisie du masque pour supprimer les contours \n")
        f.write("echo \"Saisie du masque pour supprimer les contours\" \n")
        f.write("mm3d SaisieMasq OIS-Reech_{}.tif Name=filtre.tif Gama=2 >> logfile\n".format(name_first_image))
        if remove_artefacts:
            f.write("echo \"Saisie du masque pour supprimer les contours et les artefacts\"\n ")
            f.write("mm3d SaisieMasq OIS-Reech_{}.tif Name=filtre_artefacts.tif Gama=2 >> logfile\n".format(name_first_image))
        f.write(f"rm -rf {base_name}*.tif\n")

    with open(os.path.join("find_tie_points.sh"), "w") as f:
        f.write("set -e\n")
        f.write("scripts_dir=$1 \n\n")
        f.write("#Conversion des orientations et positions des sommets de prise de vue contenue dans le fichier csv dans le format MicMac \n")
        f.write("echo \"OriConvert\" \n")
        f.write("mm3d OriConvert OriTxtInFile SommetsNav.csv Nav NameCple=CouplesTA.xml >> logfile \n\n")
        f.write("# Recherche des points homologues \n")
        f.write("echo \"Tapioca\" \n")
        f.write("mm3d Tapioca File CouplesTA.xml 5000 | tee reports/rapport_Tapioca.txt >> logfile \n\n")
        f.write("python ${scripts_dir}/analyze_Tapioca.py --input_report=reports/rapport_Tapioca.txt --output_rapport=reports/resultat_analyse_Tapioca.txt \n\n")


def case_n_fiduciaux(remove_artefacts, sensors, targets, nb_fiducial_marks, apply_threshold, TA_path):
    with open(os.path.join("correct_geometrically_images.sh"), "w") as f:
        f.write("set -e\n")
        f.write("scripts_dir=$1 \n\n")
        f.write("#Saisie des repères de fond de chambre sur une image \n")
        f.write("echo \"Saisie des repères de fonds de chambre\" \n")
        if targets == 1:
            f.write("python ${scripts_dir}/detect_fiducial_marks_YOLO.py --nb_points " + str(nb_fiducial_marks) + " --scripts ${scripts_dir} " + f" --ta {TA_path} \n\n")
        else:
            for sensor_dict in sensors:
                identifiant = sensor_dict["identifiant"]
                images = sensor_dict["images"]
                name_first_image = images[0][:-4]
                base_name = name_first_image[:5]
                f.write("python ${scripts_dir}/select_points.py --image_name " + name_first_image + f".tif --output_file MeasuresIm-{name_first_image}.tif-S2D.xml --flag {False} --nb_fiducial_marks {nb_fiducial_marks} \n\n")
                f.write("#Saisie d'un masque indiquant où les repères de fond de chambre peuvent se trouver \n")
                f.write("echo \"Saisie du masque où les repères du fond de chambre se trouvent\" \n")
                f.write("python ${scripts_dir}/saisie_masq.py --image " + f"{name_first_image}.tif --xml_file MeasuresIm-{name_first_image}.tif-S2D.xml --output_mask {name_first_image}_Masq.tif \n\n")

                if apply_threshold:
                    f.write("python ${scripts_dir}/filtre_FFTKugelhupf.py "+ f"--identifiant {identifiant} --ta {TA_path} \n")
                
                f.write("#Recherche des repères de fond de chambre \n")
                f.write("echo \"FFTKugelhupf\" \n")

                if apply_threshold:
                    f.write("mm3d FFTKugelhupf filtre_FFTKugelHupf_{}.*tif MeasuresIm-{}.tif-S2D.xml Masq=Masq | tee reports/rapport_FFTKugelhupf.txt >> logfile \n\n".format(base_name, name_first_image))
                else:
                    f.write("mm3d FFTKugelhupf {} MeasuresIm-{}.tif-S2D.xml Masq=Masq | tee reports/rapport_FFTKugelhupf.txt >> logfile \n\n".format(get_pattern(images), name_first_image))

                f.write("echo \"Analyse du rapport FFTKugelhupf\" \n")
                f.write("python ${scripts_dir}/analyze_FFTKugelhupf.py --input_report reports/rapport_FFTKugelhupf.txt --out_xml MeasuresIm-"+ name_first_image +".tif-S2D.xml --dir ${scripts_dir} \n\n")
                f.write("#Suppression de fichiers de masques sinon ils sont traités comme faisant partie des images \n")
                f.write("rm {}_Masq.tif \n".format(name_first_image))
                f.write("rm MeasuresIm-{}.tif-S2D.xml \n".format(name_first_image))

                if apply_threshold:
                    f.write("rm filtre_FFTKugelHupf_*tif \n")
                    f.write("#Modifie le dossier Ori-InterneScan pour faire comme si la recherche de points fiduciaux a été faite sur les images originales et non sur les images filtrées \n")
                    f.write("python ${scripts_dir}/modify_FFTKugelhupf.py \n")

        f.write("#Recherche des positions moyennes des repères de fond de chambre \n")
        for sensor_dict in sensors:
            identifiant = sensor_dict["identifiant"]
            images = sensor_dict["images"]
            name_first_image = images[0][:-4]
            f.write("echo \"Recherche des positions moyennes des repères de fonds de chambre\" \n")
            f.write("python ${scripts_dir}/compute_mean_fiducial_marks.py " + f"--identifiant {identifiant} --ta {TA_path} >> logfile \n\n")
            f.write("#Rééchantillonnage des clichés \n")
            f.write("echo \"Rééchantillonnage des clichés\" \n")
            f.write(f"mm3d ReSampFid {get_pattern(images)} 1 | tee reports/rapport_ReSampFid.txt >> logfile \n\n")
            f.write("#Analyse du rapport de ReSampFid \n")
            f.write("python ${scripts_dir}/analyze_ReSampFid.py --input_report reports/rapport_ReSampFid.txt \n\n")
            f.write("#Mise à jour du fichier de calibration \n")
            f.write("python ${scripts_dir}/maj_calibNum.py "+ f"--identifiant {identifiant} --ta {TA_path} >> logfile \n\n")
            f.write("#Saisie du masque pour supprimer les contours \n")
            f.write("echo \"Saisie du masque pour supprimer les contours\" \n")
            f.write("mm3d SaisieMasq OIS-Reech_{}.tif Name=filtre{}.tif Gama=2 >> logfile\n".format(name_first_image, identifiant))

        if remove_artefacts:
            f.write("echo \"Saisie du masque pour supprimer les contours et les artefacts\" \n ")
            f.write("mm3d SaisieMasq OIS-Reech_{}.tif Name=filtre_artefacts.tif Gama=2 >> logfile\n".format(name_first_image))
        images = sensors[0]["images"]
        name_first_image = images[0][:-4]
        base_name = name_first_image[:5]
        f.write(f"rm -rf {base_name}*.tif\n")

    with open("find_tie_points.sh", "w") as f:
        f.write("set -e\n")
        f.write("scripts_dir=$1 \n\n")
        f.write("#Conversion des orientations et positions des sommets de prise de vue contenue dans le fichier csv dans le format MicMac \n")
        f.write("echo \"OriConvert\" \n")
        f.write("mm3d OriConvert OriTxtInFile SommetsNav.csv Nav NameCple=CouplesTA.xml >> logfile \n\n")
        f.write("# Recherche des points homologues \n")
        f.write("echo \"Tapioca\" \n")
        f.write("mm3d Tapioca File CouplesTA.xml 5000 5000 | tee reports/rapport_Tapioca.txt >> logfile \n\n")
        f.write("python ${scripts_dir}/analyze_Tapioca.py --input_report=reports/rapport_Tapioca.txt --output_rapport=reports/resultat_analyse_Tapioca.txt \n\n")


    with open("id_reperes.txt", "w") as f:
        for i in range(1, nb_fiducial_marks+1):
            f.write("{}\n".format(i))

root = openXml(TA_path)
sensors = getSensors(root)
logger.info(f"Il y a {len(sensors)} caméras dans le chantier")
createOriCalibNum(scripts_path, sensors)
createLocalChantierDescripteur(scripts_path, sensors)
cliches = createSommetsNav(root)

if nb_fiducial_marks == 0:
    case_0_fiduciaux(cliches, remove_artefacts)

else:
    case_n_fiduciaux(remove_artefacts, sensors, targets, nb_fiducial_marks, apply_threshold, TA_path)
