import geopandas as gpd
import os
import logging
import shutil
from lxml import etree
from shapely import Polygon, intersects


logging.basicConfig(filename='main.log', level=logging.INFO, format='%(asctime)s : %(levelname)s : %(module)s : %(message)s')
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


def run_chantier(chantier_name, path_chantier_pompei):
    xml_file = [i for i in os.listdir(path_chantier_pompei) if i[-4:]==".xml"]
    if len(xml_file)==1:
        path_xml_pompei = os.path.join(path_chantier_pompei, xml_file[0])
        logger.info(f"Début du calcul")
        os.system(f"cd Pompei/pompei; sh visualize_flight_plan.sh {path_xml_pompei} ; sh pompei_rapide.sh {path_xml_pompei} 4 1 0 0 storeref 12")
        
        result_dir = os.path.join("pompei", "chantiers", "resultats", chantier_name)
        os.makedirs(result_dir, exists_ok=True)
        shutil.copytree(os.path.join(path_chantier_pompei, "ortho_mnt"), result_dir)
        shutil.copytree(os.path.join(path_chantier_pompei, "reports"), result_dir)
        shutil.rmtree(path_chantier_pompei)
        with open(path_chantiers_done, "a") as f:
            f.write(f"{chantier_name}\n")


def load_done():
    chantiers_done = []
    with open(path_chantiers_done, "r") as f:
        for line in f:
            chantiers_done.append(line.strip())
    print(f"Nombre de chantiers déjà effectués : {len(chantiers_done)}")
    return chantiers_done

misphot_path = os.path.join("/media", "misphot", "Lambert93")
misphot_path = "/run/user/23706/gvfs/smb-share:server=dgs1209n015,share=misphot_image_15/Lambert93"
selection_path = "selection.gpkg"
selection_gdf = gpd.read_file(selection_path)

path_chantiers_done = os.path.join("pompei", "chantiers", "done.txt")
chantiers_done = load_done()

chantiers_list = os.listdir(os.path.join("pompei", "chantiers"))
for chantier_name in chantiers_list:
    if chantier_name not in chantiers_done:
        run_chantier(chantier_name, os.path.join("pompei", "chantiers", chantier_name))

for selection_id in range(selection_gdf.shape[0]):
    selection_row = selection_gdf.iloc[selection_id]
    if selection_row.zone not in chantiers_done:
        result = download_images(selection_row)
        if result is not None:
            path_chantier_pompei, path_xml_pompei, path_chantier_misphot = result
            load_xml(selection_row, path_xml_pompei, path_chantier_misphot, path_chantier_pompei)
            run_chantier(selection_row, path_chantier_pompei, path_xml_pompei)