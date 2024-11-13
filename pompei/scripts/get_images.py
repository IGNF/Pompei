"""
Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/

File main authors:
- Célestin Huet

This file is part of Pompei: https://github.com/IGNF/Pompei

Pompei is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Pompei is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Pompei. If not, see <https://www.gnu.org/licenses/>.
"""

import requests
import json
import geojson
import argparse
import os
from shapely import Polygon
from osgeo import gdal
from lxml import etree
from pyproj import CRS, Transformer
import geopandas as gpd
from tqdm import tqdm

parser = argparse.ArgumentParser(description="Récupère les footprints au sol des chantiers disponibles sur la géoplateforme")
parser.add_argument('--selection', help="Fichier avec les footprints au sol des chantiers")
parser.add_argument('--id', help="Fichier avec les footprints au sol des chantiers")
parser.add_argument('--epsg', help="EPSG du chantier")
parser.add_argument('--outdir', help="Répertoire où préparer le chantier")
args = parser.parse_args()


def get_bbox(footprints_file, id):
    with open(footprints_file, "r") as f:
        footprints = json.loads(f.read())
    
    for feature in footprints["features"]:
        if feature["id"] == "dataset."+id:
            bbox = feature["bbox"]
            bbox_polygon = Polygon([[bbox[0], bbox[1]], [bbox[0], bbox[3]], [bbox[2], bbox[3]], [bbox[2], bbox[1]], [bbox[0], bbox[1]]])
            return bbox_polygon

    raise ValueError("Aucun chantier avec l'identifiant {} n'a été trouvé".format(id))


def load_selection_file(selection):
    gdf = gpd.read_file(selection)
    bbox = gdf.total_bounds
    bbox_polygon = Polygon([[bbox[0], bbox[1]], [bbox[0], bbox[3]], [bbox[2], bbox[3]], [bbox[2], bbox[1]], [bbox[0], bbox[1]]])

    selected_images = list(gdf["id"])
    selected_images = [i.replace("image.", "") for i in selected_images]

    return bbox_polygon, selected_images
    


def get_images_metadata(bbox, id, selected_images):
    url = "https://data.geopf.fr/wfs?service=WFS&version=2.0.0&typeName=pva:image&request=GetFeature&outputFormat=json&cql_filter=INTERSECTS(geom,{})".format(bbox)

    r = requests.get(url)
    if r.status_code==200:
        data = json.loads(r.text)

        data0 = json.loads(r.text)
        nb_features = data0["totalFeatures"]

        for i in range(5000, nb_features, 5000):
            url = "https://data.geopf.fr/wfs?service=WFS&version=2.0.0&typeName=pva:image&request=GetFeature&outputFormat=json&cql_filter=INTERSECTS(geom,{})&startIndex={}".format(bbox, i)

            r = requests.get(url)
            if r.status_code==200:
                data = json.loads(r.text)
                data0["features"] += data["features"]


        keep_features = []
        for feature in data0["features"]:
            if feature["properties"]["dataset_identifier"] == id and feature["properties"]["image_identifier"] in selected_images:
                keep_features.append(feature)

        data0["features"] = keep_features

        return data0


def download_images(images_metadata, id, outdir):
    for feature in tqdm(images_metadata["features"]):
        image_id = feature["id"][6:]

        url = "https://data.geopf.fr/telechargement/download/pva/{}/{}.tif".format(id, image_id)


        r = requests.get(url)
        if r.status_code == 200:
            with open(os.path.join(outdir, image_id+"_temp.tif"), 'wb') as out:
                out.write(bytes(r.content))

        ds = gdal.Open(os.path.join(outdir, image_id+"_temp.tif"))
        ds = gdal.Translate(os.path.join(outdir, image_id+".tif"), ds)
        os.remove(os.path.join(outdir, image_id+"_temp.tif"))


def get_projection_name(epsg):
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

    for key in dictionnaire.keys():
        if dictionnaire[key]==epsg:
            return key
    raise ValueError("L'EPSG du chantier n'est pas reconnu. Il doit être parmi : {}".format(dictionnaire.values()))


def create_xml_file(images_metadata, outdir, epsg):
    crsWMS = CRS.from_epsg(3857)
    crsChantier = CRS.from_epsg(epsg)
    transformer = Transformer.from_crs(crsWMS, crsChantier)
    root = etree.Element("TA")
    projection = etree.SubElement(root, "projection")
    projection.text = get_projection_name(epsg)
    vol = etree.SubElement(root, "vol")
    for feature in images_metadata["features"]:
        cliche = etree.SubElement(vol, "cliche")
        image = etree.SubElement(cliche, "image")
        image.text = feature["id"][6:]
        model = etree.SubElement(cliche, "model")
        pt3d = etree.SubElement(model, "pt3d")
        x_L93, y_L93 = transformer.transform(feature["properties"]["x"], feature["properties"]["y"])
        x = etree.SubElement(pt3d, "x")
        x.text = str(x_L93)
        y = etree.SubElement(pt3d, "y")
        y.text = str(y_L93)
        z = etree.SubElement(pt3d, "z")
        z.text = "5200"


        quaternion = etree.SubElement(model, "quaternion")
        x = etree.SubElement(quaternion, "x")
        x.text = "0"
        y = etree.SubElement(quaternion, "y")
        y.text = "0"
        z = etree.SubElement(quaternion, "z")
        z.text = "0"
        w = etree.SubElement(quaternion, "w")
        w.text = "0"


        polygon2d = etree.SubElement(cliche, "polygon2d")

        for point in feature["geometry"]["coordinates"][0]:
            x_L93, y_L93 = transformer.transform(point[0], point[1])
            x = etree.SubElement(polygon2d, "x")
            x.text = str(x_L93)
            y = etree.SubElement(polygon2d, "y")
            y.text = str(y_L93)



    sensor = etree.SubElement(vol, "sensor")
    

    images = [i for i in os.listdir(outdir) if i[-4:]==".tif"]
    inputds = gdal.Open(os.path.join(outdir, images[0]))

    rect = etree.SubElement(sensor, "rect")
    x = etree.SubElement(rect, "x")
    x.text = "0"
    y = etree.SubElement(rect, "y")
    y.text = "0"
    h = etree.SubElement(rect, "h")
    h.text = str(int(inputds.RasterYSize * 0.021))
    w = etree.SubElement(rect, "w")
    w.text = str(int(inputds.RasterXSize * 0.021))
    
    
    
    focal = etree.SubElement(sensor, "focal")
    pt3d = etree.SubElement(focal, "pt3d")
    x = etree.SubElement(pt3d, "x")
    x.text = str(int(inputds.RasterXSize * 0.021 / 2))
    y = etree.SubElement(pt3d, "y")
    y.text = str(int(inputds.RasterYSize * 0.021 / 2))
    z = etree.SubElement(pt3d, "z")
    z.text = "152"

    pixel_size = etree.SubElement(sensor, "pixel_size")
    pixel_size.text = "0.0010000"

    with open(os.path.join(outdir, "ta.xml"), "w") as f:
        f.write(str(etree.tostring(root, encoding='unicode')))

    




selection = args.selection
id = args.id
epsg = int(args.epsg)
outdir = args.outdir

os.makedirs(outdir, exist_ok=True)

bbox, selected_images = load_selection_file(selection)

images_metadata = get_images_metadata(bbox, id, selected_images)

download_images(images_metadata, id, outdir)

create_xml_file(images_metadata, outdir, epsg)