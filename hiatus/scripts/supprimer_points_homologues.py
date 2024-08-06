import argparse
import os
import geopandas as gpd
from shapely import Polygon, intersects
import shutil


parser = argparse.ArgumentParser(description="Visualise les points de liaisons")
parser.add_argument('--homol_input', help='Répertoire contenant les points homologues')
parser.add_argument('--homol_output', help='Répertoire où exporter les points homologues filtrés')
parser.add_argument('--emprises', help='Emprises au sol')
args = parser.parse_args()



homol_input_dir = args.homol_input
homol_output_dir = args.homol_output
emprises_file = args.emprises


def recuperer_emprises(emprises):
    images = []
    gdf = gpd.read_file(emprises)
    for image in gdf.iterfeatures():
        dict = {}
        dict["nom"] = image["properties"]["nom"]
        geometry = Polygon(image["geometry"]["coordinates"][0])
        dict["geometry"] = geometry
        images.append(dict)
    return images

def get_emprise(image, emprises):
    for emprise in emprises:
        if emprise["nom"] == image:
            return emprise["geometry"]
    raise ValueError("Impossible de trouver l'emprise de l'image {}".format(image))



def intersection(image_1, image_2, emprises):
    emprise_1 = get_emprise(image_1, emprises)
    emprise_2 = get_emprise(image_2, emprises)
    return intersects(emprise_1, emprise_2)


emprises = recuperer_emprises(emprises_file)

nb_homol_list = []
geometries = []

os.makedirs(homol_output_dir, exist_ok=True)

homol_dir_images = os.listdir(homol_input_dir)
for homol_dir_image in homol_dir_images:
    os.makedirs(os.path.join(homol_output_dir, homol_dir_image), exist_ok=True)
    image_name = homol_dir_image[16:-4]
    homol_files = os.listdir(os.path.join(homol_input_dir, homol_dir_image))
    for homol_file in homol_files:
        homol_file_name = homol_file[10:-8]
        
        if intersection(image_name, homol_file_name, emprises):
            shutil.copy(os.path.join(homol_input_dir, homol_dir_image, homol_file), os.path.join(homol_output_dir, homol_dir_image, homol_file))