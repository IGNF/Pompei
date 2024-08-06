import geopandas as gpd
import math
from shapely.geometry import Polygon, box
import os
import argparse
import shutil
from osgeo import gdal, osr
from tools import getEPSG

parser = argparse.ArgumentParser(description="Vérification qu'il n'y a pas d'images isolées sur le chantier")
parser.add_argument('--metadata', help='Chemin où se trouvent les fichiers bbox.txt et EPSG.txt')
parser.add_argument('--scripts', help='Répertoire où se trouvent les scripts')
args = parser.parse_args()



EPSG_DEP = {
    "32620": "971", # 972,
    "32738": "976",
    "32740": "974",
    "32622": "973",
}


EPSG_WGS84_RGAF = {
    "32620": 5490,
    "32738": 4471,
    "32740": 2975,
    "32622": 2972,
    "2154": 2154
}

EPSG_NOM = {
    "32620": "RRAFUTM20",
    "32738": "RGM04UTM38S",
    "32740": "RGR92UTM40S",
    "32622": "RGFG95UTM22",
    "2154": "RGF93LAMB93"
}


def load_bbox():
    bbox = []
    with open(os.path.join(args.metadata, "bbox.txt"), "r") as f:
        for line in f:
            bbox.append(float(line.strip()))
    
    tile_factor = 1
    bbox[0] = math.floor(bbox[0]/(tile_factor*1000)) * tile_factor
    bbox[1] = math.floor(bbox[1]/(tile_factor*1000)) * tile_factor
    bbox[2] = math.ceil(bbox[2]/(tile_factor*1000)) * tile_factor
    bbox[3] = math.ceil(bbox[3]/(tile_factor*1000)) * tile_factor
    return bbox

def get_emprise_tiles(bbox, EPSG):

    #On divise l'emprise en tuiles de 1 km de côté
    tmp_list = []
    compte = 0
    for e in range(bbox[0], bbox[2], 1):
        for n in range(bbox[1], bbox[3], 1):
            geometry = Polygon([(e*1000, n*1000), ((e+1)*1000, n*1000), ((e+1)*1000, (n+1)*1000), (e*1000, (n+1)*1000)])
            
            # Si c'est en France métropolitaine, alors on détermine le département avec une jointure sur les départements de la BDAdmin
            if EPSG == 2154:
                tmp_list.append({
                    'geometry' : geometry,
                    'id': compte,
                    "name": "{}_{}".format(e, n)
                })
            else:# Si c'est dans les DOM-TOM, alors on détermine le département à partir de l'EPSG
                tmp_list.append({
                    'geometry' : geometry,
                    'id': compte,
                    "name": "{}_{}".format(e, n),
                    "INSEE_DEP":EPSG_DEP[str(EPSG)]
                })
            compte += 1
    
    # On met les tuiles dans l'EPSG des données de store-ref
    # En effet, dans les métadonnées Hiatus, les données sont en UTM WGS84
    # Dans store-ref, elles sont en UTM projection locale
    emprise_tiles = gpd.GeoDataFrame(tmp_list).set_crs(epsg=EPSG).to_crs(epsg=EPSG_WGS84_RGAF[str(EPSG)])

    if EPSG == 2154:
        #On charge le shapefile contenant les départements
        departements = gpd.read_file(os.path.join(args.scripts, "ADMIN-EXPRESS", "DEPARTEMENT.shp"))

        #On effectue une jointure entre les tuiles et les départements
        emprise_tiles_join = gpd.sjoin(emprise_tiles, departements)

        return emprise_tiles_join

    else:
        return emprise_tiles


def ajouter_departement(departements_MNS_existants, departement, annee, MNS_directory, resolution):
    if departement not in departements_MNS_existants.keys():
        departements_MNS_existants[departement] = [{"annee":annee, "repertoire":MNS_directory, "resolution":resolution}]
    else:
        departements_MNS_existants[departement].append({"annee":annee, "repertoire":MNS_directory, "resolution":resolution})
    return departements_MNS_existants


def get_millesimes(emprise_tiles):

    #On récupère la liste des départements
    liste_departements = []
    for tile in emprise_tiles.iterfeatures():
        if tile["properties"]["INSEE_DEP"] not in liste_departements:
            liste_departements.append(tile["properties"]["INSEE_DEP"])
    # Les départements 971 et 972 sont dans le même EPSG
    if "971" in liste_departements and "972" not in liste_departements:
        liste_departements.append("972")

    chemin_MNS = os.path.join("/media", 'store-ref', "modeles-numeriques-3D", "MNS")
    MNS_directories = [i for i in os.listdir(chemin_MNS) if "MNS_TIFF_" in i]

    departements_MNS_existants = {}
    for MNS_directory in MNS_directories:
        code = MNS_directory.split("_")
        if len(code) == 4:
            code = code[3]
            resolution = code[-2:]
            annee = code[0:2]
            departement = code[4:-2]

        else:
            resolution = code[-1]
            annee = code[3][:2]
            departement = code[4]
            code = code[3]

        if "IDF" in code:
            deps = ["75", "77", "78", "91", "92", "93", "94", "95"]
        elif departement == "2AB":
            deps = ["2A", "2B"]
        elif len(departement) >= 4:
            departement1 = departement[:2]
            departement2 = departement[2:]
            deps = [departement1, departement2]
        else:
            deps = [departement]

        for dep in deps:
            departements_MNS_existants = ajouter_departement(departements_MNS_existants, dep, annee, MNS_directory, resolution)

    # On choisit en priorité les données les plus anciennes    
    MNS_disponibles_chantiers = {}
    for departement in liste_departements:
        if departement in departements_MNS_existants.keys():
            MNS_disponibles_chantiers[departement] = sorted(departements_MNS_existants[departement], key=lambda d: d['annee']) 

    return MNS_disponibles_chantiers


def save_hdr(name, e_min_dalle, n_max_dalle, height, width, resolution):
    with open(os.path.join(args.metadata, "mns", name), 'w') as out:
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





def get_dalles(emprise_tiles, MNS_disponibles_chantiers, EPSG):
    
    #On parcourt toutes les tuiles de l'emprise
    for tile in emprise_tiles.iterfeatures():
        departement_tile = tile["properties"]["INSEE_DEP"]

        #On récupère les coordonnées de la tuile
        e_min = int(tile["geometry"]["coordinates"][0][0][0] / 1000)
        n_min = int(tile["geometry"]["coordinates"][0][0][1] / 1000)

        if e_min < 1000:
            e_min = "0" + str(e_min)
        else:
            e_min = str(e_min)

        if n_min < 1000:
            n_min = "0" + str(n_min)
        else:
            n_min = str(n_min)

        trouve = False

        geom = Polygon(tile["geometry"]["coordinates"][0])

        #On parcourt tous les chantiers du répertoire
        for chantier in MNS_disponibles_chantiers[departement_tile]:

            if not trouve:
                if chantier["resolution"] == "15":
                    chemin_MNS = os.path.join("/media", 'store-ref', "modeles-numeriques-3D", "MNS", chantier["repertoire"], "data", "MNS_CORREL_1-0", "dataset")
                    name = os.listdir(chemin_MNS)[0][:-4].split("_")


                    for x_end in range(0, 10):
                        for y_end in range(0, 10):
                            
                            name[-2] = e_min[1:] + str(x_end)
                            name[-1] = n_min + str(y_end)
                            filename = "_".join(name) + ".tif"
                            
                            x_bl = int(e_min)*1000.0+x_end*100
                            y_bl = int(n_min)*1000.0+y_end*100
                            file_box = box(x_bl, y_bl, x_bl+600, y_bl+600)

                            if os.path.exists(os.path.join(chemin_MNS, filename)) and file_box.intersects(geom) and not file_box.touches(geom):
                                
                                chemin_image_local = os.path.join(args.metadata, "mns_temp2", filename)
                                shutil.copy(os.path.join(chemin_MNS, filename), chemin_image_local)

                                inputds = gdal.Open(chemin_image_local)

                                srs = osr.SpatialReference()
                                srs.ImportFromEPSG(EPSG)
                                inputds.SetProjection(srs.ExportToWkt())
                                

                                #Il faut que la dalle soit carré, sinon c'est qu'elle est incomplète
                                if inputds.RasterXSize == inputds.RasterYSize:
                                    trouve = True

                                    input_ds2 = gdal.Warp(os.path.join(args.metadata, "mns_temp", filename), inputds, dstSRS='EPSG:'+str(EPSG))

                                    #Les dalles de MNS sont un peu plus grande qu'un kilomètre de côté
                                    geotransform = inputds.GetGeoTransform()
                                    e_min_mns = geotransform[0]
                                    n_max_mns = geotransform[3]
                                    resolution = geotransform[1]
                                    save_hdr(filename.replace(".tif", ".hdr"), e_min_mns, n_max_mns, input_ds2.RasterXSize, input_ds2.RasterYSize, resolution)
                                    get_dalle_ortho(e_min, n_min, 2000 + int(chantier["annee"]), departement_tile, tile, EPSG)
                                else:
                                    os.remove(chemin_image_local)

                else:    
                
                    #On construit le nom du fichier que devrait avoir la tuile
                    chemin_MNS = os.path.join("/media", 'store-ref', "modeles-numeriques-3D", "MNS", chantier["repertoire"], "data", "MNS_CORREL_1-0", "dataset")
                    name = os.listdir(chemin_MNS)[0][:-4].split("_")
                    name[-2] = e_min
                    name[-1] = n_min
                    fichier = "_".join(name) + ".tif"
                    
                    #On regarde si la tuile existe bien
                    if os.path.exists(os.path.join(chemin_MNS, fichier)):
                        
                        chemin_image_local = os.path.join(args.metadata, "mns_temp2", fichier)
                        shutil.copy(os.path.join(chemin_MNS, fichier), chemin_image_local)

                        inputds = gdal.Open(chemin_image_local)
                        srs = osr.SpatialReference()
                        srs.ImportFromEPSG(EPSG)
                        inputds.SetProjection(srs.ExportToWkt())

                    
                        #Il faut que la dalle soit carré, sinon c'est qu'elle est incomplète
                        #Il est arrivé une fois que le geotransform de la dalle de MNS était faux
                        if inputds.RasterXSize == inputds.RasterYSize and inputds.GetGeoTransform()[0] != 0.0:
                            trouve = True   

                            # On reprojette les dalles dans le même EPSG que le chantier (en WGS84)
                            input_ds2 = gdal.Warp(os.path.join(args.metadata, "mns_temp", fichier), inputds, dstSRS='EPSG:'+str(EPSG))

                            #Les dalles de MNS sont un peu plus grande qu'un kilomètre de côté donc il faut recalculer les métadonnées à partir des informations du raster
                            geotransform = input_ds2.GetGeoTransform()
                            e_min_mns = geotransform[0]
                            n_max_mns = geotransform[3]
                            resolution = geotransform[1]
                            save_hdr(fichier.replace(".tif", ".hdr"), e_min_mns, n_max_mns, input_ds2.RasterXSize, input_ds2.RasterYSize, resolution)
                            get_dalle_ortho(e_min, n_min, 2000 + int(chantier["annee"]), departement_tile, tile, EPSG)
                        else:
                            os.remove(chemin_image_local)
            
        if not trouve:
            print("La dalle {} {} n'a pas été trouvée".format(e_min, n_min))


def save_tfw(name, e_min, n_max):
    with open(os.path.join(args.metadata, "ortho", name), 'w') as out:
        out.write("0.50\n")
        out.write("0.00\n")
        out.write("0.00\n")
        out.write("-0.50\n")
        out.write("{}\n".format(e_min))
        out.write("{}\n".format(n_max))


def get_dalle_ortho(e_min, n_min, annee, departement, tile, EPSG):
    if len(departement) <= 2:
        departement = "D0" + departement
    else:
        departement = "D" + departement


    dossier_departement = "BDORTHO_RVB-0M50_JP2-E100_{}_{}_{}".format(EPSG_NOM[str(EPSG)], departement, annee)
    chemin_ortho = os.path.join("/media", 'store-ref', "ortho-images", "Ortho", departement, str(annee), dossier_departement)

    if os.path.exists(chemin_ortho):
        exemple_fichier = os.listdir(chemin_ortho)[0][:-4].split("-")
        exemple_fichier[2] = e_min
        exemple_fichier[3] = str(int(n_min) +1)
        fichier = "-".join(exemple_fichier) + ".jp2"
        if os.path.exists(os.path.join(chemin_ortho, fichier)):

            chemin_image_local = os.path.join(args.metadata, "ortho_temp2", "ORTHO_{}.jp2".format(tile["properties"]["name"]))
            shutil.copy(os.path.join(chemin_ortho, fichier), chemin_image_local)
            inputds = gdal.Open(chemin_image_local)

            #Il faut que la dalle soit carré, sinon c'est qu'elle est incomplète
            if inputds.RasterXSize == inputds.RasterYSize:
                input_ds2 = gdal.Warp(os.path.join(args.metadata, "ortho_temp", "ORTHO_{}.jp2".format(tile["properties"]["name"])), inputds, dstSRS='EPSG:'+str(EPSG))
                geotransform = input_ds2.GetGeoTransform()
                e_min = geotransform[0]
                n_max = geotransform[3]

                save_tfw("ORTHO_{}.tfw".format(tile["properties"]["name"]), e_min+0.25, n_max-0.25)
            else:
                os.remove(chemin_image_local)
    else:
        print("Le répertoire {} n'existe pas".format(chemin_ortho))
        


if not os.path.exists(os.path.join(args.metadata, "ortho_temp")):
    os.makedirs(os.path.join(args.metadata, "ortho_temp"))

if not os.path.exists(os.path.join(args.metadata, "ortho_temp2")):
    os.makedirs(os.path.join(args.metadata, "ortho_temp2"))

if not os.path.exists(os.path.join(args.metadata, "ortho")):
    os.makedirs(os.path.join(args.metadata, "ortho"))

if not os.path.exists(os.path.join(args.metadata, "mns_temp")):
    os.makedirs(os.path.join(args.metadata, "mns_temp"))

if not os.path.exists(os.path.join(args.metadata, "mns_temp2")):
    os.makedirs(os.path.join(args.metadata, "mns_temp2"))

if not os.path.exists(os.path.join(args.metadata, "mns")):
    os.makedirs(os.path.join(args.metadata, "mns"))




#On récupère l'emprise du chantier, arrondie au kilomètre
bbox = load_bbox()

#On récupère l'EPSG du chantier
EPSG = getEPSG(args.metadata)

#On divise le chantier en dalles de 1 km de côté
emprise_tiles = get_emprise_tiles(bbox, EPSG)
emprise_tiles.to_file("emprise.shp")


#On récupère pour chaque département les années disponibles 
# Les départements d'Ile-de-France sont soit sous leur numéro de département soit avec la clef "IDF"
# Pour la Corse, ils sont sous la clef "2AB"
MNS_disponibles_chantiers = get_millesimes(emprise_tiles)


get_dalles(emprise_tiles, MNS_disponibles_chantiers, EPSG)

shutil.rmtree(os.path.join(args.metadata, "mns_temp2"))
shutil.rmtree(os.path.join(args.metadata, "ortho_temp2"))


# sudo mount -v -t cifs -o rw,user=CHuet2,domain=IGN,uid=23706,gid=10000 //store.ign.fr/store-ref/produits /media/store-ref