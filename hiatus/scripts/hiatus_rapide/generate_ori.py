import rasterio
import numpy as np
from lxml import etree
import argparse
import os


parser = argparse.ArgumentParser(description="Script permettant de créer les fichiers ori pour la recherche de points d'appuis avec hiatus_rapide.")
parser.add_argument('--metadata', help="Répertoire contenant les métadonnées")
parser.add_argument('--ta_xml', help="Fichier TA.xml")
args = parser.parse_args()

"""
Les points d'appuis ont été trouvés une première fois sur les images sous-échantillonnées d'un facteur 10. 
Ces premiers points d'appuis servent à déterminer la translation à appliquer sur les imagettes afin qu'elles correspondent 
au mieux lorsque l'on appliquera la recherche de points d'appuis à résolution normale

Toutefois, pour chaque imagette, pour déterminer les points d'appuis à sélectionner parmi ceux trouvés précédemment, il faut d'abord créer un fichier ori.
Comme les imagettes ne sont pas forcément bien à l'horizontale (contrairement à hiatus.sh où l'on utilise l'ortho précalculée), 
prendre le point origine du geotransform ne correspond pas forcément au point supérieur gauche. Pour ne pas s'embêter avec des rotations 
qui peuvent varier selon les chantiers, le fichier ori décrit la boîte englobante de l'image
"""

metadata = args.metadata
ta_xml_path = args.ta_xml

def convert_geotransform_to_array(gt):
    """
    It is faster to convert xy to row column (and inversally) with a numpy array rather than rasterio.Affine object
    """
    return np.array([[gt.a, gt.b, gt.c], [gt.d, gt.e, gt.f], [0, 0, 1]])

def open_image(image_name):
    src_image = rasterio.open(image_name)
    image_array = src_image.read()
    return image_array


def read_ta(ta_xml):
    tree = etree.parse(ta_xml)
    root = tree.getroot()
    return root


def get_footprint(ta_xml, image_name, image):
    """
    Get approximation of image_name geotransform

    """
    # Find in TA_xml the image
    _, l_image, c_image = image.shape
    image_name_not_OIS = image_name.replace("OIS-Reech_", "").replace(".tif", "")
    for cliche in ta_xml.getiterator("cliche"):
        if cliche.find("image").text.strip() == image_name_not_OIS:
            # get footprint
            polygon2d = cliche.find("polygon2d")
            x = polygon2d.findall("x")
            y = polygon2d.findall("y")
            points = [(float(x[i].text), float(y[i].text)) for i in range(len(x))]
            
            # create geotransform object 
            c = points[0][0]
            f = points[0][1]
            a = (points[2][0]-points[0][0])/c_image
            b = (points[2][1]-points[0][1])/c_image
            d = (points[-2][0]-points[0][0])/l_image
            e = (points[-2][1]-points[0][1])/l_image
            geotransform = rasterio.Affine(a, b, c, d, e, f)
            
            # Convert geotransform in array
            gt_array = convert_geotransform_to_array(geotransform)
            
            return gt_array
    raise ValueError("Emprise de l'image {} non trouvée dans le fichier ta_xml".format(image_name_not_OIS))



def create_ori(path, x_min, x_max, y_min, y_max):
    with open(path, "w") as f:
        f.write("CARTO\n")
        f.write("{} {}\n".format(x_min*1000, y_max*1000))
        f.write("0\n")
        f.write("1000 1000\n")
        f.write("{} {}\n".format(x_max-x_min, y_max-y_min))# pour être exact : (x_max-x_min)/1000*1000


def one_image(path_appuis, image_name, ta_xml):

    # Open image
    image = open_image(image_name)

    # Get image footprint from ta_xml (approximation of around 100 meters)
    gt_image = get_footprint(ta_xml, image_name, image)
    _, l_image, c_image = image.shape


    # Cut in tiles of 1000*facteur_sous_ech pixels
    for l_count, l in enumerate(range(0, l_image, 1000)):
        for c_count, c in enumerate(range(0, c_image, 1000)):
            max_l = min(l+1000, l_image)
            max_c = min(c+1000, c_image)
            lignes = np.array([l, max_l])
            colonnes = np.array([c, max_c])
            ll, cc = np.meshgrid(lignes, colonnes)
            cc_reshaped = cc.reshape((1, -1))
            ll_reshaped = ll.reshape((1, -1))
            ones = np.ones(cc_reshaped.shape)
            coords_lc = np.concatenate((cc_reshaped, ll_reshaped, ones))

            # get xy coordinates
            coords_xy = gt_image @ coords_lc # C'est interminable si on passe par l'objet Affine de rasterio, donc autant le faire à la main
            x_min = np.min(coords_xy[0,:])
            x_max = np.max(coords_xy[0,:])
            y_min = np.min(coords_xy[1,:])
            y_max = np.max(coords_xy[1,:])
            ori_name = "{}--{}_{}.ori".format(image_name.replace(".tif", ""), l_count, c_count)
            create_ori(os.path.join(path_appuis, ori_name), x_min, x_max, y_min, y_max)



# read ta.xml
ta_xml = read_ta(ta_xml_path)

# Create dir appuis
path_appuis = os.path.join("appuis", "dallage")
os.makedirs(path_appuis, exist_ok=True)

# Get images name
images_names = [i for i in os.listdir() if i[:10]=="OIS-Reech_" and i[-4:]==".tif"]
for image_name in images_names:
    # For each image, cut in small tiles and get the equivalent from the BD Ortho
    one_image(path_appuis, image_name, ta_xml)