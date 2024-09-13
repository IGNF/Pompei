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

import os
from lxml import etree
from osgeo import ogr
from osgeo import osr
import fiona                                                                                                       
from shapely.ops import unary_union                                                                             
from shapely.geometry import shape, mapping  
import argparse
import shutil
from math import sqrt
from osgeo import gdal

parser = argparse.ArgumentParser(description="Visualisation de la position approximative des chantiers")
parser.add_argument('--chantier', help='Répertoire du chantier')
parser.add_argument('--TA', help='Fichier xml du chantier')
args = parser.parse_args()


chemin_chantier = args.chantier
path_xml = args.TA
chemin_metadata = os.path.join(chemin_chantier, "metadata")


def findEPSG(root):
    projection = root.find(".//projection").text.strip()
    dictionnaire = {
        "UTM_WGS84_f01sud":32701,
        "UTM_WGS84_f05sud":32705,
        "UTM_WGS84_f06sud":32706,
        "UTM_WGS84_f07sud":32707,
        "UTM_WGS84_f12nord":32612,
        "UTM_WGS84_f20nord":32620,
        "UTM_WGS84_f21nord":32621,
        "UTM_WGS84_f22nord":32622,
        "UTM_WGS84_f30nord":32630,
        "UTM_WGS84_f31nord":32631,
        "UTM_WGS84_f32nord":32632,
        "UTM_WGS84_f33nord":32633,
        "UTM_WGS84_f34nord":32634,
        "UTM_WGS84_f36nord":32636,
        "UTM_WGS84_f38sud":32738,
        "UTM_WGS84_f39sud":32739,
        "UTM_WGS84_f40sud":32740,
        "UTM_WGS84_f42sud":32742,
        "UTM_WGS84_f43sud":32743,
        "UTM_WGS84_f58sud":32758,
        "Lambert93":2154,
    }

    os.makedirs(chemin_metadata, exist_ok=True)

    EPSG = dictionnaire[projection]
    with open(os.path.join(chemin_metadata, "EPSG.txt"), "w") as f:
        f.write(str(EPSG))

    print("L'EPSG du chantier est {}".format(EPSG))

    return EPSG



def getListeImages():
    #Récupère la liste des images présentes dans le dossier
    liste_fichiers = os.listdir(chemin_chantier)
    liste_images = []
    for fichier in liste_fichiers:
        if fichier[-4:] == ".tif" or fichier[-4:] == ".jp2":
            liste_images.append(fichier.split(".")[0])
    return liste_images

def find_recouvrement(x, y):
    dist1 = sqrt((x[2] - x[0])**2 + (y[2] - y[0])**2)
    dist2 = sqrt((x[2] - x[4])**2 + (y[2] - y[4])**2)
    dist3 = sqrt((x[6] - x[4])**2 + (y[6] - y[4])**2)
    dist4 = sqrt((x[6] - x[0])**2 + (y[6] - y[0])**2)
    
    distance_buffer = min(dist1, dist2, dist3, dist4) * 0.1
    return distance_buffer

def lecture_xml(path):
    #Récupère pour chaque cliché le nom de l'image et l'footprintdonnée par le fichier xml
    tree = etree.parse(path)
    root = tree.getroot()

    images = []
    min_distance_buffer = 1e15

    for nb_vol, vol in enumerate(root.getiterator("vol")):
        for cliche in vol.getiterator("cliche"):
            image = {}
            image["nom"] = cliche.find("image").text.strip()
            polygon2d = cliche.find("polygon2d")
            x = polygon2d.findall("x")
            y = polygon2d.findall("y")
            x = [float(i.text) for i in x]
            y = [float(i.text) for i in y]
            distance_buffer = find_recouvrement(x, y)
            if distance_buffer < min_distance_buffer:
                min_distance_buffer = distance_buffer
            
            image["x"] = x
            image["y"] = y
            image["nb_vol"] = nb_vol
            images.append(image)
    print("La distance appliquée sur le buffer est {} m".format(distance_buffer))

    EPSG = findEPSG(root)

    return images, -min_distance_buffer, EPSG

def remove_images_without_metadata(liste_images, images):
    path_without_metadata = os.path.join(chemin_chantier, "images_without_metadata")
    #Met de côté des images qui n'ont pas de métadonnées dans le fichier xml
    os.makedirs(path_without_metadata, exist_ok=True)

    for image in liste_images:
        booleen = False
        for image_metadata in images:
            if image_metadata["nom"]== image.strip():
                booleen = True
        if not booleen:
            shutil.move(os.path.join(chemin_chantier, image+".jp2"), os.path.join(path_without_metadata, image+".jp2"))
            print("L'image {} n'a pas de métadonnées. Elle est retirée des données.".format(image))

def save_shapefile(liste_images, images, path_footprint_chantier, EPSG):
    #Sauvegarde les footprints dans un fichier shapefile

    driver = ogr.GetDriverByName("ESRI Shapefile")

    ds = driver.CreateDataSource(path_footprint_chantier)
    srs =  osr.SpatialReference()
    srs.ImportFromEPSG(EPSG)

    layer = ds.CreateLayer("line", srs, ogr.wkbPolygon)

    nameField = ogr.FieldDefn("nom", ogr.OFTString)
    volField = ogr.FieldDefn("nb_vol", ogr.OFTString)
    layer.CreateField(nameField)
    layer.CreateField(volField)

    featureDefn = layer.GetLayerDefn()


    for image in images:
        if image["nom"] in liste_images:
            ring = ogr.Geometry(ogr.wkbLinearRing)
            for i in range(len(image["x"])):
                ring.AddPoint(image["x"][i], image["y"][i])
            ring.AddPoint(image["x"][0], image["y"][0])

            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(ring)
            
            feature = ogr.Feature(featureDefn)
            feature.SetGeometry(poly)
            feature.SetField("nom", image["nom"])
            feature.SetField("nb_vol", image["nb_vol"])
            layer.CreateFeature(feature)

            feature = None

    ds = None



def createBuffer(inputfn, outputBufferfn, bufferDist):
    #Applique un buffer sur les footprints
    inputds = ogr.Open(inputfn)
    inputlyr = inputds.GetLayer()

    shpdriver = ogr.GetDriverByName('ESRI Shapefile')
    if os.path.exists(outputBufferfn):
        shpdriver.DeleteDataSource(outputBufferfn)
    outputBufferds = shpdriver.CreateDataSource(outputBufferfn)
    bufferlyr = outputBufferds.CreateLayer(outputBufferfn, geom_type=ogr.wkbPolygon)
    featureDefn = bufferlyr.GetLayerDefn()

    for feature in inputlyr:
        ingeom = feature.GetGeometryRef()
        geomBuffer = ingeom.Buffer(bufferDist)

        outFeature = ogr.Feature(featureDefn)
        outFeature.SetGeometry(geomBuffer)
        bufferlyr.CreateFeature(outFeature)
        outFeature = None

def merge(src, dst, typeData):
    #Regroupe toutes les footprints qui sont connexes
    with fiona.open(src, 'r') as ds_in: 
        crs = ds_in.crs 
        drv = ds_in.driver 

        filtered = filter(lambda x: shape(x["geometry"]).is_valid, list(ds_in))                                                                                   

        geoms = [shape(x["geometry"]) for x in filtered]                                                   
        dissolved = unary_union(geoms)                                    

    schema = {                                                                                                     
        "geometry": "Polygon",                                                                                     
        "properties": {"id": "int"}                                                                                
    }  


    try:
        with fiona.open(dst, 'w', driver=drv, schema=schema, crs=crs) as ds_dst:                                       
            id = 0
            for geom in dissolved.geoms:
                ds_dst.write({"geometry": mapping(geom), "properties": {"id": id}})
                id += 1
    except:
        with fiona.open(dst, 'w', driver=drv, schema=schema, crs=crs) as ds_dst:                                       
            id = 0
            ds_dst.write({"geometry": mapping(dissolved), "properties": {"id": id}})
                
    if id > 1:
        if typeData=="buffer":
            print("Attention : des images sont isolées sur le chantier. Regardez les fichiers {} et {}". format(path_footprint_chantier, path_buffer))
        elif typeData=="recouvrement":
            print("Attention : le recouvrement n'est pas idéal. Regardez les fichiers {} et {}". format(path_footprint_chantier, path_buffer))


def recouvrement(chemin_footprint, chemin_resultat):
    schema = {                                                                                                     
        "geometry": "Polygon",                                                                                     
    }
    footprints1 = fiona.open(chemin_footprint)
    with fiona.open(chemin_resultat, 'w',driver='ESRI Shapefile', schema=schema, crs=footprints1.crs) as output:
        for emp1 in footprints1:
            for emp2 in fiona.open(chemin_footprint):
                if emp1['id'] != emp2['id'] and shape(emp1['geometry']).intersects(shape(emp2['geometry'])):
                    intersection = shape(emp1['geometry']).intersection(shape(emp2['geometry']))
                    output.write({'geometry':mapping(intersection)})

def calcul_proportion_recouvrement(path_recouvrement_merged, path_footprint_chantier_merged):
    aire_recouvrement = 0
    aire_chantier = 0
    for emp1 in fiona.open(path_recouvrement_merged):
        aire_recouvrement += shape(emp1['geometry']).area
    for emp2 in fiona.open(path_footprint_chantier_merged):
        aire_chantier += shape(emp2['geometry']).area
    print("{0:.2f} % du chantier est vu depuis au moins deux points de vue".format(aire_recouvrement/aire_chantier*100))


def get_nb_couleurs():
    image = [i for i in os.listdir(chemin_chantier) if i[-4:]==".jp2" or i[-4:]==".tif"]
    inputds = gdal.Open(os.path.join(chemin_chantier, image[0]))
    nbBands = inputds.RasterCount
    with open(os.path.join(chemin_metadata, "nb_colors.txt"), "w") as f:
        f.write(str(nbBands))


os.makedirs(os.path.join(chemin_chantier, "flight_plan"), exist_ok=True)
path_footprint_chantier = os.path.join(chemin_chantier, "flight_plan", "flight_plan.shp")
path_footprint_chantier_merged = os.path.join(chemin_chantier, "flight_plan", "merged_flight_plan.shp")
path_buffer = os.path.join(chemin_chantier, "flight_plan", "buffer.shp")
path_merged = os.path.join(chemin_chantier, "flight_plan", "buffer_merged.shp")
path_recouvrement = os.path.join(chemin_chantier, "flight_plan", "recouvrement.shp")
path_recouvrement_merged = os.path.join(chemin_chantier, "flight_plan", "recouvrement_merged.shp")


#Récupère la liste des images présentes dans le dossier
liste_images = getListeImages()

#Récupère les footprints indiquées dans le fichier de métadonnées xml du chantier 
images, distance_buffer, EPSG = lecture_xml(path_xml)

#Retire les images qui n'ont pas de métadonnées
remove_images_without_metadata(liste_images, images)

#Sauvegarde dans un fichier shapefile les footprints seulement pour les images présentes dans le dossier
save_shapefile(liste_images, images, path_footprint_chantier, EPSG)

#Crée un buffer sur le fichier shapefile pour tenir compte des possibles erreurs de positionnement et que les points homologues ne seront pas cherchés sur les bords des images
createBuffer(path_footprint_chantier, path_buffer, distance_buffer)

#Regroupe les footprints qui se superposent. Si l'on obtient au moins deux features, alors on met un message d'alerte : il est probable que des images soient déconnectées du reste du chantier
merge(path_buffer, path_merged, "buffer")

#Récupère les zones du chantier qui sont vues par au moins deux photos
recouvrement(path_footprint_chantier, path_recouvrement)
#Regroupe les zones du chantier qui sont vues par au moins deux photos
merge(path_recouvrement, path_recouvrement_merged, "recouvrement")

merge(path_footprint_chantier, path_footprint_chantier_merged, "footprints")

calcul_proportion_recouvrement(path_recouvrement_merged, path_footprint_chantier_merged)

get_nb_couleurs()