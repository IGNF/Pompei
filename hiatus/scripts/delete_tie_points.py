import argparse
import os
import geopandas as gpd
from shapely import Polygon, intersects
import shutil


parser = argparse.ArgumentParser(description="Visualise les points de liaisons")
parser.add_argument('--homol_input', help='Répertoire contenant les points homologues')
parser.add_argument('--homol_output', help='Répertoire où exporter les points homologues filtrés')
parser.add_argument('--footprints', help='Emprises au sol')
args = parser.parse_args()



homol_input_dir = args.homol_input
homol_output_dir = args.homol_output
footprints_file = args.footprints


def get_footprints(footprints):
    images = []
    gdf = gpd.read_file(footprints)
    for image in gdf.iterfeatures():
        dict = {}
        dict["nom"] = image["properties"]["nom"]
        geometry = Polygon(image["geometry"]["coordinates"][0])
        dict["geometry"] = geometry
        images.append(dict)
    return images

def get_footprint(image, footprints):
    for footprint in footprints:
        if footprint["nom"] == image:
            return footprint["geometry"]
    raise ValueError("Impossible de trouver l'footprintde l'image {}".format(image))



def intersection(image_1, image_2, footprints):
    footprint_1 = get_footprint(image_1, footprints)
    footprint_2 = get_footprint(image_2, footprints)
    return intersects(footprint_1, footprint_2)


footprints = get_footprints(footprints_file)

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
        
        if intersection(image_name, homol_file_name, footprints):
            shutil.copy(os.path.join(homol_input_dir, homol_dir_image, homol_file), os.path.join(homol_output_dir, homol_dir_image, homol_file))