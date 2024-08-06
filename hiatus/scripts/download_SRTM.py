import argparse
from osgeo import gdal
import os
from pyproj import CRS, Transformer
import requests
from tools import getEPSG

parser = argparse.ArgumentParser(description="Téléchargement des dalles du SRTM du chantier")
parser.add_argument('--MNS_Histo', help='MNS de MEC-Malt-Abs-Ratafia')
parser.add_argument('--metadata', help='Dossier contenant EPSG.txt')
parser.add_argument('--output', help='Chemin où enregistrer la dalle du SRTM')
args = parser.parse_args()



def get_emprise(path_mns_histo):
    inputds = gdal.Open(path_mns_histo)
    geoTransform = inputds.GetGeoTransform()
    image = inputds.GetRasterBand(1).ReadAsArray()
    E_min = geoTransform[0]
    N_max = geoTransform[3]
    resE = geoTransform[1]
    resN = geoTransform[5]
    colonne = image.shape[1]
    ligne = image.shape[0]
    E_max = E_min + colonne * resE
    N_min = N_max + ligne * resN

    #On ajoute une marge sur la zone du SRTM à télécharger
    E_min -= 500
    E_max += 500
    N_min -= 500
    N_max += 500
    points = [(E_min, N_max), (E_max, N_max), (E_max, N_min), (E_min, N_min)]
    return points

def transform_Points_WGS84(EPSG, points):
    crsWGS84 = CRS.from_epsg(4326)
    crsChantier = CRS.from_epsg(EPSG)
    transformer = Transformer.from_crs(crsChantier, crsWGS84)
    pointsWGS84 = []
    for point in points:
        pointsWGS84.append(transformer.transform(point[0], point[1]))
    #Les points sont en latitude longitude
    return pointsWGS84


def download(pointsWGS84, path):
    south = pointsWGS84[0][0]
    north = pointsWGS84[0][0]
    east = pointsWGS84[0][1]
    west = pointsWGS84[0][1]
    for point in pointsWGS84:
        south = min(south, point[0])
        north = max(north, point[0])
        west = min(west, point[1])
        east = max(east, point[1])
    url = "https://portal.opentopography.org/API/globaldem?demtype=SRTMGL1&south={}&north={}&west={}&east={}&outputFormat=GTiff&API_Key=demoapikeyot2022".format(south, north, west, east)
    print(url)
    r = requests.get(url)
    with open(path, 'wb') as out:
        out.write(bytes(r.content))
    


points = get_emprise(args.MNS_Histo)  
EPSG = getEPSG(args.metadata)  
pointsWGS84 = transform_Points_WGS84(EPSG, points)
download(pointsWGS84, args.output)
