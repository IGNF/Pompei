# -*- coding: utf-8 -*-
"""
Created on Sat Dec 21 12:43:45 2024

@author: abont
"""

import sys

from PyQt5.QtWidgets import (
    QApplication, QGraphicsView, QGraphicsScene, QMainWindow, 
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSplitter
)
from PyQt5.QtGui import QPixmap, QImage, QPen, QCursor, QPainter, QColor
from PyQt5.QtCore import QRectF, Qt

import xml.etree.ElementTree as ET

import argparse

import numpy as np


class SelectPoints(QMainWindow):
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
        width = 900 # initialisation of width window
        height = 800  # initialisation of height window
        
        # Create a scene and add the image
        self.scene = QGraphicsScene()
        self.scene.addPixmap(self.pixmap)
        
        # Configure the view to display the scene
        self.view = QGraphicsView(self.scene, self)
        
        # Create control buttons
        self.controls_widget = QWidget()
        self.controls_layout = QVBoxLayout(self.controls_widget)
        
        if not flag:                  
            # Add buttons
            self.zoom_top_left_button = QPushButton("Zoom Haut-Gauche", self)
            self.zoom_top_right_button = QPushButton("Zoom Haut-Droite", self)
            self.zoom_bottom_left_button = QPushButton("Zoom Bas-Gauche", self)
            self.zoom_bottom_right_button = QPushButton("Zoom Bas-Droite", self)
            
            self.zoom_medium_top = QPushButton("Zoom Milieu-Haut", self)
            self.zoom_medium_right = QPushButton("Zoom Milieu-Droite", self)
            self.zoom_medium_bottom = QPushButton("Zoom Milieu-Bas", self)
            self.zoom_medium_left = QPushButton("Zoom Milieu-Gauche", self)
            
            # find border
            array = self.pixmap_to_numpy(self.pixmap)
            row, column = self.analyze_lines_and_columns(array, threshold=15)
            top_border, bottom_border = self.find_border(row, self.pixmap.height()/2)
            left_border, right_border = self.find_border(column, self.pixmap.width()/2)
            print(top_border, self.pixmap.width()-right_border, self.pixmap.height()- bottom_border, left_border)
            
            # Connect buttons to zoom function
            self.zoom_top_left_button.clicked.connect(
                lambda: self.zoom_on_area(left_border, top_border))
            self.zoom_top_right_button.clicked.connect(
                lambda: self.zoom_on_area(right_border-width, top_border))
            self.zoom_bottom_left_button.clicked.connect(
                lambda: self.zoom_on_area(left_border, bottom_border-height))
            self.zoom_bottom_right_button.clicked.connect(
                lambda: self.zoom_on_area(right_border-width, bottom_border-height))

            self.zoom_medium_top.clicked.connect(
                lambda: self.zoom_on_area(self.pixmap.width()/2 - width/2, top_border))
            self.zoom_medium_right.clicked.connect(
                lambda: self.zoom_on_area(right_border, self.pixmap.height()/2 - height/2))
            self.zoom_medium_bottom.clicked.connect(
                lambda: self.zoom_on_area(self.pixmap.width()/2 - width/2, bottom_border))
            self.zoom_medium_left.clicked.connect(
                lambda: self.zoom_on_area(left_border, self.pixmap.height()/2 - height/2))

            # Add buttons to the layout
            self.controls_layout.addWidget(self.zoom_top_left_button)
            self.controls_layout.addWidget(self.zoom_medium_top)
            self.controls_layout.addWidget(self.zoom_top_right_button)
            self.controls_layout.addWidget(self.zoom_medium_right)
            self.controls_layout.addWidget(self.zoom_bottom_right_button)
            self.controls_layout.addWidget(self.zoom_medium_bottom)
            self.controls_layout.addWidget(self.zoom_bottom_left_button)
            self.controls_layout.addWidget(self.zoom_medium_left)
        
            # Add flexible space      
            self.controls_layout.addStretch()
        
        if flag:
            list_points = np.array(self.read_xml(in_xml))
            print(list_points)
            print(len(list_points))
            
            n = len(list_points)
            for i in range(n):
                
                def call_zoom(x, list_points):
                    ''' intermediate function to capture current value of `i` '''
                    return lambda: self.zoom_on_area(
                        list_points[x, 0] - width / 2,
                        list_points[x, 1] - height / 2
                    )

                button = QPushButton(f"Zoom {i+1}", self)  # Create buttons            
                button.clicked.connect(call_zoom(i, list_points)) # Connect buttons to zoom function            
                self.controls_layout.addWidget(button)  # Add buttons to the layout
                
            self.controls_layout.addStretch()  # Add flexible space
            
        # Split the window into the view and the controls
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.view)
        self.splitter.addWidget(self.controls_widget)

        # Set the splitter as the central widget of the main window
        self.setCentralWidget(self.splitter)

        # Set the initial window size
        self.resize(width + 200, height)

        # Initialize zoom
        self.zoom_on_area(self.pixmap.width()/2, self.pixmap.height()/2)  # Centre image
        
        # Handle mouse clicks
        self.view.mousePressEvent = self.handle_mouse_press
        
        # Customize the cursor
        self.set_custom_cursor()
        
    def set_custom_cursor(self):
        """
        Create a cross cursor
        """
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
        """ 
        Analyze the mouse click 

        Args:
            event: detection of click
        """
        scene_pos = self.view.mapToScene(event.pos())
        if event.button() == Qt.LeftButton:
            self.add_point(scene_pos)
        elif event.button() == Qt.RightButton:
            self.remove_point(scene_pos)

    def add_point(self, scene_pos):
        """
        Add a new point at the clicked position 

        Args:
            scene_pos: mouse position
        """
        self.points.append((scene_pos.x(), scene_pos.y()))
        print(f"Point added: {scene_pos.x()}, {scene_pos.y()}")

        # Add a visual marker for the point
        pen = QPen(Qt.red)
        point_item = self.scene.addEllipse(scene_pos.x() - 2, scene_pos.y() - 2, 4, 4, pen)
        self.point_items.append(point_item)

    def remove_point(self, scene_pos):
        """ 
        Remove point if the click is near an existing point 

        Args:
            scene_pos: mouse position
        """
        tolerance = 10  # Radius around the point
        for i, (x, y) in enumerate(self.points):
            if abs(scene_pos.x() - x) <= tolerance and abs(scene_pos.y() - y) <= tolerance:
                # Remove the point and its marker
                print(f"Point removed: {x}, {y}")
                self.points.pop(i)
                point_item = self.point_items.pop(i)
                self.scene.removeItem(point_item)
                break  # Only remove one point

    
    def pixmap_to_numpy(self, pixmap):
        """
        Convert a QPixmap to a NumPy array

        Args:
            pixmap (pixmap): representation of the image per pixel

        Returns:
            arr (array): array of pixel
        """
        qimage = pixmap.toImage()
        qimage = qimage.convertToFormat(QImage.Format_RGBA8888)
        width = qimage.width()
        height = qimage.height()
        
        ptr = qimage.bits()
        ptr.setsize(qimage.byteCount())
        arr = np.array(ptr, dtype=np.uint8).reshape((height, width, 4))  # RGBA format
        return arr
    

    def analyze_lines_and_columns(self, image_array, threshold=15):
        """
        Analyze the rows and columns of an image to find lines/columns that are:
        - Majorly black (most pixel values close to 0)
        - Majorly white (most pixel values close to 255)
        - Very homogeneous (standard deviation below a threshold)
        - Composed mostly of black and white pixels (e.g., >90% black+white)

        Args:
            image_array (array): array of pixel
            threshold (int): threshold on the standard deviation of a row or column

        Returns:
            bad_raw (list): list of black/white/Homogeneous lines
            bad_column (list): list of black/white/Homogeneous column
        """
        # Convert RGBA to grayscale
        grayscale = np.mean(image_array[:, :, :3], axis=2)  # Ignore alpha channel
        total_pixels = grayscale.shape[1]  
        pixel_threshold = 0.85 * total_pixels  
        
        # Analyze rows
        bad_row = []
        for i, row in enumerate(grayscale):
            black_pixels = np.sum(row < 15)  # Count nearly black pixels
            white_pixels = np.sum(row > 240)  # Count nearly white pixels
            total_black_white = black_pixels + white_pixels  # Total black + white pixels
            if black_pixels >= pixel_threshold or white_pixels >= pixel_threshold:  # Mostly black or white
                bad_row.append(i)
            elif total_black_white >= pixel_threshold:  # Mostly black + white combined
                bad_row.append(i)
            elif np.std(row) < threshold:  # Homogeneous
                bad_row.append(i)
        
        # Analyze columns
        bad_column = []
        for j, col in enumerate(grayscale.T):  # Transpose to iterate columns as rows
            black_pixels = np.sum(col < 15)  
            white_pixels = np.sum(col > 240)  
            total_black_white = black_pixels + white_pixels  
            if black_pixels >= pixel_threshold or white_pixels >= pixel_threshold:  
                bad_column.append(j)
            elif total_black_white >= pixel_threshold:  
                bad_column.append(j)
            elif np.std(col) < threshold:  
                bad_column.append(j)
        
        return bad_row, bad_column

    def find_border(self, list_results, center):
        """
        Retrieve the analysis indices which are closest to the center => image border

        Args:
            list_results (list): list of black/white/Homogeneous lines or column
            center (float): coordinate of the center of the image

        Returns:
            closest_left (float): left or top border
            closest_right (float): right or bottom border
        """
        left_indices = [idx for idx in list_results if idx < center]
        closest_left = max(left_indices) if left_indices else None  # None si aucun
    
        right_indices = [idx for idx in list_results if idx >= center]
        closest_right = min(right_indices) if right_indices else None  # None si aucun
    
        return closest_left, closest_right
    

    def zoom_on_area(self, x, y, zoom_factor=1.4):
        """
        Define the zoom rectangle based on coordinates and zoom factor

        Args:
            x (float): x coodinate of the top-left corner of the zoom rectangle 
            y (float): y coodinate of the top-left corner of the zoom rectangle
            zoom_factor (float): zoom factor
        """
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
     
    def read_xml(self, name_xml):
        """
        Reads a measurement XML file

        Args:
            name_xml (String): path to XML file of image 1 (mode 1)

        Returns:
            points (list): list of coordinates of points.
        """
        try:
            # load XML file
            tree = ET.parse(name_xml)
            root = tree.getroot()
            
            points = []
            
            # Browse the “OneMesureAF1I” elements in the XML file
            for mesure in root.findall(".//OneMesureAF1I"):                
                coord_text = mesure.find("PtIm").text # coordinates (PtIm)
                x, y = map(float, coord_text.split())  # Convert coordinates to float
                points.append([x, y])
            return points
        except ET.ParseError as e:
            print(f"Erreur lors du parsing du fichier XML : {e}")
            return []
        except Exception as e:
            print(f"Erreur inattendue : {e}")
            return []
    
    def closeEvent(self, event):
        """
        create xml file with clicked points when the window is closed

        Args:
            event: detection of click
        """
        # First element
        root = ET.Element("SetOfMesureAppuisFlottants")

        # second element
        mesure_appui = ET.SubElement(root, "MesureAppuiFlottant1Im")

        # third element
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
        

if __name__ == "__main__":

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
    if hasattr(args, 'input_file') and args.input_file:  # Check existence and value
        in_xml = args.input_file
    else:
        in_xml = None
    
    '''    
    # Path to the input image
    #image_path = "IGNF_PVA_1-0__1978-07-28__C2716-0031_1978_F2616-2716_0034.tif" #cible
    #image_path = "IGNF_PVA_1-0__1967__C2720-0061_1967_CDP5468_0795.tif" #mini_cible bande blanche
    #image_path = "IGNF_PVA_1-0__1960-03-19__C2729-0131_1960_FR184_0012.tif" # trait
    image_path = "IGNF_PVA_1-0__1960-03-19__C2729-0131_1960_FR184_0013.tif" #trait2
    out_xml = "output_pointsim2.xml"
    flag = False
    in_xml = "output_points.xml"
    '''
    window = SelectPoints(image_path, out_xml, flag, in_xml)
    window.show()
    sys.exit(app.exec_())
