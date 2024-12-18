import geopandas as gpd
import os
import logging
import shutil
from lxml import etree
from shapely import Polygon, intersects, Point
import numpy as np


logging.basicConfig(filename='pompei/main.log', level=logging.INFO, format='%(asctime)s : %(levelname)s : %(module)s : %(message)s')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)
logger = logging.getLogger(__name__)


def download_images(row):
    
    chantier = row.chantier
    emprise = row.geometry
    annee = row.annees
    logger.info(f"Traitement de {row.zone}")

    path_chantier_misphot = os.path.join(misphot_path, annee, chantier)
    if os.path.isdir(path_chantier_misphot):
        xml_file = [i for i in os.listdir(path_chantier_misphot) if i[-4:]==".xml" and not "archive" in i]
        if len(xml_file)==1:
            xml_file = xml_file[0]
            xml_path = os.path.join(path_chantier_misphot, xml_file)
        else:
            logger.warning(f"Problème sur le fichier xml : {xml_file}")
            return None
    else:
        logger.warning(f"Le répertoire {path_chantier_misphot} n'a pas été trouvé")
        return None

    path_chantier_pompei = os.path.join("Pompei", "pompei", "chantiers", row.zone)

    if os.path.isdir(path_chantier_pompei):
        shutil.rmtree(path_chantier_pompei)
    os.makedirs(path_chantier_pompei, exist_ok=True)
    path_xml_pompei = os.path.join(path_chantier_pompei, xml_file).replace(" ", "_")
    shutil.copy(xml_path, path_xml_pompei)
    logger.info(f"Le fichier xml de {chantier} a été trouvé")
    return [os.path.abspath(path_chantier_pompei), os.path.abspath(path_xml_pompei), path_chantier_misphot]


def load_xml(selection_row, xml_path, path_chantier_misphot, path_chantier_pompei):
    geometry = selection_row.geometry
    root = etree.parse(xml_path)
    cliches = root.findall(".//cliche")
    compte = 0
    for cliche in cliches:
        image = cliche.find(".//image").text.strip()
        polygon2d = cliche.find(".//polygon2d")
        x_balises = polygon2d.findall(".//x")
        y_balises = polygon2d.findall(".//y")
        x = [i.text for i in x_balises]
        y = [i.text for i in y_balises]
        coords = [[x[i], y[i]] for i in range(len(x))]
        polygon = Polygon(coords)
        if intersects(polygon, geometry):
            image_path = os.path.join(path_chantier_misphot, image+".jp2")
            if os.path.isfile(image_path):
                shutil.copy(image_path, path_chantier_pompei)
                compte += 1
    logger.info(f"Chantier {selection_row.zone} : {compte} images")


def get_force_verticale(xml_path, path_chantier):
    images = [i for i in os.listdir(path_chantier) if i[-4:]==".jp2"]
    root = etree.parse(xml_path)
    cliches = root.findall(".//cliche")
    points = []
    for cliche in cliches:
        image = cliche.find(".//image").text.strip()
        if image+".jp2" in images:
            model = cliche.find(".//model")
            x = float(model.find(".//x").text)
            y = float(model.find(".//y").text)
            z = float(model.find(".//z").text)
            points.append(Point(x, y, z))
    if len(points)<=2:
        return 1
    p0 = points[0]
    p1 = points[1]
    u = np.array([p1.x-p0.x, p1.y-p0.y, p1.z-p0.z])
    norm_u = np.linalg.norm(u)
    for i in range(2, len(points)):
        p2 = points[i]
        m = np.array([p2.x-p0.x, p2.y-p0.y, p2.z-p0.z])
        dist = np.linalg.norm(np.cross(u, m)) / norm_u
        if dist > 500:
            return 0
    return 1


def run_chantier(chantier_name, path_chantier_pompei):
    xml_file = [i for i in os.listdir(os.path.join("pompei", path_chantier_pompei)) if i[-4:]==".xml" and i[:2]=="19"]
    if len(xml_file)==1:
        path_xml_pompei = os.path.join(path_chantier_pompei, xml_file[0])
        logger.info(f"Début du calcul")
        os.system(f"cd pompei; sh scripts/aero_tmp.sh 1 a 130 storeref {path_xml_pompei}")
        
        result_dir = os.path.join("pompei", "chantiers", "resultats", chantier_name)
        os.makedirs(result_dir, exist_ok=True)
        path_chantier_pompei = os.path.join("pompei", path_chantier_pompei)
        if os.path.isfile(os.path.join(path_chantier_pompei, "pompei_debug.log")):
            shutil.copy(os.path.join(path_chantier_pompei, "pompei_debug.log"), result_dir)
        if os.path.isdir(os.path.join(path_chantier_pompei, "ortho_mnt")):
            shutil.copytree(os.path.join(path_chantier_pompei, "ortho_mnt"), os.path.join(result_dir, "ortho_mnt"), dirs_exist_ok=True)
        if os.path.isdir(os.path.join(path_chantier_pompei, "ortho_mns")):
            shutil.copytree(os.path.join(path_chantier_pompei, "ortho_mns"), os.path.join(result_dir, "ortho_mns"), dirs_exist_ok=True)
        if os.path.isdir(os.path.join(path_chantier_pompei, "reports")):
            shutil.copytree(os.path.join(path_chantier_pompei, "reports"), os.path.join(result_dir, "reports"), dirs_exist_ok=True)
        with open(path_chantiers_done, "a") as f:
            f.write(f"{chantier_name}\n")


def load_failed():
    chantiers_failed = []
    with open(path_chantiers_failed, "r") as f:
        for line in f:
            chantiers_failed.append(line.strip())
    print(f"Nombre de chantiers ratés : {len(chantiers_failed)}")
    return chantiers_failed

misphot_path = os.path.join("/media", "misphot", "Lambert93")
misphot_path = "/run/user/23706/gvfs/smb-share:server=dgs1209n015,share=misphot_image_15/Lambert93"

path_chantiers_failed = os.path.join("pompei", "chantiers", "failed.txt")
path_chantiers_done = os.path.join("pompei", "chantiers", "failed_done.txt")
chantiers_failed = load_failed()

chantiers_list = os.listdir(os.path.join("pompei", "chantiers"))
for chantier_name in chantiers_list:
    if chantier_name in chantiers_failed:
        print(chantier_name)
        run_chantier(chantier_name, os.path.join("chantiers", chantier_name))
