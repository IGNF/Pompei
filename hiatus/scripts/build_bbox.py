import os
from lxml import etree
import argparse

parser = argparse.ArgumentParser(description="On enregistre dans un fichier la boîte englobante du chantier")
parser.add_argument('--TA', help='Fichier xml du chantier')
parser.add_argument('--metadata', help='Chemin où enregistrer la BD Ortho et le MNS')
args = parser.parse_args()



def get_images_list():
    #Récupère la liste des images présentes dans le dossier
    liste_fichiers = os.listdir()
    liste_images = []
    for fichier in liste_fichiers:
        if fichier[-4:] == ".tif" and "OIS-Reech" in fichier:
            liste_images.append(fichier.split(".")[0])
    return liste_images


def read_xml(path):
    #Récupère pour chaque cliché le nom de l'image et l'emprise donnée par le fichier xml
    tree = etree.parse(path)
    root = tree.getroot()

    images = []
    
    for cliche in root.getiterator("cliche"):
        image = {}
        image["nom"] = cliche.find("image").text.strip()
        polygon2d = cliche.find("polygon2d")
        x = polygon2d.findall("x")
        y = polygon2d.findall("y")
        x = [float(i.text) for i in x]
        y = [float(i.text) for i in y]
        
        image["x"] = x
        image["y"] = y
        images.append(image)

    return images

def get_bbox(liste_images, images):
    #Sauvegarde les emprises dans un fichier shapefile

    xmin = 1e15
    ymin = 1e15
    xmax = -1e15
    ymax = -1e15

    for image in images:
        if "OIS-Reech_"+image["nom"] in liste_images:
            for i in range(len(image["x"])):
                xmin = min(xmin, image["x"][i])
                ymin = min(ymin, image["y"][i])
                xmax = max(xmax, image["x"][i])
                ymax = max(ymax, image["y"][i])

    return [xmin, ymin, xmax, ymax]


def save_bbox(bbox):
    
    with open(os.path.join(args.metadata, "bbox.txt"), "w") as f:
        for i in bbox:
            f.write("{}\n".format(i))

path_xml = args.TA

#Récupère la liste des images présentes dans le dossier
liste_images = get_images_list()

#Récupère les emprises indiquées dans le fichier de métadonnées xml du chantier 
images= read_xml(path_xml)



#Sauvegarde dans un fichier shapefile les emprises seulement pour les images présentes dans le dossier
bbox = get_bbox(liste_images, images)

#Sauvegarde la bounding box du chantier. Sert à déterminer l'emprise de la BD Topo si nécessaire
save_bbox(bbox)