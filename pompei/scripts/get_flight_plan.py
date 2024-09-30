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

parser = argparse.ArgumentParser(description="Récupère le plan de vol d'un chantier disponible sur la géoplateforme")
parser.add_argument('--footprints_file', help="Fichier avec les footprints au sol des chantiers")
parser.add_argument('--id', help="Fichier avec les footprints au sol des chantiers")
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



def get_images_metadata(bbox, outdir, id):
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
            if feature["properties"]["dataset_identifier"] == id:
                keep_features.append(feature)

        data0["features"] = keep_features
        
        with open(os.path.join(outdir, "images.geojson"), "w") as f:
            f.write(geojson.dumps(data0))

        return data0


footprints_file = args.footprints_file
id = args.id
outdir = args.outdir

os.makedirs(outdir, exist_ok=True)

bbox = get_bbox(footprints_file, id)
images_metadata = get_images_metadata(bbox, outdir, id)