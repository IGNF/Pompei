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
from lxml import etree
import os
from shapely import Point
import numpy as np
from osgeo import gdal
from scipy import ndimage
from scipy.spatial.transform import Rotation as R

parser = argparse.ArgumentParser(description="Crée un nouveau fichier TA avec les valeurs déterminées pendant le chantier (orientation, position...)")

parser.add_argument('--ta_xml', help="Fichier TA")
parser.add_argument('--ori', help="Répertoire contenant les fichiers orientations")
parser.add_argument('--imagesSave', help="Répertoire où sauvegarder les images")
parser.add_argument('--result', help="Fichier TA en sortie")
args = parser.parse_args()

ta_xml_path = args.ta_xml
ori_path = args.ori
result_path = args.result
imagesSave_path = args.imagesSave



class Calibration:
    def __init__(self) -> None:
        pass

    
    @staticmethod
    def createCalibration(path):
        tree = etree.parse(path)
        root = tree.getroot()
        calibration = Calibration()
        calibration.setPP(root)
        calibration.setFocale(root)
        calibration.setSizeImage(root)
        calibration.setDistorsionCoeff(root)
        calibration.setDecentric(root)
        calibration.setAffine(root)
        return calibration

    def setPP(self, root):
        PP = root.find(".//PP").text
        self.PPX = float(PP.split()[0])
        self.PPY = float(PP.split()[1])

    def setFocale(self, root):
        focale = root.find(".//F").text
        self.focale = float(focale)

    def setSizeImage(self, root):
        sizeImage = root.find(".//SzIm").text
        self.sizeX = int(sizeImage.split()[0])
        self.sizeY = int(sizeImage.split()[1])

    def setDistorsionCoeff(self, root):
        distorsionCoefficient = []
        for coeffDist in root.getiterator("CoeffDist"):
            distorsionCoefficient.append(float(coeffDist.text))
        self.distorsionCoefficient = distorsionCoefficient

    def setDecentric(self, root):
        self.decentric_P1 = float(root.find(".//P1").text)
        self.decentric_P2 = float(root.find(".//P2").text)

    def setAffine(self, root):
        self.affine_b1 = float(root.find(".//b1").text)
        self.affine_b2 = float(root.find(".//b2").text)

    def changeFocale(self, sensor):
        pixel_size = 0.021
        sensor.find(".//pixel_size").text = str(pixel_size)
        pt3d = sensor.find((".//pt3d"))
        x = pt3d.find(".//x")
        y = pt3d.find(".//y")
        z = pt3d.find(".//z")
        x.text = str(self.PPX*pixel_size)
        y.text = str(self.PPY*pixel_size)
        z.text = str(self.focale*pixel_size)
        
    

class Orientation:

    def __init__(self) -> None:
        pass

    @staticmethod
    def createOrientation(path, image):
        tree = etree.parse(path)
        root = tree.getroot()
        orientation = Orientation()
        orientation.image = image[:-4]
        orientation.setCentre(root)
        orientation.setMatrice(root)
        return orientation

    def setCentre(self, root):
        centre = root.find(".//Centre").text
        self.centre = Point(float(centre.split()[0]), float(centre.split()[1]), float(centre.split()[2]))

    def setMatrice(self, root):
        rotMatrice = np.zeros((3,3))
        L1 = root.find(".//L1").text
        rotMatrice[0,0] = float(L1.split()[0])
        rotMatrice[0,1] = float(L1.split()[1])
        rotMatrice[0,2] = float(L1.split()[2])
        L2 = root.find(".//L2").text
        rotMatrice[1,0] = float(L2.split()[0])
        rotMatrice[1,1] = float(L2.split()[1])
        rotMatrice[1,2] = float(L2.split()[2])
        L3 = root.find(".//L3").text
        rotMatrice[2,0] = float(L3.split()[0])
        rotMatrice[2,1] = float(L3.split()[1])
        rotMatrice[2,2] = float(L3.split()[2])
        self.rotMatrice = rotMatrice

    def changePt3d(self, cliche):
        pt3d = cliche.find(".//pt3d")
        x = pt3d.find(".//x")
        y = pt3d.find(".//y")
        z = pt3d.find(".//z")
        x.text = str(self.centre.x)
        y.text = str(self.centre.y)
        z.text = str(self.centre.z)

    def mat_eucli_to_quaternion(self, mat_eucli: np.array) -> np.array:
        """
        Transform rotation matrix (TOPAERO convention) into quaternions

        :param mat_eucli: quaternion

        :return: quaternion
        """
        # Passage en convention classique
        # Transposition + inversion des deux premières colonnes
        mat = mat_eucli.T[:, [1, 0, 2]]
        # axe Z dans l'autre sens donc *-1 sur la dernière colonne
        mat = mat*np.array([1, 1, -1])
        q = R.from_matrix(mat).as_quat()
        return q

    def changeQuaternion(self, cliche):
        quaternion = cliche.find(".//quaternion")
        
        w = quaternion.find(".//w")
        x = quaternion.find(".//x")
        y = quaternion.find(".//y")
        z = quaternion.find(".//z")

        quaternion = self.mat_eucli_to_quaternion(self.rotMatrice)
        x.text = str(quaternion[0])
        y.text = str(quaternion[1])
        z.text = str(quaternion[2])
        w.text = str(quaternion[3])
        
        



class DistorsionCorrection:

    def __init__(self, image_path, calibration:Calibration) -> None:
        self.image_path = image_path
        self.calibration = calibration

    def openImage(self):
        inputds = gdal.Open(self.image_path)
        self.image = inputds.ReadAsArray()

    def create_cc_ll(self):
        l = np.arange(calibration.sizeX)
        c = np.arange(calibration.sizeY)
        self.cc, self.ll = np.meshgrid(l, c)
        self.du = self.cc - calibration.PPX
        self.dv = self.ll - calibration.PPY
        self.rho = self.du**2 + self.dv**2
    
    def compute_Dr(self):

        intermediaire = (1+calibration.distorsionCoefficient[0]*self.rho+calibration.distorsionCoefficient[1]*self.rho**2+calibration.distorsionCoefficient[2]*self.rho**3+calibration.distorsionCoefficient[3]*self.rho**4)
        self.drx = calibration.PPX + intermediaire * self.du
        self.dry = calibration.PPY + intermediaire * self.dv
        
    def computeDecentric(self):
        P1x = calibration.decentric_P1 * (2*self.du**2 + self.rho)
        P1y = calibration.decentric_P1 * 2*self.du *self.dv
        P2x = calibration.decentric_P2 * 2*self.du *self.dv
        P2y = calibration.decentric_P2 * (2*self.dv**2 + self.rho)
        self.decentricx = P1x + P2x
        self.decentricy = P1y + P2y
        
    def computeAffine(self):
        self.affine = calibration.affine_b1 * self.du + calibration.affine_b2 * self.dv

    def computeAll(self):
        self.DPx = self.drx + self.decentricx + self.affine
        self.DPy = self.dry + self.decentricy

    def compute_new_image(self):
        n, m = self.DPx.shape
        dpx_reshape = self.DPx.reshape((-1))
        dpy_reshape = self.DPy.reshape((-1))
        imageWithoutDistorsion = ndimage.map_coordinates(self.image, np.vstack([dpy_reshape, dpx_reshape]))
        self.imageWithoutDistorsion = imageWithoutDistorsion.reshape((n, m))

    def saveImage(self, path):
        n, m = self.imageWithoutDistorsion.shape
        driver = gdal.GetDriverByName('GTiff')
        outRaster = driver.Create(path, m, n, 1, gdal.GDT_Byte)
        outband = outRaster.GetRasterBand(1)
        outband.WriteArray(self.imageWithoutDistorsion)

        

def open_ta(ta_xml_path):
    tree = etree.parse(ta_xml_path)
    return tree

def getCalibrationFile(path):
    files = os.listdir(path)
    for file in files:
        if file[:11] == "AutoCal_Foc":
            return os.path.join(path, file)
    raise Exception("No calibration file in {}".format(path))

def createOrientation(path):
    files = [i for i in os.listdir(path) if i[:11] == "Orientation"]
    orientations = []
    for file in files:
        orientations.append(Orientation.createOrientation(os.path.join(path, file), file))
    return orientations

def transformImages(path_in, path_out, calibration):
    os.makedirs(path_out, exist_ok=True)
    images = [i for i in os.listdir(path_in) if i[-4:]==".tif" and i[:9]=="OIS-Reech"]
    for image in images:
        dc = DistorsionCorrection(os.path.join(path_in, image), calibration)
        dc.openImage()
        dc.create_cc_ll()
        dc.compute_Dr()
        dc.computeDecentric()
        dc.computeAffine()
        dc.computeAll()
        dc.compute_new_image()
        dc.saveImage(os.path.join(path_out, image))


def get_image(orientations, image)->Orientation:
    for orientation in orientations:
        if orientation.image == "Orientation-OIS-Reech_{}.tif".format(image):
            return orientation
    return None


def complete_TA(ta_xml, calibration, orientations):
    root = ta_xml.getroot()
    for cliche in root.getiterator("cliche"):
        image = cliche.find("image").text.strip()
        orientation = get_image(orientations, image)
        if orientation is not None:
            orientation.changePt3d(cliche)
            orientation.changeQuaternion(cliche)

    sensor = root.find(".//sensor")
    calibration.changeFocale(sensor)





def save_TA(ta_xml, result_path):
    with open(result_path, "w") as f:
        f.write("<?xml version=\"1.0\" ?>\n")
        f.write(str(etree.tostring(ta_xml, encoding='unicode')))

# On charge le TA
ta_xml = open_ta(ta_xml_path)

# On crée l'objet calibration qui contient les paramètres internes de la caméra
calibrationFile = getCalibrationFile(ori_path)
calibration = Calibration.createCalibration(calibrationFile)

# On crée un objet orientation par image
orientations = createOrientation(ori_path)

# Facultatif : corrige les images de la distorsion. Pas suffisamment testé
#transformImages("./", imagesSave_path, calibration)

# On complète le nouveau fichier TA
complete_TA(ta_xml, calibration, orientations)

# On sauvegarde le nouveau fichier TA. Attention, les z sont des altitudes, pas des hauteurs
save_TA(ta_xml, result_path)