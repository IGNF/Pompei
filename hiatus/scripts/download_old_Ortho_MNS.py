import os
import argparse
import requests
from lxml import etree
import numpy as np
from osgeo import gdal, osr
from tools import getEPSG, load_bbox, getResolution

parser = argparse.ArgumentParser(description="Téléchargement des dalles de la BD Ortho ou des orthos historiques déjà calculées et du MNS du chantier")
parser.add_argument('--metadata', help='Chemin où enregistrer la BD Ortho et le MNS')
args = parser.parse_args()


def emprise_commune(bbox1, bbox2):
    e_min = max(bbox1[0], bbox2[0])
    n_min = max(bbox1[1], bbox2[1])
    e_max = min(bbox1[2], bbox2[2])
    n_max = min(bbox1[3], bbox2[3])
    if e_min < e_max and n_min < n_max:
        return True
    return False


def verification(chemin):
    print("début de la vérification")
    #S'il y a plus de 75 % de pixels de nodata dans l'image, on renvoie False et on cherchera une ortho d'un chantier plus récent
    inputds = gdal.Open(chemin)
    inputlyr = np.array(inputds.GetRasterBand(1).ReadAsArray())
    valeur_non_nulle = np.ones(inputlyr.shape)
    valeur_non_nulle[inputlyr==0] = 0
    valeur_non_nulle[inputlyr==255] = 0
    print("Proportion : ",np.sum(valeur_non_nulle) / (inputlyr.shape[1]*inputlyr.shape[0]) * 100)
    if np.sum(valeur_non_nulle) / (inputlyr.shape[1]*inputlyr.shape[0]) * 100 < 75:
        return False
    driver = gdal.GetDriverByName('GTiff')
    outRaster = driver.Create(chemin, inputlyr.shape[1], inputlyr.shape[0], 3, gdal.GDT_Byte)
    outRaster.SetGeoTransform(inputds.GetGeoTransform())

    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(EPSG)
    outRaster.SetProjection(outSpatialRef.ExportToWkt())

    for i in range(1, 4):
        outband = outRaster.GetRasterBand(i)
        outband.WriteArray(inputlyr)
    return True

def write_tfw(chemin, e_min_dalle, n_max_dalle, resolution):
    with open(chemin, 'w') as out:
        out.write("{}\n".format(resolution))
        out.write("0.00\n")
        out.write("0.00\n")
        out.write("-{}\n".format(resolution))
        out.write("{}\n".format(e_min_dalle+0.25))
        out.write("{}\n".format(n_max_dalle-0.25))

def write_ori(chemin, e_min_dalle, n_max_dalle, width, height, resolution):
    with open(chemin, 'w') as out:
        out.write("CARTO\n")
        out.write("{} {}\n".format(e_min_dalle*1000, n_max_dalle*1000))
        out.write("0\n")
        out.write("{} {}\n".format(width, height))
        out.write("{} {}\n".format(resolution*1000, resolution*1000))

def write_hdr(chemin, e_min_dalle, n_max_dalle, width, height, resolution):
    with open(chemin, 'w') as out:
        out.write(" // Convention de georeferencement : angle noeud (Geoview)\n")
        out.write("!+\n!+--------------------------\n!+ HDR/A : Image Information\n!+--------------------------\n!+\n")
        out.write("ULXMAP  {}\n".format(e_min_dalle))
        out.write("ULYMAP  {}\n".format(n_max_dalle))
        out.write("XDIM    {}\n".format(resolution))
        out.write("YDIM    {}\n".format(resolution))
        out.write("NROWS  {}\n".format(height))
        out.write("NCOLS  {}\n".format(width))
        out.write("NBANDS   1\n")
        out.write("!+\n!+--------------------------\n!+ HDR/B : Frame Corner Support\n!+--------------------------\n!+\n")
        out.write("!+\n!+--------------------------\n!+ HDR/C : File Encoding\n!+--------------------------\n!+\n")
        out.write("!+\n!+--------------------------\n!+ HDR/E : More Parameters\n!+--------------------------\n!+\n")
        out.write("COSINUS 1.00\n")
        out.write("SINUS 0.00\n")
        out.write("SIGNE	1\n")
        out.write("BAND_NAMES	Z\n")
        out.write("PROJECTION    LAMBERT93\n")

def setProjectionL93(chemin, dtype):
    #Fixe la projection de la dalle dans l'EPSG du chantier
    inputds = gdal.Open(chemin)
    inputlyr = np.array(inputds.ReadAsArray())

    driver = gdal.GetDriverByName('GTiff')
    if inputds.RasterCount == 3:
        outRaster = driver.Create(chemin, inputlyr.shape[2], inputlyr.shape[1], inputds.RasterCount, dtype)
    else:
        outRaster = driver.Create(chemin, inputlyr.shape[1], inputlyr.shape[0], inputds.RasterCount, dtype)
    outRaster.SetGeoTransform(inputds.GetGeoTransform())

    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(EPSG)
    outRaster.SetProjection(outSpatialRef.ExportToWkt())
    outRaster.WriteArray(inputlyr)


def download_MNS(url, path_meta_MNS, path_tuile_MNS, i, j, e_min_dalle, n_max_dalle, width, height, resolution):
    #On télécharge le MNS
    url = url.replace("Ortho", "MNS")
    r = requests.get(url)
    chemin = os.path.join(path_tuile_MNS, 'MNS_dalle_{}_{}.tif'.format(i, j))

    try:
        with open(chemin, 'wb') as out:
            out.write(bytes(r.content))
            write_ori(os.path.join(path_meta_MNS, 'MNS_dalle_{}_{}.ori'.format(i, j)), e_min_dalle, n_max_dalle, width, height, resolution)
            write_hdr(os.path.join(path_meta_MNS, 'MNS_dalle_{}_{}.hdr'.format(i, j)), e_min_dalle, n_max_dalle, width, height, resolution)
        setProjectionL93(chemin, gdal.GDT_Float32)
    except:
        print('MNS failed to download.')


def download_data(bbox, liste_layers):
    #On crée les dossiers qui récupèreront les données
    #On doit créer des fichier temp car il faudra ensuite appliquer un gdal_translate sur les dalles pour être sûr que les scripts de recherche de points d'appuis fonctionnent
    #On ne peut pas, dans un gdal_translate, indiquer le même chemin pour l'image en entrée et l'image en sortie
    path_meta_ortho = os.path.join(args.metadata, "ortho")
    if not os.path.exists(path_meta_ortho):
        os.makedirs(path_meta_ortho)

    path_tuile_ortho = os.path.join(args.metadata, "ortho_temp")
    if not os.path.exists(path_tuile_ortho):
        os.makedirs(path_tuile_ortho)

    path_meta_MNS = os.path.join(args.metadata, "mns")
    if not os.path.exists(path_meta_MNS):
        os.makedirs(path_meta_MNS)

    path_tuile_MNS = os.path.join(args.metadata, "mns_temp")
    if not os.path.exists(path_tuile_MNS):
        os.makedirs(path_tuile_MNS)

    #On récupère la résolution du chantier
    resolution = getResolution()

    emin, nmin, emax, nmax = bbox
    #Les positions des sommets de prises de vue sont approximatives, donc il faut ajouter une marge. On ajoute une marge de 500 mètres
    emin -= 500
    nmin -= 500
    emax += 500
    nmax += 500

    #On divise le chantier en dalles de 2000 pixels de côté
    liste_e = [e for e in range(int(emin), int(emax), int(2000 * resolution))]
    liste_e.append(emax)

    liste_n = [n for n in range(int(nmin), int(nmax), int(2000 * resolution))]
    liste_n.append(nmax)

    #On parcourt chaque dalle
    for i in range(len(liste_e) - 1):
        e_min_dalle = liste_e[i]
        e_max_dalle = liste_e[i+1]
        for j in range(len(liste_n) - 1):
            print("")
            print(i, j)
            n_min_dalle = liste_n[j]
            n_max_dalle = liste_n[j+1]
            bbox_tuile = [e_min_dalle, n_min_dalle, e_max_dalle, n_max_dalle]
            bbox_string = "{},{},{},{}".format(e_min_dalle, n_min_dalle, e_max_dalle, n_max_dalle).strip()
            width=str(int((e_max_dalle - e_min_dalle)/resolution))
            height=str(int((n_max_dalle - n_min_dalle)/resolution))

            tuile_trouvee = False

            #On parcourt chaque couche d'orthophotos disponibles, de la plus ancienne à la plus récente. On s'arrête dès que l'on trouve une couche qui convient
            for layer in liste_layers:
                if not tuile_trouvee:
                    #On vérifie que la couche possède une emprise commune avec la dalle
                    if emprise_commune(liste_layers[layer], bbox_tuile):
                        #On télécharge la couche d'ortho historique

                        print("On télécharge la couche : ", layer)
                        url = '{}wms?LAYERS={}&FORMAT=image/geotiff&SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&STYLES=&CRS=EPSG:{}&BBOX={}&WIDTH={}&HEIGHT={}'.format(adresse_geoserver, layer, EPSG, bbox_string, width, height)
                        r = requests.get(url)
                        chemin = os.path.join(path_tuile_ortho, 'ORTHO_dalle_{}_{}.tif'.format(i, j))
                        try:
                            with open(chemin, 'wb') as out:
                                out.write(bytes(r.content))
                            if verification(chemin):
                            #Si la dalle ne contient pas que du nodata, alors on crée le fichier tfw et on télécharge le MNS                            if verification(chemin):
                                print("La tuile a été bien trouvée")
                                tuile_trouvee = True
                                write_tfw(os.path.join(path_meta_ortho, 'ORTHO_dalle_{}_{}.tfw'.format(i, j)), e_min_dalle, n_max_dalle, resolution)
                                download_MNS(url, path_meta_MNS, path_tuile_MNS, i, j, e_min_dalle, n_max_dalle, width, height, resolution)
                        except:
                            print('File failed to download.')

            #Si aucune orthophoto historique ne convient, alors on télécharge la BD Ortho et le MNS actuel
            if not tuile_trouvee:
                print("On télécharge la BD Ortho")
                url = '{}?LAYERS={}&FORMAT=image/geotiff&SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&STYLES=&CRS=EPSG:{}&BBOX={}&WIDTH={}&HEIGHT={}'.format(adresse_wxs_ortho, layer_BD_Ortho, EPSG, bbox_string, width, height)
                r = requests.get(url)
                chemin = os.path.join(path_tuile_ortho, 'ORTHO_dalle_{}_{}.tif'.format(i, j))
                try:
                    with open(chemin, 'wb') as out:
                        out.write(bytes(r.content))

                    #On écrit le fichier tfw
                    write_tfw(os.path.join(path_meta_ortho, 'ORTHO_dalle_{}_{}.tfw'.format(i, j)), e_min_dalle, n_max_dalle, resolution)
                    setProjectionL93(chemin, gdal.GDT_Byte)
                    #On télécharge le MNS
                    url_MNS = '{}?LAYERS={}&FORMAT=image/geotiff&SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&STYLES=&CRS=EPSG:{}&BBOX={}&WIDTH={}&HEIGHT={}'.format(adresse_wxs_MNS, layer_MNS, EPSG, bbox_string, width, height)
                    download_MNS(url_MNS, path_meta_MNS, path_tuile_MNS, i, j, e_min_dalle, n_max_dalle, width, height, resolution)
                except:
                    print('File failed to download.')

def getCapabilities():
    #Récupère la liste des orthophotos historiques disponibles dans le geoserver
    #Les orthophotos sont considérées comme disponibles si elles ont le mot "Ortho" dans le titre et ne conteniennent pas le mot "echec"
    #Les couches de MNS ne doivent pas avoir le mot "Ortho" dans le titre.
    #Chaque couche d'orthophoto doit avoir son équivalent en MNS. Le titre du MNS doit être le même que celui de l'orthopĥoto, mais en remplaçant "Ortho" par "MNS" 
    #Chaque couche doit commencer par l'année du chantier car elles seront triées par ordre alphabétique pour aller chercher la plus ancienne

    url = adresse_geoserver + "wms?service=WMS&version=1.1.0&request=GetCapabilities&SERVICE=WMS&VERSION=1.3.0"
    r = requests.get(url)

    root = etree.fromstring(r.content)

    layers = {}
    liste_layers = root.findall(".//{http://www.opengis.net/wms}Layer")
    for layer in liste_layers:
        nom = layer.find("{http://www.opengis.net/wms}Name")
        #S'il y a une balise "nom" dans la couche
        if not nom == None :
            #S'il s'agit d'une couche d'orthophoto (et pas de MNS)
            if "Ortho" in nom.text and not "echec" in nom.text:
                #On récupère la bounding box qui est dans l'EPSG du chantier
                bounding_boxes = layer.findall(".//{http://www.opengis.net/wms}BoundingBox")
                for bounding_box in bounding_boxes:
                    #if bounding_box.get("CRS") == "EPSG:2154":
                    if bounding_box.get("CRS") == "EPSG:"+str(EPSG):
                        layers[nom.text] = [float(bounding_box.get("minx")), float(bounding_box.get("miny")), float(bounding_box.get("maxx")), float(bounding_box.get("maxy")), ]
    #On trie les couches par ordre chronologique
    return dict(sorted(layers.items()))


def filtrer_layers(liste_layers, bbox):
    #On ne conserve que les couches qui ont une emprise commune avec le chantier
    dict_filtre = {}
    for layer in liste_layers:
        bbox_layer = liste_layers[layer]
        if emprise_commune(bbox_layer, bbox):
            dict_filtre[layer] = bbox_layer
    return dict_filtre




#Adresses pour pouvoir aller chercher la BD ortho et le MNS actuel sur le geoportail
adresse_wxs_ortho = "https://wxs.ign.fr/ortho/geoportail/r/wms"
adresse_wxs_MNS = "https://wxs.ign.fr/altimetrie/geoportail/r/wms"

#Nom des couches de BD Ortho et de MNS dans le geoportail
layer_BD_Ortho='ORTHOIMAGERY.ORTHOPHOTOS.BDORTHO'
layer_MNS='ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES.MNS'

#Sur le geoserver hiatus où se trouvent les orthos historiques déjà produites
adresse_geoserver = "" # A completer avec l'adresse de votre geoserver


#Charge l'emprise du chantier
bbox = load_bbox(args.metadata)

#On récupère l'EPSG du chantier
EPSG = getEPSG(args.metadata)

#On récupère la liste des orthophotos déjà disponibles
liste_layers = getCapabilities()
print(liste_layers)

#On ne conserve que les orthos qui ont une surface commune avec le chantier
liste_layers = filtrer_layers(liste_layers, bbox)
print(liste_layers)

#On télécharge les dalles
download_data(bbox, liste_layers)
