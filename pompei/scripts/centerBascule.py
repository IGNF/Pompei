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

import argparse
import os
import log # Chargement des configurations des logs
import logging
from lxml import etree
import numpy as np
from shapely import Point

logger = logging.getLogger()


parser = argparse.ArgumentParser(description="On applique CenterBascule pour passer d'une ortiantation relative en une orientation absolue")
parser.add_argument('--ta_xml', help="Tableau d'assemblage sous format xml")
args = parser.parse_args()

xml_path = args.ta_xml

def get_force_verticale(xml_path):
    images = [i for i in os.listdir() if i[:9]=="OIS-Reech" and i[-4:]==".tif"]
    root = etree.parse(xml_path)
    cliches = root.findall(".//cliche")
    points = []
    for cliche in cliches:
        image = cliche.find(".//image").text.strip()
        if f"OIS-Reech_{image}.tif" in images:
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


force_verticale = get_force_verticale(xml_path)
if force_verticale:
    logger.info("Les images sont alignées, donc on force la verticale dans le passage à l'orientation absolue approchée")
    cmd = 'mm3d CenterBascule "OIS-Reech_.*tif" Rel Nav Abs L1=true ForceVert=1000000 | tee reports/report_CenterBascule.txt >> logfile'
else:
    cmd = 'mm3d CenterBascule "OIS-Reech_.*tif" Rel Nav Abs L1=true | tee reports/report_CenterBascule.txt >> logfile'
os.system(cmd)