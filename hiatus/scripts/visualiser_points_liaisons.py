import argparse
import os
import geopandas as gpd
from shapely import Polygon, LineString


parser = argparse.ArgumentParser(description="Visualise les points de liaisons")
parser.add_argument('--homol', help='Répertoire contenant les points homologues')
parser.add_argument('--emprises', help='Emprises au sol')
parser.add_argument('--rapports', help='Répertoire contenant les rapports')
args = parser.parse_args()








homol_dir = args.homol
emprises = args.emprises
rapports_dir = args.rapports

def get_number_homol(file):
    compte = 0
    with open(file, "r") as f:
        for line in f:
            compte += 1
    return compte

def get_barycentre(coordinates):
    p = Polygon(coordinates[0])
    return p.centroid


def get_center(gdf, image_name):
    for image in gdf.iterfeatures():
        if image["properties"]["nom"] == image_name:
            return get_barycentre(image["geometry"]["coordinates"])
    raise ValueError("Impossible de trouver l'image {}".format(image_name))


gdf = gpd.read_file(emprises)

nb_homol_list = []
geometries = []

homol_dir_images = os.listdir(homol_dir)
for homol_dir_image in homol_dir_images:
    image_name = homol_dir_image[16:-4]
    center_image_1 = get_center(gdf, image_name)
    homol_files = [i for i in os.listdir(os.path.join(homol_dir, homol_dir_image)) if i[-4:]==".txt"]
    for homol_file in homol_files:
        homol_file_name = homol_file[10:-8]
        nb_homol = get_number_homol(os.path.join(homol_dir, homol_dir_image, homol_file))
        center_image_2 = get_center(gdf, homol_file_name)
        nb_homol_list.append(nb_homol)
        geometries.append(LineString([center_image_1, center_image_2]))

d = {"nb_homol":nb_homol_list, "geometry": geometries}
gdf = gpd.GeoDataFrame(d, crs="EPSG:2154")
gdf.to_file(os.path.join(rapports_dir, "nb_homologues.shp"))     
        