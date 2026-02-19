import argparse
from pathlib import Path
from tools import getEPSG, getNbCouleurs, getResolution, read_ori
import rasterio
import os
from equations import Shot, DistorsionCorrection
import numpy as np
from scipy import ndimage
from tqdm import tqdm
from lxml import etree
from scipy.spatial.transform import Rotation as R

parser = argparse.ArgumentParser(description="Correction de la distorsion sur les images OIS-Reech")
parser.add_argument('--ori', help='Répertoire avec les orientations du chantier')
parser.add_argument('--ta', help='Fichier TA du chantier')
args = parser.parse_args()

ori_path = Path(args.ori)
ta_path = Path(args.ta)
output_dir = Path("images_without_distorsion")
os.makedirs(output_dir, exist_ok=True)


def correct_distorsion(shot:Shot):
    array_OIS = rasterio.open(shot.imagePath).read()

    _, i_max, j_max = array_OIS.shape

    image_corrected = np.zeros(array_OIS.shape)

    dc = DistorsionCorrection(shot.calibration)

    pas = 100
    for i0 in range(0, i_max, pas):
        i1 = min(i_max, i0+pas)
        for j0 in range(0, j_max, pas):
            j1 = min(j_max, j0+pas)
            
            c = np.arange(np.min(j0), np.max(j1))
            l = np.arange(np.min(i0), np.max(i1))

            cc, ll = np.meshgrid(c, l)
            cc = cc.reshape((-1, 1))
            ll = ll.reshape((-1, 1))
            c_corr, l_corr = dc.compute(cc, ll)
            c_corr = c_corr.reshape((1, -1))
            l_corr = l_corr.reshape((1, -1))
            
            min_c = int(np.floor(np.min(c_corr)))
            max_c = int(np.ceil(np.max(c_corr)))
            min_l = int(np.floor(np.min(l_corr)))
            max_l = int(np.ceil(np.max(l_corr)))

            # Coordonnées pour lire une partie de l'image même si dans l'idéal on a besoin d'une partie en-dehors de l'image
            min_c_read = max(0, min_c)
            max_c_read = min(j_max-1, max_c)
            min_l_read = max(0, min_l)
            max_l_read = min(i_max-1, max_l)



            if min_l > i_max or min_c > j_max or max_l < 0 or max_c < 0:
                finalImage = None
            # Si on veut une image trop grande, on renvoie None par sécurité
            elif max_l-min_l+1 > 30000 or max_c-min_c+1 > 30000:
                finalImage = None
            else:
                image = array_OIS[:,min_l_read:max_l_read+1, min_c_read:max_c_read+1]
                image = image.reshape((nbCouleurs, max_l_read-min_l_read+1, max_c_read-min_c_read+1))
                
                finalImage = np.zeros((nbCouleurs, max_l-min_l+1, max_c-min_c+1), dtype=np.uint8)
                finalImage[:,min_l_read-min_l:max_l_read-min_l+1, min_c_read-min_c:max_c_read-min_c+1] = image
            
            for i in range(nbCouleurs):
                value_band = ndimage.map_coordinates(image[i], np.vstack([l_corr-min_l, c_corr-min_c])).reshape((1, l.shape[0], c.shape[0]))
                image_corrected[i, i0:i1, j0:j1] = value_band


    save_image(image_corrected, output_dir/shot.imagePath, np.uint8)

def save_image(image, path, encoding):
    dictionnaire = {
            'interleave': 'Band',
            'tiled': True
        }
    with rasterio.open(
        path, "w",
        driver = "GTiff",
        dtype = encoding,
        count = image.shape[0],
        width = image.shape[2],
        height = image.shape[1],
        **dictionnaire) as dst:
        dst.write(image)

def get_shot(shots, image_name):
    for shot in shots:
        if shot.nom==f"OIS-Reech_{image_name.strip()}":
            return shot
        

def mat_eucli_to_quaternion(mat_eucli: np.array) -> np.array:
    """
    Transform rotation matrix (TOPAERO convention) into quaternions
    :param mat_eucli: quaternion
    :return: quaternion
    """
    # Passage en convention classique
    # Transposition + inversion des deux premières colonnes
    mat = mat_eucli[:, [1, 0, 2]]
    # axe Z dans l'autre sens donc *-1 sur la dernière colonne
    mat = mat*np.array([1, 1, -1])
    q = -R.from_matrix(mat).as_quat()
    return q

#On récupère l'EPSG du chantier
EPSG = getEPSG("metadata")

resolution = getResolution()
nbCouleurs = getNbCouleurs("metadata")

# On crée un objet shot par image
shots = read_ori(ori_path, ta_path, EPSG)

for shot in tqdm(shots):
    correct_distorsion(shot)

tree = etree.parse(ta_path)
root = tree.getroot()
vols = root.findall(".//vol")
for vol in vols:
    cliches = vol.findall(".//cliche")
    for cliche in cliches:
        image = cliche.find(".//image")
        shot = get_shot(shots, image.text)
        if shot is None:
            continue
        shot_valid = shot
        model = cliche.find(".//model")

        image.text = shot.nom
        
        x = model.find(".//x")
        x.text = str(shot.x_pos)
        y = model.find(".//y")
        y.text = str(shot.y_pos)
        z = model.find(".//z")
        z.text = str(shot.z_pos)

        quaternions = mat_eucli_to_quaternion(shot.mat_eucli)
        
        quat_balise = cliche.find(".//quaternion")
        w = quat_balise.find(".//w")
        x = quat_balise.find(".//x")
        y = quat_balise.find(".//y")
        z = quat_balise.find(".//z")

        x.text = str(quaternions[0])
        y.text = str(quaternions[1])
        z.text = str(quaternions[2])
        w.text = str(quaternions[3])

    focal = vol.find(".//focal")
    x = focal.find(".//x")
    x.text = str(shot_valid.x_ppa)
    y = focal.find(".//y")
    y.text = str(shot_valid.y_ppa)
    z = focal.find(".//z")
    z.text = str(shot_valid.focal)

    usefull_frame = vol.find(".//usefull-frame")
    width = usefull_frame.find(".//w")
    height = usefull_frame.find(".//h")
    width.text = str(shot_valid.X_size)
    height.text = str(shot_valid.Y_size)

with open(os.path.join(output_dir, "ta_corrected.xml"), "w") as f:
		f.write(str(etree.tostring(root,encoding='unicode')))


