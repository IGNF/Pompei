import rasterio
import numpy as np
from rasterio import features
import geopandas as gpd
import argparse
from tqdm import tqdm
from scipy.interpolate import LinearNDInterpolator
from multiprocessing import Pool
import log # Chargement des configurations des logs
import logging
import os

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="Améliore le MNS, \
                                 notamment les défauts de corrélation en montagne qui donne un MNS avec des trous \
                                 de plusieurs centaines de mètres")

parser.add_argument('--mns_input', help="MNS à améliorer")
parser.add_argument('--indicateur', help="Indicateur")
parser.add_argument('--cpu', help="Nombre de cpus à utiliser", type=int)
args = parser.parse_args()


mns_input = args.mns_input
indicateur_path = args.indicateur
nb_cpus = args.cpu

def read_image(path, bounds=None):
    input_ds = rasterio.open(path)
    if bounds is None:
        array = input_ds.read().squeeze()
        bounds_return = input_ds.bounds
    else:
        transformer = rasterio.transform.AffineTransformer(transform)
        l_max, c_min = transformer.rowcol(bounds[0], bounds[1])
        l_min, c_max = transformer.rowcol(bounds[2], bounds[3])
        array = input_ds.read(window=rasterio.windows.Window(c_min, l_min, c_max-c_min+1, l_max-l_min+1)).squeeze()
        bounds_return = bounds
    return array, input_ds.transform, bounds_return


def vectorize_MNS(MNS, transform, indicateur):
    MNS = MNS//50
    MNS = MNS.astype(np.uint16)
    mask = indicateur!=0
    shapes = features.shapes(MNS, mask=mask, transform=transform)
    fc = ({"geometry": shape, "properties": {"value": value}} for shape, value in shapes)
    gdf = gpd.GeoDataFrame.from_features(fc)
    gdf = gdf.set_crs(2154)# TODO le CRS
    return gdf



def look_for_recompute(vectorisation, seuil=7000):
    """
    seuil : seuil sur la surface en m2 des segments qu'il faudra recalculer 
    """
    if "recompute" not in vectorisation.columns:
        vectorisation["recompute"] = 0
    sindex = vectorisation.sindex
    for index, segment in vectorisation.iterrows():
        object_geometry = segment.geometry
        if object_geometry.area <= seuil:            
            segment_value = segment.value
            recompute = True
            neighbors_id = sindex.query(object_geometry, predicate="intersects")
            neighbors_value = vectorisation.iloc[neighbors_id].value.to_list()
            if len(neighbors_value) == 0:
                recompute = False
            for value in neighbors_value:
                difference = abs(value-segment_value)
                if difference == 1:
                    recompute = False
            if recompute:
                vectorisation.at[index, "recompute"] = 1
    return vectorisation

def rasterize(vectorisation, shape, transform):
    geometries = vectorisation.geometry
    values = vectorisation.recompute

    list_segments = []
    for i in range(vectorisation.shape[0]):
        list_segments.append((geometries.iloc[i], values.iloc[i]))

    rasterized = features.rasterize(list_segments,
                                out_shape = shape,
                                fill = 0,
                                out = None,
                                transform = transform,
                                all_touched = False,
                                default_value = 1,
                                dtype = None)
    rasterized = (rasterized -1)*-1
    return rasterized


def poolProcess(work_data):
    ligne = work_data[0]
    ligne_1 = work_data[1]
    colonne = work_data[2]
    colonne_1 = work_data[3]
    MNS_ex = work_data[4]
    indicateur_ex = work_data[5]
    recompute_mns_ex = work_data[6]
    MNS_points_utile = indicateur_ex * recompute_mns_ex
    x_p_utiles, y_p_utiles = np.where(MNS_points_utile!=0)
    x_calcul, y_calcul = np.where(recompute_mns_ex==0)
    if x_p_utiles.shape[0]!=0 and x_calcul.shape[0]!=0:
        z_p_utiles = MNS_ex[x_p_utiles, y_p_utiles]
        interp = LinearNDInterpolator(list(zip(x_p_utiles, y_p_utiles)), z_p_utiles)
        z_calcul = interp(x_calcul, y_calcul)
        MNS_ex2 = np.copy(MNS_ex)
        MNS_ex2[x_calcul, y_calcul] = z_calcul
        MNS_ex = np.where(np.isnan(MNS_ex2), MNS_ex, MNS_ex2)
        return (ligne, ligne_1, colonne, colonne_1, MNS_ex)
    return (None, None, None, None, None)


def interpolate(MNS, indicateur, recompute_mns):
    n, m = MNS.shape
    tile_size = 500
    work_data = []
    for ligne in range(0, n, 480):
        for colonne in range(0, m, 480):
            ligne_1 = min(ligne+tile_size, n)
            colonne_1 = min(colonne+tile_size, m)
            MNS_ex = MNS[ligne:ligne_1, colonne:colonne_1]
            indicateur_ex = indicateur[ligne:ligne_1, colonne:colonne_1]
            recompute_mns_ex = recompute_mns[ligne:ligne_1, colonne:colonne_1]
            work_data.append([ligne, ligne_1, colonne, colonne_1, MNS_ex, indicateur_ex, recompute_mns_ex])
    
    with Pool(nb_cpus) as pool:
        for result in tqdm(pool.imap(poolProcess, work_data), total=len(work_data), desc="Interpolation : "):
            ligne = result[0]
            ligne_1 = result[1]
            colonne = result[2]
            colonne_1 = result[3]
            MNS_ex = result[4]
            if ligne is not None:
                MNS[ligne:ligne_1, colonne:colonne_1] = MNS_ex
    return MNS

def new_transform(transform, ligne, colonne):
    transformer = rasterio.transform.AffineTransformer(transform)
    x_new, y_new = transformer.xy(ligne, colonne)
    new_transform = rasterio.Affine(transform.a, transform.b, x_new, transform.d, transform.e, y_new)
    return new_transform


def get_rasterisation_pool(work_data):
    ligne = work_data[0]
    ligne_1 = work_data[1]
    colonne = work_data[2]
    colonne_1 = work_data[3]
    MNS_ex = work_data[4]
    indicateur_ex = work_data[5]
    transform_ex = work_data[6]

    # Si la dalle fait entièrement partie de la zone à ne pas calculer, on renvoie un tableau nul
    if np.all(indicateur_ex==0):
        return (ligne, ligne_1, colonne, colonne_1, np.zeros(MNS_ex.shape))
    
    # On vectorise le MNS après l'avoir divisé par 50 et converti en entiers    
    vectorisation = vectorize_MNS(MNS_ex, transform_ex, indicateur_ex)
    # On cherche les éléments de la vectorisation pour lesquels il faut recalculer le MNS par interpolation :
    # - la surface doit être inférieure à 7000 mètres carrés
    # - aucun voisin du segment ne doit être dans la tranche voisine de la vectorisation (altitude à +- 50 mètres)
    vectorisation = look_for_recompute(vectorisation)
    # On rasterise les segments : on obtient une carte qui pour chaque pixel indique s'il doit être recalculé ou non
    rasterization = rasterize(vectorisation, MNS_ex.shape, transform_ex)
    return (ligne, ligne_1, colonne, colonne_1, rasterization)
    



def get_rasterisation(MNS, transform, indicateur):
    """
    On parallélise le calcul sur des dalles de 2000 pixels de côté
    """
    n, m = MNS.shape
    tile_size = 2000
    work_data = []
    rasterisation = np.zeros(MNS.shape)
    for ligne in range(0, n, 1980):
        for colonne in range(0, m, 1980):
            ligne_1 = min(ligne+tile_size, n)
            colonne_1 = min(colonne+tile_size, m)
            MNS_ex = MNS[ligne:ligne_1, colonne:colonne_1]
            indicateur_ex = indicateur[ligne:ligne_1, colonne:colonne_1]
            transform_ex = new_transform(transform, ligne, colonne)
            work_data.append([ligne, ligne_1, colonne, colonne_1, MNS_ex, indicateur_ex, transform_ex])

    with Pool(nb_cpus) as pool:
        for result in tqdm(pool.imap(get_rasterisation_pool, work_data), total=len(work_data), desc="Rasterisation : "):
            ligne = result[0]
            ligne_1 = result[1]
            colonne = result[2]
            colonne_1 = result[3]
            rasterisation_ex = result[4]
            rasterisation[ligne:ligne_1, colonne:colonne_1] = rasterisation_ex
    return rasterisation

def resize(MNS, indicateur):
    """
    Redécoupe le mns et la carte de corrélation pour qu'elle ait la taille définie par c et l
    """
    l, c = MNS.shape
    indicateur = np.ones((l, c), dtype=np.uint8)
    l_current, c_current = indicateur.shape
    l_min = min(l, l_current)
    c_min = min(c, c_current)
    indicateur[:l_min,:c_min] = indicateur[:l_min,:c_min]
    return indicateur


if __name__=="__main__":
    MNS_files = [i for i in os.listdir("MEC-Malt-Final") if i[:12]=="MNS_pyramide" and i[-4:]==".tif"]
    for MNS_file in MNS_files:
        print(MNS_file)
        mns_input = os.path.join("MEC-Malt-Final", MNS_file)
        
        # Ouverture du MNS
        MNS, transform, bounds = read_image(mns_input)
        # Ouverture de la carte des indicateurs de la couche de la pyramide utilisée pour calculer le MNS
        indicateur, _, _ = read_image(indicateur_path, bounds=bounds)
        indicateur = resize(MNS, indicateur)

        # On récupère un raster qui indique les pixels qu'il faudra recalculer
        rasterization = get_rasterisation(MNS, transform, indicateur)
        logger.info("Rasterisation terminée")
        # Pour chaque pixel devant être recalculé, on le recalcule grâce à une interpolation sur les pixels n'ayant pas besoin d'être recalculés
        MNS_final = interpolate(MNS, indicateur,  rasterization)
        logger.info("Interpolation terminée")

        MNS_final = np.expand_dims(MNS_final, axis=0)
        mns_final_filename = MNS_file.replace("pyramide", "Final")
        dictionnaire = {
            'interleave': 'Band',
            'tiled': True
        }
        with rasterio.open(
            os.path.join("MEC-Malt-Final", mns_final_filename), "w",
            driver = "GTiff",
            transform = transform,
            dtype = rasterio.float32,
            count = MNS_final.shape[0],
            width = MNS_final.shape[2],
            height = MNS_final.shape[1],
            **dictionnaire) as dst:
            dst.write(MNS_final)

        rasterization = np.expand_dims(rasterization, axis=0)
        interpolation_filename = MNS_file.replace("MNS_pyramide", "carte_interpolation")
        with rasterio.open(
            os.path.join("MEC-Malt-Final", interpolation_filename), "w",
            driver = "GTiff",
            transform = transform,
            dtype = rasterio.uint8,
            count = rasterization.shape[0],
            width = rasterization.shape[2],
            height = rasterization.shape[1],
            **dictionnaire) as dst:
            dst.write(rasterization)
