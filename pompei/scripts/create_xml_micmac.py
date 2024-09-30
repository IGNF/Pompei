#Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/
#
#File main authors:
#- Célestin Huet
#This file is part of Pompei: https://github.com/IGNF/Pompei
#
#Pompei is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#Pompei is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#You should have received a copy of the GNU General Public License along with Pompei. If not, see <https://www.gnu.org/licenses/>.

import rasterio
from lxml import etree
import argparse

parser = argparse.ArgumentParser(description="Crée les métadonnées d'une image tif sous format xml pour être exploité par Micmac")
parser.add_argument('--tif_image', help='Image tif')
parser.add_argument('--xml_file', help='Fichier xml à créer')
args = parser.parse_args()

def create_xml(tif_image, xml_file):
    dst = rasterio.open(tif_image)
    transform = dst.transform

    fileOriMnt = etree.Element("FileOriMnt")
    
    nameFileMnt = etree.SubElement(fileOriMnt, "NameFileMnt")
    nameFileMnt.text = "MNS.tif"

    nombrePixels = etree.SubElement(fileOriMnt, "NombrePixels")
    nombrePixels.text = "{} {}".format(dst.width, dst.height)

    originePlani = etree.SubElement(fileOriMnt, "OriginePlani")
    originePlani.text = "{} {}".format(transform.c, transform.f)

    resolutionPlani = etree.SubElement(fileOriMnt, "ResolutionPlani")
    resolutionPlani.text = "{} {}".format(transform.a, transform.e)

    origineAlti = etree.SubElement(fileOriMnt, "OrigineAlti")
    origineAlti.text = "0"

    resolutionAlti = etree.SubElement(fileOriMnt, "ResolutionAlti")
    resolutionAlti.text = "1"

    geometrie = etree.SubElement(fileOriMnt, "Geometrie")
    geometrie.text = "eGeomMNTEuclid"

    with open(xml_file, "w") as f:
        f.write(str(etree.tostring(fileOriMnt,encoding='unicode')))


create_xml(args.tif_image, args.xml_file)
