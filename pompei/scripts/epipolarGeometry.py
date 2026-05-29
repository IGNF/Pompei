
import numpy as np
from equations import Shot, DistorsionCorrection
from pathlib import Path
import struct
from shapely import Point, Polygon
import geopandas as gpd

class EpipolarGeometry:

    def __init__(self, image1, image2, dem, homolDir:Path) -> None:
        """
        Construit deux images dans leur géométrie épipolaire

        Equations issues de : Mathématiques de la photogrammétrie numérique, J. F. Haas, 2004
        """

        self.image1:Shot = image1
        self.image2:Shot = image2
        self.dem = dem
        self.homolDir = homolDir

        self.r2e:np.array = None
        self.r1e:np.array = None


    @staticmethod
    def load(image1, image2, r1e, r2e):
        epipolarGeometry = EpipolarGeometry(image1, image2, None, None)
        epipolarGeometry.r1e = r1e
        epipolarGeometry.r2e = r2e
        return epipolarGeometry

        


    def compute(self):
        # On détermine la matrice permettant de passer l'image 1 en géométrie épipolaire
        self.r1e = self.geom_epipolaire(self.image1, self.image2)
        
        # On détermine la matrice permettant de passer l'image 2 en géométrie épipolaire
        self.r2e = self.geom_epipolaire(self.image2, self.image1)

        self.decalage = self.compute_dh()


        #self.decalage.to_file("diff.gpkg")


        c1, l1 = self.image_to_epip(np.array([10]), np.array([10]), self.image1, self.r1e)
        c2, l2 = self.epip_to_image(c1, l1, self.image1, self.r1e)


        c1, l1 = self.image_to_epip(np.array([100]), np.array([100]), self.image2, self.r2e)
        c2, l2 = self.epip_to_image(c1, l1, self.image2, self.r2e)


    def compute_epip_image(self, c1_epip, l1_epip, image:Shot, E, len_x, len_y):
        c, l = self.epip_to_image(c1_epip, l1_epip, image, E)
        image_epip = image.read(c, l, len_x, len_y, 1)
        return image_epip, c, l
    

    def get_decalage(self, c1_epip, l1_epip):
        emprise = Polygon.from_bounds(np.min(c1_epip), np.min(l1_epip), np.max(c1_epip), np.max(l1_epip))
        tie_points_in = self.decalage[self.decalage.intersects(emprise)]
        diff_l = tie_points_in["diff_l"]
        diff_c = tie_points_in["diff_c"]
        return np.median(diff_c), np.median(diff_l)


    def compute_epip_images(self, xx, yy, z, len_x, len_y):
        """
        Calcule les images épipolaires pour les deux images
        xx, yy, z : coordonnées terrain de la zone à étudier
        """

        # On projette les pixels terrain en géométrie image pour la première image
        c1_im, l1_im = self.image1.world_to_image(xx, yy, z)
        
        ## On applique la correction de la distorsion 
        #dc = DistorsionCorrection(self.image1.calibration)
        #c1_corr, l1_corr = dc.compute(c1_im, l1_im)
#
        ## On récupère les coordonnées épipolaires, toujours pour la première image
        #c1_epip, l1_epip = self.image_to_epip(c1_corr, l1_corr, self.image1, self.r1e)



        c1_epip, l1_epip = self.image_to_epip(c1_im, l1_im, self.image1, self.r1e)

        # On calcule la translation à appliquer entre les deux images en géométrie épipolaire pour qu'elles se superposent correctement
        # Pour cela, on utilise les points de liaisons
        diff_c, diff_l = self.get_decalage(c1_epip, l1_epip)

        # A partir de ces coordonnées épipolaires, on calcule les coordonnées images correspondant pour reconstruire l'image épipolaire
        image_epip_1, c1_im, l1_im = self.compute_epip_image(c1_epip, l1_epip, self.image1, self.r1e, len_x, len_y)
        # On applique le décalage entre les deux géométries épipolaires
        image_epip_2, c2_im, l2_im = self.compute_epip_image(c1_epip-diff_c, l1_epip-diff_l, self.image2, self.r2e, len_x, len_y)

        return image_epip_1, image_epip_2, c1_im, l1_im, c2_im, l2_im, diff_c, diff_l


    



    def get_path_tie_points(self):
        return self.homolDir/f"Pastis{self.image1.nom}.tif"/f"{self.image2.nom}.tif.dat"


    def load_tie_points(self, file):
        points1 = []
        points2 = []
        with open(file, "rb") as f:
            fileContent = f.read()
            en_tete = "ii"
            longueur_en_tete = struct.calcsize(en_tete) 

            for i in range(longueur_en_tete, len(fileContent), 44):
                extrait = fileContent[i+4:i+44]

                a = struct.unpack(("ddddd"), extrait)
                points1.append([a[1], a[2]])
                points2.append([a[3], a[4]])
                

        return points1, points2


    def compute_dh(self):
        paths_tie_points = self.get_path_tie_points()
        tp_image_1, tp_image_2 = self.load_tie_points(paths_tie_points)
        tp_image_1 = np.array(tp_image_1)
        tp_image_2 = np.array(tp_image_2)
    
        c_epip_1, l_epip_1 = self.image_to_epip(tp_image_1[:,0], tp_image_1[:,1], self.image1, self.r1e)
        c_epip_2, l_epip_2 = self.image_to_epip(tp_image_2[:,0], tp_image_2[:,1], self.image2, self.r2e)

        decalage_l = l_epip_1-l_epip_2
        decalage_c = c_epip_1-c_epip_2

        geometry = []
        diff_l = []
        diff_c = []
        for i in range(decalage_l.shape[0]):
            geometry.append(Point(c_epip_1[i], l_epip_1[i]))
            diff_l.append(decalage_l[i])
            diff_c.append(decalage_c[i])
        return gpd.GeoDataFrame({"geometry":geometry, "diff_l":diff_l, "diff_c":diff_c})



    def image_to_epip(self, c, l, image:Shot, E):
        """
        Convertit les coordonnées images d'une image en coordonnées épipolaires
        """

        focale = -image.focal
        
        m = np.vstack([c, l, np.zeros(c.shape)])
        F = np.full_like(m, np.array([[0], [0], [focale]]))
        L1E = E[0,:].T
        L2E = E[1,:].T
        L3E = E[2,:].T

        p_prime = -(self.image1.focal+self.image2.focal)/2
        
        m_f = m-F
        x = - p_prime * ((L1E @ (m_f)) / (L3E @ (m_f)))
        
        y = - p_prime * ((L2E @ (m_f)) / (L3E @ (m_f)))

        return x, y



    def epip_to_image(self, c, l, image:Shot, E):
        """
        Convertit les coordonnées épipolaires d'une image en coordonnées images
        """

        focale = -image.focal

        # On met en forme les points
        m = np.vstack([c, l, np.zeros(c.shape)])

        # On calcule F_prime dans le repère de l'image épipolaire
        # F_prime est le point F mais dans le repère de l'image épipolaire
        F_prime = np.full_like(m, np.array([[0], [0], [-(self.image1.focal+self.image2.focal)/2]]))

        C1E = E[:,0]
        C2E = E[:,1]
        C3E = E[:,2]

        m_f = m-F_prime
        x = -focale * ((C1E @ (m_f)) / (C3E @ (m_f)))
        y = -focale * ((C2E @ (m_f)) / (C3E @ (m_f)))

        return x, y




    def geom_epipolaire(self, im1, im2, facteur_base=1):
        """
        Calcule E, la matrice pour passer en géométrie épipolaire
        """
        # Calcul de omega

        R = im1.mat_eucli.T
        RA = im2.mat_eucli.T


        L2 = R[1,:]
        L3A = RA[2,:]
        L1 = R[0,:]


        t = (L2 @ L3A.T) / (L1 @ L3A.T)

        a = - t / (np.sqrt(1+t**2))
        b = 1 / np.sqrt(1+t**2)
        c = 0



        # Calcul de n
        L3 = R[2,:]
        s1 = im1.sommet
        s2 = im2.sommet
        B = np.array([s2[0] - s1[0], s2[1] - s1[1], s2[2] - s1[2]]) * facteur_base
        d = np.sqrt((1+t**2) * (L3 @ B)**2 + (L1 @ B + t * L2 @ B)**2)
        n = np.array([L3 @ B / d, t * L3 @ B / d, -(L1 @ B + t * L2 @ B) / d])
        
        
        sigma = L3 @ B / np.linalg.norm(L3@B)

        # Calcul de theta
        if n[2]<0:
            n = -n
            cos_theta = n[2]
            sin_theta = np.sqrt(n[0]**2 + n[1]**2) * (L3 @ B / np.abs(L3 @ B))
        else:
            cos_theta = n[2]
            sin_theta = -np.sqrt(n[0]**2 + n[1]**2) * (L3 @ B / np.abs(L3 @ B))

        # Calcul de R_prime
        omega_axiateur = np.array([[0, -c, b], [c, 0, -a], [-b, a, 0]])
        R_prime = np.eye(3) + omega_axiateur * sin_theta + omega_axiateur @ omega_axiateur * (1 - cos_theta)

        # Calcul de R_seconde
        L1_prime = R_prime[0,:]
        L2_prime = R_prime[1,:]
        if L1_prime @ R @ B > 0:
            sigma = 1
        else:
            sigma = -1
        B_norme = np.linalg.norm(B)
        R_seconde = 1 / B_norme * np.array([[sigma * L1_prime @ R @ B, sigma * L2_prime @ R @ B, 0], [-sigma * L2_prime @ R @ B, sigma * L1_prime @ R @ B, 0], [0, 0, B_norme]])
        # calcul de E, matrice pour passer dans la géométrie épipolaire

        E = R_seconde @ R_prime
        return E