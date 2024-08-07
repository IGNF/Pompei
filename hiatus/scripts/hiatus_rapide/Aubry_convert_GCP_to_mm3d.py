import os
import rasterio
import rasterio.transform
import argparse
from lxml import etree


parser = argparse.ArgumentParser(description="Convertit les points d'appuis trouvés par Aubry dans le format MicMac")
parser.add_argument('--metadata', help="Dossier contenant les métadonnées")
args = parser.parse_args()

metadata = args.metadata


def read_result_ransac(path, mesures_2D, mesures_3D, image_name):
    mesures_2D_image = []
    with open(path, "r") as f:
        for line in f:
            name_point = "APP"+str(len(mesures_3D))
            line_splitted = line.split()
            point_ortho = {"name":name_point, "x":float(line_splitted[0]), "y":float(line_splitted[1])}
            point_histo = {"name":name_point, "x":float(line_splitted[2]), "y":float(line_splitted[3])}

            mesures_2D_image.append(point_histo)
            mesures_3D.append(point_ortho)
    
    mesures_2D[image_name] = mesures_2D_image
    return mesures_2D, mesures_3D


def read_gt_image(image_name):
    image_src = rasterio.open(os.path.join("appuis", image_name))
    return image_src.transform


def to_histo_image_system(mesures_2D):
    for image_name in list(mesures_2D.keys()):
        image_name_base = image_name.replace("OIS-Reech_", "").split(".")[0]
        image_rectifiee = image_name_base+"_rectifiee.tif"
        gt = read_gt_image(image_rectifiee)
        for mesure in mesures_2D[image_name]:
            row, column = rasterio.transform.rowcol(gt, mesure["x"], mesure["y"])
            mesure["row"] = row
            mesure["column"] = column
    return mesures_2D


def open_MNS(metadata):
    """
    Ouvre le MNS
    """
    image_src = rasterio.open(os.path.join(metadata, "mns", "MNS.vrt"))
    mns = image_src.read()
    gt_mns = image_src.transform
    return mns, gt_mns


def z_value_measures_3D(mns, gt_mns, mesures_3D):
    """
    Pour chaque point d'appui en géométrie terrain, récupère son altitude grâce au MNS
    """
    for mesure in mesures_3D:
        row, column = rasterio.transform.rowcol(gt_mns, mesure["x"], mesure["y"])
        mesure["z"] = mns[0, int(row), int(column)]
    return mesures_3D



def save_mesures_3D_mm3d(mesures_3D):
    """
    Sauvegarde les points d'appuis en géométrie terrain sous le format Micmac
    """
    root = etree.Element("Root")
    xml = etree.ElementTree(root)
                            
    dicoAppuisFlottant = etree.Element("DicoAppuisFlottant")
    root.append(dicoAppuisFlottant)

    for mesure in mesures_3D:
        oneAppuisDAF = etree.Element("OneAppuisDAF")
        dicoAppuisFlottant.append(oneAppuisDAF)

        pt = etree.Element("Pt")
        pt.text = "{} {} {}".format(mesure["x"], mesure["y"], mesure["z"])
        oneAppuisDAF.append(pt)

        namePt = etree.Element("NamePt")
        namePt.text = mesure["name"]
        oneAppuisDAF.append(namePt)

        incertitude = etree.Element("Incertitude")
        incertitude.text = "1 1 1"
        oneAppuisDAF.append(incertitude)

    xml.write("GCP.xml", xml_declaration=True, encoding="UTF-8")

def save_mesures_2D_mm3d(mesures_2D_mm3d):
    """
    Sauvegarde les points d'appuis en géométrie image sous le format Micmac
    """
    root = etree.Element("Root")
    xml = etree.ElementTree(root)
                            
    setOfMesureAppuisFlottants = etree.Element("SetOfMesureAppuisFlottants")
    root.append(setOfMesureAppuisFlottants)

    for image in list(mesures_2D_mm3d.keys()):
        mesureAppuiFlottant1Im = etree.Element("MesureAppuiFlottant1Im")
        setOfMesureAppuisFlottants.append(mesureAppuiFlottant1Im)

        nameIm = etree.Element("NameIm")
        nameIm.text = image+".tif"
        mesureAppuiFlottant1Im.append(nameIm)

        mesures_image = mesures_2D_mm3d[image]

        for mesure in mesures_image:
            oneMesureAF1I = etree.Element("OneMesureAF1I")
            mesureAppuiFlottant1Im.append(oneMesureAF1I)

            namePt = etree.Element("NamePt")
            namePt.text = mesure["name"]
            oneMesureAF1I.append(namePt)
            
            ptIm = etree.Element("PtIm")
            ptIm.text = "{} {}".format(mesure["column"], mesure["row"])
            oneMesureAF1I.append(ptIm)

    xml.write("GCP-S2D.xml", xml_declaration=True, encoding="UTF-8")

def save_nb_GCP_per_image(mesures_2D):
    """
    Sauvegarde le nombre de points d'appuis pour chaque image
    """
    with open(os.path.join("reports", "nb_GCP_per_image.txt"), "w") as f:
        for image_name in sorted(list(mesures_2D.keys())):
            f.write("{} : {}\n".format(image_name, len(mesures_2D[image_name])))


# On récupère le MNS
mns, gt_mns = open_MNS(metadata)
mesures_2D = {}
mesures_3D = []

# On parcourt tous les fichiers points d'appuis 
result_ransac_files = [i for i in os.listdir(os.path.join("appuis", "dallage")) if i[-7:]==".ransac"]
for result_ransac_file in result_ransac_files:
    image_name = result_ransac_file.replace(".ransac", "")
    mesures_2D, mesures_3D = read_result_ransac(os.path.join("appuis", "dallage", result_ransac_file), mesures_2D, mesures_3D, image_name)
# On convertit les coordonnées historiques en coordonnées image
mesures_2D = to_histo_image_system(mesures_2D)
# On récupère l'altitude des points d'appuis trouvés sur l'ortho de référence
mesures_3D = z_value_measures_3D(mns, gt_mns, mesures_3D)

# On sauvegarde les mesures
save_mesures_3D_mm3d(mesures_3D)
save_mesures_2D_mm3d(mesures_2D)

# On sauvegarde le nombre de GCPs par image pour contrôle
save_nb_GCP_per_image(mesures_2D)