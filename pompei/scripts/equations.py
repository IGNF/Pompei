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

import numpy as np
import pyproj
from scipy.spatial.transform import Rotation as R
from osgeo import gdal
from scipy import ndimage
from lxml import etree
import rasterio
import os




dict_EPSG = {
    32705:{"auth":32705, "epsg_geoc": "IGNF:RGPF", "epsg_geog": "IGNF:RGPFGDD"},#à vérifier
    32706:{"auth":32706, "epsg_geoc": "IGNF:RGPF", "epsg_geog": "IGNF:RGPFGDD"},#à vérifier
    32707:{"auth":32707, "epsg_geoc": "IGNF:RGPF", "epsg_geog": "IGNF:RGPFGDD"},#à vérifier
    32620:{"auth":32620, "epsg_geoc": 5487, "epsg_geog": 7086},#à vérifier
    32621:{"auth":32621, "epsg_geoc": 4966, "epsg_geog": 7041},#à vérifier
    32622:{"auth":32622, "epsg_geoc": 4966, "epsg_geog": 7041},#à vérifier
    32738:{"auth":32738, "epsg_geoc": 4468, "epsg_geog": 7039},#à vérifier
    32739:{"auth":32739, "epsg_geoc": "IGNF:RGTAAF07", "epsg_geog": 7088},#à vérifier
    32740:{"auth":32740, "epsg_geoc": 4970, "epsg_geog": 7036},
    32742:{"auth":32742, "epsg_geoc": "IGNF:RGTAAF07", "epsg_geog": 7088},#à vérifier
    32743:{"auth":32743, "epsg_geoc": "IGNF:RGTAAF07", "epsg_geog": 7088},#à vérifier
    2154:{"auth": "IGNF:RGF93LAMB93", "epsg_geoc": 4374, "epsg_geog": 7084}    
}

class Shot:
    def __init__(self) -> None:
        self.x_central = None
        self.y_central = None
        self.z_central = None
        self.rot_to_euclidean_local = None
        

    def __str__(self) -> str:
        return "Shot_{}".format(self.imagePath)

    @staticmethod
    def getProj(EPSG):
        if not EPSG in dict_EPSG.keys():
            raise ValueError("Impossible de créer une ortho sur MNT pour l'EPSG {} car ses coordonnées géocentriques et géographiques n'ont pas été renseignées".format(EPSG))

        proj = dict_EPSG[EPSG]

        if isinstance(proj["auth"], int):
            crs = pyproj.CRS.from_epsg(proj["auth"])
        else:
            crs = pyproj.CRS.from_string(proj["auth"])

        if isinstance(proj["epsg_geoc"], int):
            crs_geoc = pyproj.CRS.from_epsg(proj["epsg_geoc"])
        else:
            crs_geoc = pyproj.CRS.from_string(proj["epsg_geoc"])

        if isinstance(proj["epsg_geog"], int):
            crs_geog = pyproj.CRS.from_epsg(proj["epsg_geog"])
        else:
            crs_geog = pyproj.CRS.from_string(proj["epsg_geog"])

        crs_to_crs_geoc = pyproj.Transformer.from_crs(crs, crs_geoc)
        crs_geoc_to_crs = pyproj.Transformer.from_crs(crs_geoc, crs)
        crs_to_crs_geog = pyproj.Transformer.from_crs(crs, crs_geog)
        return {
            "crs_to_crs_geoc":crs_to_crs_geoc,
            "crs_geoc_to_crs":crs_geoc_to_crs,
            "crs_to_crs_geog":crs_to_crs_geog,
            "crs":crs,
            "crs_geoc":crs_geoc,
            "crs_geog":crs_geog
        }


    def setProj(self, proj):

        self.crs_to_crs_geoc = proj["crs_to_crs_geoc"]
        self.crs_geoc_to_crs = proj["crs_geoc_to_crs"]
        self.crs_to_crs_geog = proj["crs_to_crs_geog"]
        self.crs = proj["crs"]
        self.crs_geoc = proj["crs_geoc"]
        self.crs_geog = proj["crs_geog"]


    @staticmethod
    def createShot(path, proj, calibration):
        shot = Shot()
        shot.setProj(proj)
        tree = etree.parse(path)
        root = tree.getroot()

        centre = root.find(".//Centre").text
        x = float(centre.split()[0])
        y = float(centre.split()[1])
        z = float(centre.split()[2])

        shot.x_pos = x
        shot.y_pos = y
        shot.z_pos = z
        shot.x_central = x
        shot.y_central = y
        shot.z_central = 0
        shot.rot_to_euclidean_local = shot.topaero_matrix(shot.x_central, shot.y_central)

        name = os.path.basename(path).replace(".tif.xml", "").replace("Orientation-", "")
        shot.nom = name
        shot.imagePath = f"{name}.tif"
        inputds = gdal.Open(shot.imagePath)
        shot.X_size = inputds.RasterXSize
        shot.Y_size = inputds.RasterYSize
        
        shot.calibration = calibration
        shot.x_ppa = calibration.PPX
        shot.y_ppa = calibration.PPY
        shot.focal = calibration.focale

        shot.x_pos_eucli, shot.y_pos_eucli, shot.z_pos_eucli = shot.world_to_euclidean(x, y, z)
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
        shot.mat_eucli = rotMatrice

        return shot


    def carto_to_geoc(self, x, y, z):
        return self.crs_to_crs_geoc.transform(x, y, z)

    def geoc_to_carto(self, x, y, z):
        return self.crs_geoc_to_crs.transform(x, y, z)

    def carto_to_geog(self, x, y):
        return self.crs_to_crs_geog.transform(x, y)

    def world_to_euclidean(self, x, y, z):
            """
            Transform a point from the world coordinate reference system into the Euclidean coordinate reference system

            :param x: x coordinate of the point
            :param y: y coordinate of the point
            :param z: z coordinate of the point

            :return: x, y, z in the Euclidean coordinate reference system
            """
            x_geoc, y_geoc, z_geoc = self.carto_to_geoc(np.array(x), np.array(y), np.array(z))
            x_central_geoc, y_central_geoc, z_central_geoc = self.carto_to_geoc(self.x_central, self.y_central, self.z_central)
            dr = np.vstack([x_geoc-x_central_geoc, y_geoc-y_central_geoc, z_geoc-z_central_geoc])
            point_eucli = (self.rot_to_euclidean_local @ dr) + np.array([self.x_central, self.y_central, self.z_central]).reshape(-1, 1)
            return np.squeeze(point_eucli[0]), np.squeeze(point_eucli[1]), np.squeeze(point_eucli[2])


    def world_to_image(self, x_world, y_world, z_world):
            """
            Compute the image coordinates of a world point.
            This algorithm is slower but more accurate than :func:`world_to_image_approx`.

            :param x_world: x_world coordinates of the point
            :param y_world: y_world coordinates of the point
            :param z_world: z_world coordinates of the point

            :return: c, l Image coordinates
            """
            type_input = type(x_world)
            x_bundle, y_bundle, z_bundle = self.local_to_bundle(x_world, y_world, z_world)
            x_shot, y_shot, z_shot = self.bundle_to_shot(x_bundle, y_bundle, z_bundle)
            c, l = self.shot_to_image(x_shot, y_shot, z_shot)
            return self.convertback(type_input, c, l)

    def euclidean_to_world(self, x_eucli, y_eucli, z_eucli):
        """
        Transform a point from the Euclidean coordinate reference system into the world coordinate reference system.

        :param x_eucli: x coordinate of the point
        :param y_eucli: y coordinate of the point
        :param z_eucli: y coordinate of the point

        :return: x, y, z in the world coordinate reference system
        """
        x_eucli, y_eucli, z_eucli = np.array(x_eucli), np.array(y_eucli), np.array(z_eucli)
        x_central_geoc, y_central_geoc, z_central_geoc = self.carto_to_geoc(np.array([self.x_central]),
                                                                                        np.array([self.y_central]),
                                                                                        np.array([self.z_central]))

        dr = np.vstack([x_eucli - self.x_central, y_eucli - self.y_central, z_eucli - self.z_central])
        point_geoc = (self.rot_to_euclidean_local.T @ dr) + \
                     np.array([x_central_geoc, y_central_geoc, z_central_geoc]).reshape(-1, 1)
        return self.geoc_to_carto(point_geoc[0], point_geoc[1], point_geoc[2])

    
    def image_to_world(self, c, l, dem, prec=0.1, iter_max=3):
        """
        Compute the world coordinates of (a) image point(s).
        A Dem must be used.

        :param c: column coordinates of image point(s)
        :param l: line coordinates of image point(s)
        :param dem: Dem of the area or constant value
        :param prec: accuracy
        :param iter_max: maximum number of iterations

        Attention, la distorsion n'est pas corrigée ici !!! 

        :return: x, y, z World coordinates
        """
        # initialisation
        # passage en local en faisant l'approximation z "local" a partir du z "world"
        # La fonction calcule le x et y euclidien correspondant à une coordonnées image et un Z local
        type_input = type(c)

        z_world = dem.get(self.x_pos, self.y_pos)
        z_world = np.full_like(c, z_world)
        x_local, y_local, z_local = self.image_z_to_local(c, l, z_world)
        # On a les coordonnées locales approchées (car z non local) on passe en world
        x_world, y_world, _ = self.euclidean_to_world(x_local, y_local, z_local)
        precision_reached = False
        nbr_iter = 0

        while not precision_reached and nbr_iter < iter_max:
            z_world = dem.get(x_world, y_world)
            # On repasse en euclidien avec le bon Zworld , l'approximation plani ayant un impact minime
            x_local, y_local, z_local = self.world_to_euclidean(x_world, y_world, z_world)
            # nouvelle transfo avec un zLocal plus precis
            x_local, y_local, z_local = self.image_z_to_local(c, l, z_local)
            # passage en terrain (normalement le zw obtenu devrait être quasiment identique au Z initial)
            x_world_new, y_world_new, z_world_new = self.euclidean_to_world(x_local, y_local, z_local)

            dist = ((x_world_new - x_world) ** 2 + (y_world_new - y_world) ** 2 + (z_world_new - z_world) ** 2) ** 0.5
            if np.any(dist < prec):
                precision_reached = True
            x_world, y_world, z_world = x_world_new, y_world_new, z_world_new
            nbr_iter += 1

        return self.convertback(type_input, x_world, y_world, z_world)

    def image_z_to_local(self, c, l, z):
        x_local_0, y_local_0, z_local_0, x_local_1, y_local_1, z_local_1 = self.image_to_local_vec(c, l)
        lamb = (z - z_local_0) / (z_local_1 - z_local_0)
        x_local = x_local_0 + (x_local_1 - x_local_0) * lamb
        y_local = y_local_0 + (y_local_1 - y_local_0) * lamb
        return x_local, y_local, z

    def image_to_local_vec(self, c, l):
        # on calcule le faisceau perspectif
        x_bundle_0, y_bundle_0, z_bundle_0 = 0, 0, 0
        x_bundle_1, y_bundle_1, z_bundle_1 = self.shot_to_bundle(*self.image_to_shot(c, l))

        # on passe le faisceau dans le repere local extrinseque
        x_local_0, y_local_0, z_local_0 = self.bundle_to_local(x_bundle_0, y_bundle_0, z_bundle_0)
        x_local_1, y_local_1, z_local_1 = self.bundle_to_local(x_bundle_1, y_bundle_1, z_bundle_1)

        return x_local_0, y_local_0, z_local_0, x_local_1, y_local_1, z_local_1

    def shot_to_bundle(self, x_shot, y_shot, z_shot):
        # Repere cliche -> repere faisceau
        x_bundle = x_shot / self.focal * z_shot
        y_bundle = y_shot / self.focal * z_shot
        z_bundle = z_shot
        return x_bundle, y_bundle, z_bundle

    def image_to_shot(self, c, l):
        # Repere image -> repere cliche
        x_shot = c - self.x_ppa
        y_shot = l - self.y_ppa
        z_shot = np.full_like(x_shot, self.focal)
        return x_shot, y_shot, z_shot

    def bundle_to_local(self, x_bundle, y_bundle, z_bundle):
        # Repere faisceau -> repere local
        point_local = self.mat_eucli @ np.vstack([x_bundle, y_bundle, z_bundle]) + np.array(
            [self.x_pos_eucli, self.y_pos_eucli, self.z_pos_eucli]).reshape(-1, 1)
        return point_local[0], point_local[1], point_local[2]

    
    def convertback(self, data_type: type, *args: np.ndarray):
        # if inputs were lists, tuples or floats, convert back to original type.
        output = []
        for val in args:
            if data_type == list:
                output.append(val.tolist())
            elif data_type == np.ndarray:
                output.append(val)
            # elif data_type == pd.core.series.Series:
            #     output.append(val)
            else:
                output.append(val.item())
        if len(output) > 1:
            return *output,
        else:
            return output[0]

    
    def local_to_bundle(self, x_local, y_local, z_local):
        # Repere local euclidien -> repere faisceau
        point_bundle = self.mat_eucli.T @ np.vstack([x_local - self.x_pos_eucli, y_local - self.y_pos_eucli, z_local - self.z_pos_eucli])
        return point_bundle[0], point_bundle[1], point_bundle[2]

    def bundle_to_shot(self, x_bundle, y_bundle, z_bundle):
        # Repere faisceau -> repere cliche
        x_shot = x_bundle * self.focal / z_bundle
        y_shot = y_bundle * self.focal / z_bundle
        z_shot = z_bundle
        return x_shot, y_shot, z_shot

    def shot_to_image(self, x_shot, y_shot, _):
        # Repere cliche -> repere image
        c = x_shot + self.x_ppa
        l = y_shot + self.y_ppa
        return c, l


    def topaero_matrix(self, x: float, y:float) -> np.array:
        """
        Compute the transition matrix between the world system and the Euclidean system centred on a point.

        :param x: x coordinate of the central point of the Euclidean system
        :param y: y coordinate of the central point of the Euclidean system

        :return: transition matrix
        """
        lon, lat = self.carto_to_geog(x, y)
        gamma = self.get_meridian_convergence(x, y)

        # rot_to_euclidean_local = R.from_euler("z", -(90+gamma), degrees=True) *\
        #                          R.from_euler("y", -(90-lat), degrees=True) *\
        #                          R.from_euler("z", -lon, degrees=True)

        # Matrice de passage en coordonnees cartesiennes locales
        sl = np.sin(lon * np.pi/180)
        sp = np.sin(lat * np.pi/180)
        sg = np.sin(gamma * np.pi/180)
        cl = np.cos(lon * np.pi/180)
        cp = np.cos(lat * np.pi/180)
        cg = np.cos(gamma * np.pi/180)
        rot_to_euclidean_local = np.zeros((3, 3))
        rot_to_euclidean_local[0, 0] = -cg * sl - sg * sp * cl
        rot_to_euclidean_local[0, 1] = cg * cl - sg * sp * sl
        rot_to_euclidean_local[0, 2] = sg * cp
        rot_to_euclidean_local[1, 0] = sg * sl - cg * sp * cl
        rot_to_euclidean_local[1, 1] = -sg * cl - cg * sp * sl
        rot_to_euclidean_local[1, 2] = cg * cp
        rot_to_euclidean_local[2, 0] = cp * cl
        rot_to_euclidean_local[2, 1] = cp * sl
        rot_to_euclidean_local[2, 2] = sp
        return rot_to_euclidean_local

    def get_meridian_convergence(self, x_carto, y_carto):
        """
            Compute meridian convergence.
            Values are extracted from pyproj.

            :param x_carto: x cartographic coordinates
            :param y_carto: y cartographic coordinates

            :return: meridian convergence in degree
        """
        x_geog, y_geog = self.carto_to_geog(x_carto, y_carto)
        proj = pyproj.Proj(self.crs)
        return -np.array(proj.get_factors(x_geog, y_geog).meridian_convergence)




class MNT:

    def __init__(self, path) -> None:
        self.dem = rasterio.open(path)
        self.gt = self.dem.transform
        self.l_max = self.dem.height
        self.c_max = self.dem.width

    def world_to_image(self, x, y):
        """
            Compute image coordinates from world coordinates

            :param x: x world coordinate
            :param y: y world coordinate
            :return: image coordinates
        """
        c = (x - self.gt.c)/self.gt.a
        l = (y - self.gt.f)/self.gt.e
        return c, l


    def get(self, x, y):
        """
            Extract value in the Dem

            :param x: x world coordinate
            :param y: y world coordinate
            :return: z value.
        """
        c, l = self.world_to_image(x, y)
        c_min = int(max(np.min(c), 0))
        l_min = int(max(np.min(l), 0))
        
        c_max = int(min(np.max(c), self.c_max))
        l_max = int(min(np.max(l), self.l_max))
        if c_max-c_min+10 < 0 or l_max-l_min+10 < 0:
            return np.zeros(x.shape)
        array_ex = self.dem.read(window=rasterio.windows.Window(c_min, l_min, c_max-c_min+10, l_max-l_min+10)).squeeze()
        array_ex = np.where(array_ex<=-1000.00, 0, array_ex)
        array_ex = np.nan_to_num(array_ex)
        # Les points images sont en col lig mais les np.array sont en lig col
        try:
            z = ndimage.map_coordinates(array_ex, np.vstack([l-l_min, c-c_min]), order=1, mode="constant")
            return z
        except:
            return np.zeros(x.shape)        

class Mask:
    def __init__(self, path) -> None:
        self.mask = rasterio.open(path)
        self.gt = self.mask.transform
        self.l_max = self.mask.height
        self.c_max = self.mask.width

    def world_to_image(self, x, y):
        """
            Compute image coordinates from world coordinates

            :param x: x world coordinate
            :param y: y world coordinate
            :return: image coordinates
        """
        c = (x - self.gt.c)/self.gt.a
        l = (y - self.gt.f)/self.gt.e
        return c, l

    def get(self, x, y):
        
        try:
            c, l = self.world_to_image(x, y)
            c_min = int(max(np.min(c), 0))
            l_min = int(max(np.min(l), 0))
            c_max = int(min(np.max(c), self.c_max))
            l_max = int(min(np.max(l), self.l_max))
            array_ex = self.mask.read(window=rasterio.windows.Window(c_min, l_min, c_max-c_min+10, l_max-l_min+10)).squeeze()
            array_ex = np.where(array_ex>=1, 1, 0)
            l_request = l-l_min
            l_request = l_request.astype(np.int16)
            c_request = c-c_min
            c_request = c_request.astype(np.int16)

            l_out = np.full(l_request.shape, False)
            l_out[l_request<0] = True
            l_request[l_request<0] = 0
            l_out[l_request>=array_ex.shape[0]] = True
            l_request[l_request>=array_ex.shape[0]] = 0

            c_out = np.full(c_request.shape, False)
            c_out[c_request<0] = True
            c_request[c_request<0] = 0
            c_out[c_request>=array_ex.shape[1]] = True
            c_request[c_request>=array_ex.shape[1]] = 0

            z = array_ex[l_request, c_request]
            z[l_out] = 0
            z[c_out] = 0
            return z
        except:
            return np.zeros(x.shape)

        

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


class DistorsionCorrection:

    def __init__(self, calibration:Calibration) -> None:
        self.calibration = calibration

    def create_cc_ll(self):
        l = np.arange(self.calibration.sizeX)
        c = np.arange(self.calibration.sizeY)
        self.cc, self.ll = np.meshgrid(l, c)
        self.du = self.cc - self.calibration.PPX
        self.dv = self.ll - self.calibration.PPY
        self.rho = self.du**2 + self.dv**2

    def compute(self, c, l):
        self.du = c - self.calibration.PPX
        self.dv = l - self.calibration.PPY
        self.rho = self.du**2 + self.dv**2
        self.compute_Dr()
        self.computeDecentric()
        self.computeAffine()
        self.computeAll()
        return self.DPx, self.DPy

    
    def compute_Dr(self):

        intermediaire = (1+self.calibration.distorsionCoefficient[0]*self.rho+self.calibration.distorsionCoefficient[1]*self.rho**2+self.calibration.distorsionCoefficient[2]*self.rho**3+self.calibration.distorsionCoefficient[3]*self.rho**4)
        self.drx = self.calibration.PPX + intermediaire * self.du
        self.dry = self.calibration.PPY + intermediaire * self.dv
        
    def computeDecentric(self):
        P1x = self.calibration.decentric_P1 * (2*self.du**2 + self.rho)
        P1y = self.calibration.decentric_P1 * 2*self.du *self.dv
        P2x = self.calibration.decentric_P2 * 2*self.du *self.dv
        P2y = self.calibration.decentric_P2 * (2*self.dv**2 + self.rho)
        self.decentricx = P1x + P2x
        self.decentricy = P1y + P2y
        
    def computeAffine(self):
        self.affine = self.calibration.affine_b1 * self.du + self.calibration.affine_b2 * self.dv

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