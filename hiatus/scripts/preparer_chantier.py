import argparse
from lxml import etree
import os

parser = argparse.ArgumentParser(description="Préparation des différents fichiers pour le chantier")
parser.add_argument('--scripts', help='Répertoire du chantier')
parser.add_argument('--TA', help='Fichier xml du chantier')
parser.add_argument('--nb_fiduciaux', help='Nombre de repères de fond de chambre')
parser.add_argument('--resolution_scannage', help='résolution du scannage de la photo argentique')
parser.add_argument('--presence_artefacts', help="Présence d'artefacts")
parser.add_argument('--cibles', help='Utiliser Yolo pour détecter les cibles')
parser.add_argument('--images_seuillees', help='faire la recherche de repères de fons de chambre sur les images seuillées')
args = parser.parse_args()

scripts_path = args.scripts
TA_path = args.TA
resolution_scannage = float(args.resolution_scannage)
nb_fiduciaux = int(args.nb_fiduciaux)
presence_artefacts = int(args.presence_artefacts)
cibles = int(args.cibles)
images_seuillees = int(args.images_seuillees)

class Sensor:

    def __init__(self) -> None:
        self.width = None
        self.height = None
        self.focale = None

    def setWidth(self, width):
        self.width = width

    def setHeight(self, height):
        self.height = height

    def setFocale(self, focale):
        self.focale = focale



def open_xml(TA_path):
    tree = etree.parse(TA_path)
    root = tree.getroot()
    return root


def checkSensor(root):
    sensors = root.findall(".//sensor")
    if len(sensors) >= 2:
        raise Exception("Attention, il y a {} caméras dans le chantier".format(len(sensors)))
    elif len(sensors)==0:
        raise Exception("Attention, il n'y a aucune caméra dans le chantier")

    else:
        sensor = Sensor()
        sensor_xml = sensors[0]
        rect = sensor_xml.find(".//rect")
        w = int(rect.find(".//w").text.strip())
        sensor.setWidth(w)
        h = int(rect.find(".//h").text.strip())
        sensor.setHeight(h)

        focal = sensor_xml.find(".//focal")
        f = int(float(focal.find(".//z").text.strip()))
        sensor.setFocale(f)

    return sensor

    
def createOriCalibNum(scripts_path, sensor:Sensor):
    Ori_CalibNum_dir = os.path.join("Ori-CalibNum")
    os.makedirs(Ori_CalibNum_dir, exist_ok=True)

    tree = etree.parse(os.path.join(scripts_path, "Autocal.xml"))
    root = tree.getroot()

    root.find(".//PP").text = "{} {}".format(sensor.width/2, sensor.height/2)
    root.find(".//F").text = "{}".format(sensor.focale / resolution_scannage)
    root.find(".//SzIm").text = "{} {}".format(sensor.width, sensor.height)
    root.find(".//CDist").text = "{} {}".format(sensor.width/2, sensor.height/2)

    AutoCal_Foc_path = os.path.join(Ori_CalibNum_dir, "AutoCal_Foc-{}_Cam-Argentique.xml".format(int(sensor.focale * 1000)))
    with open(AutoCal_Foc_path, "w") as f:
        f.write("<?xml version=\"1.0\" ?>\n")
        f.write(str(etree.tostring(root, encoding='unicode')))

    

def createLocalChantierDescripteur(scripts_path, sensor:Sensor):
    tree = etree.parse(os.path.join(scripts_path, "MicMac-LocalChantierDescripteur.xml"))
    root = tree.getroot()
    
    root.find(".//SzCaptMm").text = "{} {}".format(sensor.width, sensor.height)
    KeyedNamesAssociations = root.findall(".//KeyedNamesAssociations")[1]
    KeyedNamesAssociations.find(".//CalcName").text = "{}".format(int(sensor.focale))

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


def case_0_fiduciaux(cliches, presence_artefacts, sensor:Sensor):
    name_first_image = cliches[0].find("image").text.strip()
    base_name = name_first_image[:5]
    with open(os.path.join("correction_cliches.sh"), "w") as f:
        f.write("repertoire_scripts=$1 \n\n")
        f.write("#On copie les images  : on fait comme si les images initiales sont les images rééchantillonnées \n")
        f.write("for f in "+base_name+"*.tif; do cp ${f} OIS-Reech_${f}; done \n\n")
        f.write("#Mise à jour du fichier de calibration \n")
        f.write("python ${repertoire_scripts}/maj_calibNum.py --input_micmac_folder=./ >> logfile \n\n")
        f.write("#Saisie du masque pour supprimer les contours \n")
        f.write("echo \"Saisie du masque pour supprimer les contours\" \n")
        f.write("mm3d SaisieMasq OIS-Reech_{}.tif Name=filtre.tif Gama=2 >> logfile\n".format(name_first_image))
        if presence_artefacts:
            f.write("echo \"Saisie du masque pour supprimer les contours et les artefacts\"\n ")
            f.write("mm3d SaisieMasq OIS-Reech_{}.tif Name=filtre_artefacts.tif Gama=2 >> logfile\n".format(name_first_image))

    with open(os.path.join("tapioca.sh"), "w") as f:
        f.write("repertoire_scripts=$1 \n\n")
        f.write("#Conversion des orientations et positions des sommets de prise de vue contenue dans le fichier csv dans le format MicMac \n")
        f.write("echo \"OriConvert\" \n")
        f.write("mm3d OriConvert OriTxtInFile SommetsNav.csv Nav NameCple=CouplesTA.xml >> logfile \n\n")
        f.write("# Recherche des points homologues \n")
        f.write("echo \"Tapioca\" \n")
        f.write("mm3d Tapioca File CouplesTA.xml {} | tee rapports/rapport_Tapioca.txt >> logfile \n\n".format(int(max(sensor.width, sensor.height)/2)))
        f.write("python ${repertoire_scripts}/analyse_Tapioca.py --input_rapport=rapports/rapport_Tapioca.txt --output_rapport=rapports/resultat_analyse_Tapioca.txt \n\n")


def case_n_fiduciaux(cliches, presence_artefacts, sensor:Sensor, cibles, nb_fiduciaux, images_seuillees):
    name_first_image = cliches[0].find("image").text.strip()
    base_name = name_first_image[:5]
    with open(os.path.join("correction_cliches.sh"), "w") as f:
        f.write("repertoire_scripts=$1 \n\n")
        f.write("#Saisie des repères de fond de chambre sur une image \n")
        f.write("echo \"Saisie des repères de fonds de chambre\" \n")
        if cibles == 1:
            f.write("python ${repertoire_scripts}/YOLO_detect_reperes_fond_chambre.py --nb_points " + str(nb_fiduciaux) + " --scripts ${repertoire_scripts} \n\n")
        else:
            f.write("mm3d SaisieAppuisInit {}.tif NONE id_reperes.txt MeasuresIm-{}.tif.xml >> logfile\n\n".format(name_first_image, name_first_image))
            f.write("#Saisie d'un masque indiquant où les repères de fond de chambre peuvent se trouver \n")
            f.write("echo \"Saisie du masque où les repères du fond de chambre se trouvent\" \n")
            f.write("mm3d SaisieMasq {}.tif >> logfile \n\n".format(name_first_image))

            if images_seuillees:
                f.write("sh ${repertoire_scripts}/filtre_FFTKugelhupf.sh ${repertoire_scripts} \n")
            
            f.write("#Recherche des repères de fond de chambre \n")
            f.write("echo \"FFTKugelhupf\" \n")

            if images_seuillees:
                f.write("mm3d FFTKugelhupf filtre_FFTKugelHupf_{}.*tif MeasuresIm-{}.tif-S2D.xml Masq=Masq | tee rapports/rapport_FFTKugelhupf.txt >> logfile \n\n".format(base_name, name_first_image))
            else:
                f.write("mm3d FFTKugelhupf {}.*tif MeasuresIm-{}.tif-S2D.xml Masq=Masq | tee rapports/rapport_FFTKugelhupf.txt >> logfile \n\n".format(base_name, name_first_image))

            f.write("echo \"Analyse du rapport FFTKugelhupf\" \n")
            f.write("python ${repertoire_scripts}/analyse_FFTKugelhupf.py --input_rapport rapports/rapport_FFTKugelhupf.txt \n\n")
            f.write("#Suppression de fichiers de masques sinon ils sont traités comme faisant partie des images \n")
            f.write("rm {}_Masq.tif \n".format(name_first_image))
            f.write("rm {}_Masq.xml \n".format(name_first_image))
            f.write("rm MeasuresIm-{}.tif-S2D.xml \n".format(name_first_image))
            f.write("rm MeasuresIm-{}.tif-S3D.xml \n".format(name_first_image))

            if images_seuillees:
                f.write("rm filtre_FFTKugelHupf_*tif \n")
                f.write("#Modifie le dossier Ori-InterneScan pour faire comme si la recherche de points fiduciaux a été faite sur les images originales et non sur les images filtrées \n")
                f.write("python ${repertoire_scripts}/modify_FFTKugelhupf.py \n")
            else:
                f.write("rm Ori-InterneScan/MeasuresIm-{}_Masq.tif.xml \n".format(name_first_image))

        f.write("#Recherche des positions moyennes des repères de fond de chambre \n")
        f.write("echo \"Recherche des positions moyennes des repères de fonds de chambre\" \n")
        #f.write("python ${repertoire_scripts}/reperemoyen_resoscan.py --input_micmac_folder=./ --input_idreperesfile=id_reperes.txt >> logfile \n\n")
        f.write("python ${repertoire_scripts}/reperemoyen_resoscan.py >> logfile \n\n")
        f.write("#Rééchantillonnage des clichés \n")
        f.write("echo \"Rééchantillonnage des clichés\" \n")
        f.write("mm3d ReSampFid {}.*tif 1 | tee rapports/rapport_ReSampFid.txt >> logfile \n\n".format(base_name))
        f.write("#Analyse du rapport de ReSampFid \n")
        f.write("python ${repertoire_scripts}/analyse_ReSampFid.py --input_rapport rapports/rapport_ReSampFid.txt \n\n")
        f.write("#Mise à jour du fichier de calibration \n")
        f.write("python ${repertoire_scripts}/maj_calibNum.py --input_micmac_folder=./ >> logfile \n\n")
        f.write("#Saisie du masque pour supprimer les contours \n")
        f.write("echo \"Saisie du masque pour supprimer les contours\" \n ")
        f.write("mm3d SaisieMasq OIS-Reech_{}.tif Name=filtre.tif Gama=2 >> logfile\n".format(name_first_image))

        if presence_artefacts:
            f.write("echo \"Saisie du masque pour supprimer les contours et les artefacts\" \n ")
            f.write("mm3d SaisieMasq OIS-Reech_{}.tif Name=filtre_artefacts.tif Gama=2 >> logfile\n".format(name_first_image))

    with open("tapioca.sh", "w") as f:
        f.write("repertoire_scripts=$1 \n\n")
        f.write("#Conversion des orientations et positions des sommets de prise de vue contenue dans le fichier csv dans le format MicMac \n")
        f.write("echo \"OriConvert\" \n")
        f.write("mm3d OriConvert OriTxtInFile SommetsNav.csv Nav NameCple=CouplesTA.xml >> logfile \n\n")
        f.write("# Recherche des points homologues \n")
        f.write("echo \"Tapioca\" \n")
        f.write("mm3d Tapioca File CouplesTA.xml {} | tee rapports/rapport_Tapioca.txt >> logfile \n\n".format(int(max(sensor.width, sensor.height)/2)))
        f.write("python ${repertoire_scripts}/analyse_Tapioca.py --input_rapport=rapports/rapport_Tapioca.txt --output_rapport=rapports/resultat_analyse_Tapioca.txt \n\n")


    with open("id_reperes.txt", "w") as f:
        for i in range(1, nb_fiduciaux+1):
            f.write("{}\n".format(i))

root = open_xml(TA_path)
sensor = checkSensor(root)
createOriCalibNum(scripts_path, sensor)
createLocalChantierDescripteur(scripts_path, sensor)
cliches = createSommetsNav(root)

if nb_fiduciaux == 0:
    case_0_fiduciaux(cliches, presence_artefacts, sensor)

else:
    case_n_fiduciaux(cliches, presence_artefacts, sensor, cibles, nb_fiduciaux, images_seuillees)

