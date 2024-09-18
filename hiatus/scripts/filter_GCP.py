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

import geopandas
from shapely.geometry import  Point
from osgeo import ogr
from osgeo import osr
import os
import requests
import argparse
from lxml import etree
from tools import getEPSG, load_bbox
import log # Chargement des configurations des logs
import logging

logger = logging.getLogger("root")

parser = argparse.ArgumentParser(description="Filtrage des points d'appuis du chantier par la BD Topo")
parser.add_argument('--appuis', help="Points d'appuis de la BD Ortho")
parser.add_argument('--S2D', help="Points d'appuis de l'orthomosaïque")
parser.add_argument('--metadata', help='Chemin où enregistrer la BD Topo')
parser.add_argument('--GCP_save', help="Points d'appuis de la BD Ortho")
parser.add_argument('--S2D_save', help="Points d'appuis de l'orthomosaïque")
parser.add_argument('--etape', help="1 ou 10")
args = parser.parse_args()



def download_data_BDTopo(bbox, layer, name):

    path_tuile = os.path.join(args.metadata, name)
    type_data = "BD_Topo"
    wfs_url = "https://data.geopf.fr/wfs/ows"

    
        
    if not os.path.exists(path_tuile):
        os.makedirs(path_tuile)
   

    #Le service WFS de l'IGN ne fournit pas plus de 1000 objets, donc il est nécessaire de diviser la surface en dalles, ici de 1 km de côté. Il manquera peut-être quelques bâtiments dans des zones très denses en bati, mais cela devrait permettre d'en récupérer assez
    #Pour voir les contraintes sur les requêtes wfs :
    #https://wxs.ign.fr/ortho/geoportail/r/wfs?SERVICE=WMS&REQUEST=GetCapabilities
    emin, nmin, emax, nmax = bbox

    #Les positions des sommets de prises de vue sont approximatives, donc il faut ajouter une marge
    emin -= 500
    nmin -= 500
    emax += 500
    nmax += 500

    liste_e = [e for e in range(int(emin), int(emax), 1000)]
    liste_e.append(emax)

    liste_n = [n for n in range(int(nmin), int(nmax), 1000)]
    liste_n.append(nmax)

    for i in range(len(liste_e) - 1):
        e_min_dalle = liste_e[i]
        e_max_dalle = liste_e[i+1]
        for j in range(len(liste_n) - 1):
            n_min_dalle = liste_n[j]
            n_max_dalle = liste_n[j+1]

            #Curieusement, il semble qu'il n'y ait pas moyen de récupérer les coordonnées en 2154, mais on peut quand même définir la bounding box en 2154
            bbox_string = "{},{},{},{},EPSG:{}".format(e_min_dalle, n_min_dalle, e_max_dalle, n_max_dalle, EPSG).strip()
            
            r = requests.get(wfs_url, params={
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetFeature',
                'resultType': 'results',
                'typename': layer,
                'bbox': bbox_string,
                'outputFormat': 'application/json'
            })


            #On sauvegarde dans un fichier json les dalles
            chemin4326 = os.path.join(path_tuile, '{}_dalle_{}_{}.GeoJSON'.format(type_data, i, j))
            with open(chemin4326, 'wb') as f:
                f.write(bytes(r.content))

    return path_tuile



def create_buffer_bati(path_dalles_json, outputBufferfn, bufferDist):
    """
    Dans cette fonction, on applique un buffer sur le bâti de la BD Topo, mais on en profite aussi réunir toutes les dalles en une seule
    et à passer de l'EPSG 4326 à l'EPSG du chantier
    """

    #On définit le repère de référence des données d'entrée
    inSpatialRef = osr.SpatialReference()
    inSpatialRef.ImportFromEPSG(4326)

    #Sans cette ligne, les coordonnées sont inversées
    inSpatialRef.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    #On définit le repère de référence des données en sortie
    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(EPSG)

    #On définit la transformation pour passer du repère d'entrée au repère de sortie
    coordTrans = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)

    #On crée le fichier qui contiendra le buffer
    shpdriver = ogr.GetDriverByName('ESRI Shapefile')

    chemin_buffer = os.path.join(path_dalles_json, outputBufferfn)
    if os.path.exists(chemin_buffer):
        shpdriver.DeleteDataSource(chemin_buffer)
    outputBufferds = shpdriver.CreateDataSource(chemin_buffer)
    bufferlyr = outputBufferds.CreateLayer(chemin_buffer, geom_type=ogr.wkbPolygon)
    featureDefn = bufferlyr.GetLayerDefn()

    #On parcourt chaque dalle de la BD Topo
    dalles_json = os.listdir(path_dalles_json)
    for dalle in dalles_json:
        inputfn = os.path.join(path_dalles_json, dalle)
        inputds = ogr.Open(inputfn)
        if inputds:
            inputlyr = inputds.GetLayer()

            #On parcourt chaque vecteur de la dalle
            for feature in inputlyr:
                ingeom = feature.GetGeometryRef()
                #On applique le changement de repère
                ingeom.Transform(coordTrans)
                #On applique le buffer
                geomBuffer = ingeom.Buffer(bufferDist)

                #On enregistre le vecteur
                outFeature = ogr.Feature(featureDefn)
                outFeature.SetGeometry(geomBuffer)
                bufferlyr.CreateFeature(outFeature)
                outFeature = None
    return chemin_buffer



def download_data(bbox):
    #Chargement des bâtiments de la BD Topo
    layer = 'BDTOPO_V3:batiment'
    name = "bati"
    path_tuile_bati = download_data_BDTopo(bbox, layer, name)

    #On applique un buffer sur les bâtiments car les points d'appuis pertinents peuvent se trouver au milieu d'une rue
    path_bati = create_buffer_bati(path_tuile_bati, "BD_Topo_buffer.shp", 20)


    #Chargement de la végétation de la BD Topo
    layer = 'BDTOPO_V3:zone_de_vegetation'
    name = "vegetation"
    path_tuile_vegetation = download_data_BDTopo(bbox, layer, name)

    #On applique un buffer qui ici ne fait que fusionner les différentes dalles
    path_vegetation = create_buffer_bati(path_tuile_vegetation, "BD_Topo_buffer.shp", 0)

    #Chargement des surfaces hydrographiques de la BD Topo
    layer = 'BDTOPO_V3:surface_hydrographique'
    name = "surface_hydro"
    path_tuile_hydro= download_data_BDTopo(bbox, layer, name)
    #On applique un buffer qui ici ne fait que fusionner les différentes dalles
    path_hydro = create_buffer_bati(path_tuile_hydro, "BD_Topo_buffer.shp", 0)
    
    return path_bati, path_vegetation, path_hydro 


def filter_GCP(path_bati, path_vegetation, path_hydro):

    #On charge les différentes couches de la BD Topo
    logger.info("Chargement du bati")
    bati = geopandas.read_file(path_bati)
    #On réunit tous les géométries d'une couche en une seule afin que le sindex.query fonctionne sans avoir besoin d'itérer sur toutes les géométries
    bati_dissolved = bati.dissolve()

    logger.info("Chargement de la végétation")
    vegetation = geopandas.read_file(path_vegetation)
    vegetation_dissolved = vegetation.dissolve()

    logger.info("Chargement de l'hydro")
    hydro = geopandas.read_file(path_hydro)
    hydro_dissolved = hydro.dissolve()

    #Lecture du fichier xml
    tree = etree.parse(args.appuis)
    root = tree.getroot()
    tmp_list = []
    liste_appuis = root.findall(".//OneAppuisDAF")
    compte = 0
    for appui in liste_appuis:
        compte += 1
        coordonnees = appui.find("Pt").text.split()
        X = float(coordonnees[0])
        Y = float(coordonnees[1])
        tmp_list.append({
            'geometry' : Point(X, Y),
            'id': compte,
            'name': appui.find("NamePt").text,
        })
    
    #Les points d'appuis sont transformés dans un format lisible par geopandas
    pointsAppuis = geopandas.GeoDataFrame(tmp_list)

    #Recherche par sélection par localisation à l'aide d'un index afin d'accélérer les calculs
    resultatBati = pointsAppuis.sindex.query(bati_dissolved.geometry[0], predicate="contains")
    resultatVegetation = pointsAppuis.sindex.query(vegetation_dissolved.geometry[0], predicate="contains")
    resultatHydro = pointsAppuis.sindex.query(hydro_dissolved.geometry[0], predicate="contains")

    liste_appuis_supprimes = []
    liste_points_conserves = []
    compte_bati = 0
    compte_foret = 0
    compte_eau = 0
    compte_champs = 0
    #On parcourt tous les points d'appuis
    for i in range(len(liste_appuis)):
        appui = liste_appuis[i]
        
        
        #Si le point d'appui est dans du bati, on le conserve
        if i in resultatBati:
            compte_bati += 1
            liste_points_conserves.append(tmp_list[i]["name"])

        #S'il est dans de la végétation, on le supprime
        elif i in resultatVegetation:
            liste_appuis_supprimes.append(tmp_list[i]["name"])
            appui.getparent().remove(appui)
            compte_foret += 1

        #S'il est dans de l'eau, on le supprime
        elif i in resultatHydro:
            liste_appuis_supprimes.append(tmp_list[i]["name"])
            appui.getparent().remove(appui)
            compte_eau += 1

        #Sinon, on le dépondère
        else:
            compte_champs += 1
            liste_points_conserves.append(tmp_list[i]["name"])
            appui.find("Incertitude").text = "{} {} {}".format(-1, -1, 1)
        

    logger.info("Répartition des points d'appuis : ")
    logger.info("Bati : {}".format(compte_bati))
    logger.info("Forêt : {}".format(compte_foret))
    logger.info("Eau : {}".format(compte_eau))
    logger.info("Champs : {}".format(compte_champs))

    with open(os.path.join("reports", "rapport_complet.txt"), 'a') as f:
        f.write("Répartition des points d'appuis : \n")
        f.write("Bati : {}\n".format(compte_bati))
        f.write("Forêt : {}\n".format(compte_foret))
        f.write("Eau : {}\n".format(compte_eau))
        f.write("Champs : {}\n".format(compte_champs))
        f.write("\n\n\n")


    #On sauvegarde le fichier
    with open(args.GCP_save, "w") as f:
        f.write("<?xml version=\"1.0\" ?>\n")
        f.write(str(etree.tostring(tree, encoding='unicode')))
    
    return liste_appuis_supprimes, liste_points_conserves




def delete_GCP(liste_appuis_supprimes):
    #On supprime les points d'appuis qui ont été supprimés dans GCP.xml
    tree = etree.parse(args.S2D)
    root = tree.getroot()

    for appui in root.findall(".//OneMesureAF1I"):
        nom_point = appui.find("NamePt").text
        if nom_point in liste_appuis_supprimes:
            appui.getparent().remove(appui)

    #On sauvegarde le fichier
    with open(args.S2D_save, "w") as f:
        f.write("<?xml version=\"1.0\" ?>\n")
        f.write(str(etree.tostring(tree, encoding='unicode')))

def save_GCP_id(liste_points_conserves):
    with open("id_GCP.txt", "w") as f:
        for point in liste_points_conserves:
            f.write("{}\n".format(point))


#Chargement de la bounding box de la zone
bbox = load_bbox(args.metadata)

#On récupère l'EPSG du chantier
EPSG = getEPSG(args.metadata)


logger.info("Téléchargement de la BD Topo")
if args.etape=="1":
    #On télécharge le bâti, la végétation et l'hydrographie de la BD Topo
    path_bati, path_vegetation, path_hydro = download_data(bbox)

path_bati = os.path.join(args.metadata, "bati", "BD_Topo_buffer.shp")
path_vegetation = os.path.join(args.metadata, "vegetation", "BD_Topo_buffer.shp")
path_hydro = os.path.join(args.metadata, "surface_hydro", "BD_Topo_buffer.shp")


liste_appuis_supprimes, liste_points_conserves = filter_GCP(path_bati, path_vegetation, path_hydro)

delete_GCP(liste_appuis_supprimes)

save_GCP_id(liste_points_conserves)
