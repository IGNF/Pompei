# -*- coding: utf-8 -*-
"""
Created on Sat Dec 21 12:43:45 2024

@author: abont
"""

from PyQt5.QtWidgets import (
    QApplication, QGraphicsView, QGraphicsScene, QMainWindow, 
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSplitter
)
from PyQt5.QtGui import QPixmap, QPen, QCursor, QPainter, QColor
from PyQt5.QtCore import QRectF, Qt

import xml.etree.ElementTree as ET

import argparse

import numpy as np


class ImageZoomer(QMainWindow):
    def __init__(self, image_path, output_path, flag, in_xml):
        super().__init__()
        self.setWindowTitle("Saisie Repères de fonds de chambre")
        self.points = [] # list of selected points
        self.point_items = []  # Keep track of graphical items for points
        self.output_path = output_path
        
        # Load the image
        self.pixmap = QPixmap(image_path)
        image = self.pixmap.toImage()
        
        print(self.pixmap.width(), self.pixmap.height())
        
        # Create a scene and add the image
        self.scene = QGraphicsScene()
        self.scene.addPixmap(self.pixmap)
        
        # Configure the view to display the scene
        self.view = QGraphicsView(self.scene, self)
        
        # Create control buttons
        self.controls_widget = QWidget()
        self.controls_layout = QVBoxLayout(self.controls_widget)
        
        if not flag:
            # Add buttons for zooming into different regions
            self.zoom_top_left_button = QPushButton("Zoom Haut-Gauche", self)
            self.zoom_top_right_button = QPushButton("Zoom Haut-Droite", self)
            self.zoom_bottom_left_button = QPushButton("Zoom Bas-Gauche", self)
            self.zoom_bottom_right_button = QPushButton("Zoom Bas-Droite", self)
            
            self.zoom_medium_top = QPushButton("Zoom Milieu-Haut", self)
            self.zoom_medium_right = QPushButton("Zoom Milieu-Droite", self)
            self.zoom_medium_bottom = QPushButton("Zoom Milieu-Bas", self)
            self.zoom_medium_left = QPushButton("Zoom Milieu-Gauche", self)
            
            # detect borders in the image
            top_border, right_border, bottom_border, left_border = self.find_border(image)
            
            # Connect buttons to their respective zoom
            self.zoom_top_left_button.clicked.connect(lambda: self.zoom_on_area(left_border, top_border))
            self.zoom_top_right_button.clicked.connect(lambda: self.zoom_on_area(self.pixmap.width() -right_border-800, top_border))
            self.zoom_bottom_left_button.clicked.connect(lambda: self.zoom_on_area(left_border, self.pixmap.height() -bottom_border-600))
            self.zoom_bottom_right_button.clicked.connect(lambda: self.zoom_on_area(self.pixmap.width() -right_border-800, self.pixmap.height() -bottom_border-600))
            
            self.zoom_medium_top.clicked.connect(lambda: self.zoom_on_area(self.pixmap.width()/2 - 400, top_border))
            self.zoom_medium_right.clicked.connect(lambda: self.zoom_on_area(self.pixmap.width() -right_border, self.pixmap.height()/2 - 400))
            self.zoom_medium_bottom.clicked.connect(lambda: self.zoom_on_area(self.pixmap.width()/2 - 400, self.pixmap.height() -bottom_border))
            self.zoom_medium_left.clicked.connect(lambda: self.zoom_on_area(left_border, self.pixmap.height()/2 - 400))

            # Add buttons to the layout
            self.controls_layout.addWidget(self.zoom_top_left_button)
            self.controls_layout.addWidget(self.zoom_top_right_button)
            self.controls_layout.addWidget(self.zoom_bottom_left_button)
            self.controls_layout.addWidget(self.zoom_bottom_right_button)
            
            self.controls_layout.addWidget(self.zoom_medium_top)
            self.controls_layout.addWidget(self.zoom_medium_right)
            self.controls_layout.addWidget(self.zoom_medium_bottom)
            self.controls_layout.addWidget(self.zoom_medium_left)
            
            self.controls_layout.addStretch()  # Add flexible space

        if flag:
            liste = np.array(self.lire_fichier_xml(in_xml))
            print(liste)
            '''
            for i in range(len(liste)):
                button = QPushButton(f"Zoom {i}", self)  # Crée un bouton avec un texte spécifique
                #button.clicked.connect(lambda: self.zoom_on_area(liste[1,i]-400, liste[2,i]-300))
                setattr(self, f"zoom_pt{i}", button)  # Attribue dynamiquement à self.zoom_pt1, etc.
                #self.zoom_pt{i}.clicked.connect(lambda: self.zoom_on_area(liste[1,i]-400, liste[2,i]-300))

                self.controls_layout.addWidget(button)  # Ajoute le bouton à l'interface

            '''            
            # Add buttons for zooming into different regions
            self.zoom_pt1 = QPushButton("Zoom 1", self)
            self.zoom_pt2 = QPushButton("Zoom 2", self)
            self.zoom_pt3 = QPushButton("Zoom 3", self)
            self.zoom_pt4 = QPushButton("Zoom 4", self)
            
            # Connect buttons to their respective zoom
            self.zoom_pt1.clicked.connect(lambda: self.zoom_on_area(liste[0,0]-400, liste[0,1]-300))
            self.zoom_pt2.clicked.connect(lambda: self.zoom_on_area(liste[1,0]-400, liste[1,1]-300))
            self.zoom_pt3.clicked.connect(lambda: self.zoom_on_area(liste[2,0]-400, liste[2,1]-300))
            self.zoom_pt4.clicked.connect(lambda: self.zoom_on_area(liste[3,0]-400, liste[3,1]-300))
            
            # Add buttons to the layout
            self.controls_layout.addWidget(self.zoom_pt1)
            self.controls_layout.addWidget(self.zoom_pt2)
            self.controls_layout.addWidget(self.zoom_pt3)
            self.controls_layout.addWidget(self.zoom_pt4)
            
            self.controls_layout.addStretch()  # Add flexible space
            
        # Split the window into two parts: the view and the controls
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.view)
        self.splitter.addWidget(self.controls_widget)

        # Set the splitter as the central widget of the main window
        self.setCentralWidget(self.splitter)

        # Set the initial window size
        self.resize(1000, 600)

        # Initialize zoom
        self.zoom_on_area(self.pixmap.width()/2, self.pixmap.height()/2)  # Centre image
        
        # Handle mouse clicks for selecting or removing points
        self.view.mousePressEvent = self.handle_mouse_press
        
        # Customize the cursor
        self.set_custom_cursor()
        
    def set_custom_cursor(self):
        # Create a cross cursor
        size = 16  # Cursor size
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)  # Transparent background
    
        # Draw a cross in the pixmap
        painter = QPainter(pixmap)
        painter.setPen(QPen(Qt.red, 2))  # Red cross
        painter.drawLine(0, size // 2, size, size // 2)  # Horizontal line
        painter.drawLine(size // 2, 0, size // 2, size)  # Vertical line
        painter.end()
    
        # Set the cursor with the hotspot at the center
        custom_cursor = QCursor(pixmap, size // 2, size // 2)
        self.view.setCursor(custom_cursor)
        
    def handle_mouse_press(self, event):
        # Map the mouse click to the scene coordinates
        scene_pos = self.view.mapToScene(event.pos())
        if event.button() == Qt.LeftButton:
            self.add_point(scene_pos)
        elif event.button() == Qt.RightButton:
            self.remove_point(scene_pos)

    def add_point(self, scene_pos):
        # Add a new point at the clicked position
        self.points.append((scene_pos.x(), scene_pos.y()))
        print(f"Point added: {scene_pos.x()}, {scene_pos.y()}")

        # Add a visual marker for the point
        pen = QPen(Qt.red)
        point_item = self.scene.addEllipse(scene_pos.x() - 5, scene_pos.y() - 5, 10, 10, pen)
        self.point_items.append(point_item)

    def remove_point(self, scene_pos):
        # Check if the click is near an existing point and remove the point
        tolerance = 10  # Radius around the point
        for i, (x, y) in enumerate(self.points):
            if abs(scene_pos.x() - x) <= tolerance and abs(scene_pos.y() - y) <= tolerance:
                # Remove the point and its marker
                print(f"Point removed: {x}, {y}")
                self.points.pop(i)
                point_item = self.point_items.pop(i)
                self.scene.removeItem(point_item)
                break  # Only remove one point
                
    def find_border(self, image):
        # functions to check if a line or column is black or white
        def is_black_line(image, y, threshold=0.85):
            black_pixel_count = 0
            for x in range(self.pixmap.width()):
                color = QColor(image.pixel(x, y))
                if color.red() <= 15 and color.green() <= 15 and color.blue() <= 15:
                    black_pixel_count += 1
            return black_pixel_count / self.pixmap.width() >= threshold
        
        def is_white_line(image, y, threshold=0.85):
            white_pixel_count = 0
            for x in range(self.pixmap.width()):
                color = QColor(image.pixel(x, y))
                if color.red() >= 250 and color.green() >= 250 and color.blue() >= 250:
                    white_pixel_count += 1
            return white_pixel_count / self.pixmap.width() >= threshold

        def is_black_column(image, x, threshold=0.85):
            black_pixel_count = 0
            for y in range(self.pixmap.height()):
                color = QColor(image.pixel(x, y))
                if color.red() <= 15 and color.green() <= 15 and color.blue() <= 15:
                    black_pixel_count += 1
            return black_pixel_count / self.pixmap.height() >= threshold
        
        def is_white_column(image, x, threshold=0.85):
            white_pixel_count = 0
            for y in range(self.pixmap.height()):
                color = QColor(image.pixel(x, y))
                if color.red() >= 250 and color.green() >= 250 and color.blue() >= 250:
                    white_pixel_count += 1
            return white_pixel_count / self.pixmap.height() >= threshold
        
        # Trouver les bordures noires
        top_border = 0
        for y in range(self.pixmap.height()):
            if not (is_black_line(image, y) or is_white_line(image, y)):
                top_border = y
                break

        bottom_border = self.pixmap.height() - 1
        for y in range(self.pixmap.height() - 1, -1, -1):
            if not (is_black_line(image, y)  or is_white_line(image, y)):
                bottom_border = self.pixmap.height() - y
                break

        left_border = 0
        for x in range(self.pixmap.width()):
            if not (is_black_column(image, x) or is_white_column(image, x)):
                left_border = x
                break

        right_border = self.pixmap.width() - 1
        for x in range(self.pixmap.width() - 1, -1, -1):
            if not (is_black_column(image, x) or is_white_column(image, x)):
                right_border = self.pixmap.width() - x
                break
        '''
        # Find the image borders by scanning lines and columns
        top_border = 0
        for y in range(2000):
            if is_black_line(image, y) or is_white_line(image, y):
                top_border = y

        bottom_border = self.pixmap.height() - 1
        for y in range(self.pixmap.height() - 1, self.pixmap.height() - 2000, -1):
            if is_black_line(image, y)  or is_white_line(image, y):
                bottom_border = self.pixmap.height() - y

        left_border = 0
        for x in range(2000):
            if is_black_column(image, x) or is_white_column(image, x):
                left_border = x

        right_border = self.pixmap.width() - 1
        for x in range(self.pixmap.width() - 1, self.pixmap.width()-2000, -1):
            if is_black_column(image, x) or is_white_column(image, x):
                right_border = self.pixmap.width() - x
        '''
        print(top_border, right_border, bottom_border, left_border)
        return top_border, right_border, bottom_border, left_border

    def zoom_on_area(self, x, y, zoom_factor=1.15):
        # Define the zoom rectangle based on coordinates and zoom factor
        view_width = self.view.viewport().width()
        view_height = self.view.viewport().height()
        
        zoom_rect = QRectF(
            x, 
            y, 
            view_width / zoom_factor, 
            view_height / zoom_factor
        )
        
        # Adjust the view to show only the zoomed rectangle
        self.view.fitInView(zoom_rect, mode=0)
     
    def closeEvent(self, event):
        # Generate an XML file with the selected points
        root = ET.Element("SetOfMesureAppuisFlottants")

        # First element
        mesure_appui = ET.SubElement(root, "MesureAppuiFlottant1Im")

        # second element
        name_im = ET.SubElement(mesure_appui, "NameIm")
        name_im.text = image_path
       
        # add coordinates points and their id
        for i, (x, y) in enumerate(self.points):
            one_measure = ET.SubElement(mesure_appui, "OneMesureAF1I")
            
            name_pt = ET.SubElement(one_measure, "NamePt")
            name_pt.text = f"{i+1}"
            
            pt_im = ET.SubElement(one_measure, "PtIm")
            pt_im.text = f"{x} {y}"

        # Write to the output file
        tree = ET.ElementTree(root)
        tree.write(self.output_path, encoding="utf-8", xml_declaration=True)
        print(f"Fichier XML créé : {self.output_path}")

    def lire_fichier_xml(self, nom_fichier):
        """
        Lit un fichier XML de mesures et extrait les IDs des points et leurs coordonnées.
        
        :param nom_fichier: Chemin du fichier XML à lire.
        :return: Liste de dictionnaires contenant les IDs et les coordonnées des points.
        """
        try:
            # Chargement du fichier XML
            tree = ET.parse(nom_fichier)
            root = tree.getroot()
            
            # Initialisation de la liste pour stocker les résultats
            points = []
            
            # Parcours des éléments "OneMesureAF1I" dans le fichier XML
            for mesure in root.findall(".//OneMesureAF1I"):
                # Récupération du nom du point (ID)
                #point_id = mesure.find("NamePt").text
                
                # Récupération des coordonnées (PtIm)
                coord_text = mesure.find("PtIm").text
                x, y = map(float, coord_text.split())  # Convertir les coordonnées en float
                '''
                # Ajout des informations dans la liste
                points.append({
                    "id": point_id,
                    "x": x,
                    "y": y
                })
                '''
                points.append([x, y])
            return points
        except ET.ParseError as e:
            print(f"Erreur lors du parsing du fichier XML : {e}")
            return []
        except Exception as e:
            print(f"Erreur inattendue : {e}")
            return []
        

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    
    # Retrieve arguments
    parser = argparse.ArgumentParser(description="Saisie des points fiduciaux")
    
    parser.add_argument("--image_name", help="Nom de l'image d'entrée.", required=True)
    parser.add_argument("--output_file", help="Nom du fichier de sortie.", required=True)
    parser.add_argument("--flag", help="indicateur si 1ère image ou re-saisie.", required=True)
                        
    parser.add_argument("--input_file", help="fichier de points image1.", required=False)           
    
    parser.add_argument('--scripts', help='Répertoire du chantier', required=False)
    parser.add_argument('--TA', help='Fichier TA du chantier', required=False)
    parser.add_argument('--nb_fiducial_marks', help='Nombre de repères de fond de chambre', required=False)
    parser.add_argument('--scan_resolution', help='résolution du scannage de la photo argentique', required=False)
    parser.add_argument('--remove_artefacts', help="Présence d'artefacts", required=False)
    parser.add_argument('--targets', help='Utiliser Yolo pour détecter les cibles', required=False)
    parser.add_argument('--apply_threshold', help='faire la recherche de repères de fons de chambre sur les images seuillées', required=False)
    
    args = parser.parse_args()
    
    image_path = args.image_name
    out_xml = args.output_file
    flag = args.flag.lower() in ("true", "1", "yes")
    if hasattr(args, 'input_file') and args.input_file:  # Vérifie l'existence et la valeur
        in_xml = args.input_file
    else:
        in_xml = None
    
    '''    
    # Path to the input image
    #image_path = "IGNF_PVA_1-0__1978-07-28__C2716-0031_1978_F2616-2716_0034.tif" #cible
    #Timage_path = "IGNF_PVA_1-0__1967__C2720-0061_1967_CDP5468_0795.tif" #mini_cible bande blanche
    #image_path = "IGNF_PVA_1-0__1960-03-19__C2729-0131_1960_FR184_0012.tif" # trait
    image_path = "IGNF_PVA_1-0__1960-03-19__C2729-0131_1960_FR184_0013.tif" #trait2
    out_xml = "output_pointsim2.xml"
    flag = True
    in_xml = "output_points.xml"
    '''
    window = ImageZoomer(image_path, out_xml, flag, in_xml)
    window.show()
    sys.exit(app.exec_())
