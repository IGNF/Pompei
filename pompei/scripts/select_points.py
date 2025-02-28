"""
Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/

File main authors:
- Aymeric Bontoux
- Célestin Huet

This file is part of Pompei: https://github.com/IGNF/Pompei

Pompei is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Pompei is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Pompei. If not, see <https://www.gnu.org/licenses/>.
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QGraphicsView, QGraphicsScene, QMainWindow, 
    QWidget, QVBoxLayout, QSplitter
)
from PyQt5.QtGui import QPixmap, QPen, QCursor, QPainter
from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtCore import QEvent
import xml.etree.ElementTree as ET
import argparse
import numpy as np


class SelectPoints(QMainWindow):
    def __init__(self, image_path, output_path, flag, in_xml, nb_fiducial_marks):
        super().__init__()
        self.setWindowTitle("Saisie Repères de fonds de chambre")
        self.points = [] # list of selected points
        self.point_items = []  # Keep track of graphical items for points
        self.output_path = output_path
        self.nb_fiducial_marks = nb_fiducial_marks
        self.points_maitres = []
        self.flag = flag
        
        # Load the image
        self.pixmap = QPixmap(image_path)
        
        # Create a scene and add the image
        self.scene = QGraphicsScene()
        self.scene.addPixmap(self.pixmap)
        
        # Configure the view to display the scene
        self.view = QGraphicsView(self.scene, self)
        self.view.viewport().installEventFilter(self)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setSceneRect()
        
        # Create control buttons
        self.controls_widget = QWidget()
        self.controls_layout = QVBoxLayout(self.controls_widget)             
        
        if flag:
            self.points_maitres = self.read_xml(in_xml)
            self.nb_fiducial_marks = len(self.points_maitres)
        else:
            self.points_maitres = self.get_zooms()
            
        # Split the window into the view and the controls
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.view)
        self.splitter.addWidget(self.controls_widget)

        # Set the splitter as the central widget of the main window
        self.setCentralWidget(self.splitter)

        # Set the initial window size
        self.resize(1000, 1000)
        
        # Handle mouse clicks
        self.view.mousePressEvent = self.handle_mouse_press
        
        # Customize the cursor
        self.set_custom_cursor()


    def first_zoom(self):
        self.zoom_on_area(self.points_maitres[0][0],self.points_maitres[0][1])


    def setSceneRect(self):
        sceneRect = self.view.sceneRect()
        w = sceneRect.width()
        h = sceneRect.height()
        self.view.setSceneRect(-2*w, -2*h, 5*w, 5*h)


    def get_zooms(self):
        w0 = 0.1 * self.pixmap.width()
        h0 = 0.1 * self.pixmap.height()
        w2 = 0.9 * self.pixmap.width()
        h2 = 0.9 * self.pixmap.height()
        w1 = (w0+w2)/2
        h1 = (h0+h2)/2
        if self.nb_fiducial_marks==4:
            return [[w0,h0], [w2,h0],[w2,h2], [w0,h2]]
        elif self.nb_fiducial_marks==8:
            return [[w0,h0], [w1,h0], [w2,h0], [w2,h1], [w2,h2], [w1,h2], [w0,h2], [w0,h1]]
        else:
            return []

    def eventFilter(self, source, event):
        if (source == self.view.viewport() and event.type() == QEvent.Wheel):
                if event.angleDelta().y() > 0:
                    scale = 1.25
                else:
                    scale = .8
                self.view.scale(scale, scale)
                # do not propagate the event to the scroll area scrollbars
                return True
        return super().eventFilter(source,event)
        
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

        next_point = self.get_next_points()
        if next_point is not None:
            self.zoom_on_area(next_point[0], next_point[1])


    def get_next_points(self):
        liste_i = []
        for point in self.points:
            d_min = 1e10
            i_min = 0
            for i, pm in enumerate(self.points_maitres):
                d = np.sqrt((pm[0]-point[0])**2+(pm[1]-point[1])**2)
                if d < d_min:
                    d_min = d
                    i_min = i
            liste_i.append(i_min)

        liste_i = sorted(liste_i)
        for i in range(self.nb_fiducial_marks):
            if len(liste_i) <= i or i != liste_i[i]:
                return self.points_maitres[i]
        return None

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
    

    def zoom_on_area(self, x, y):
        """
        Define the zoom rectangle based on coordinates and zoom factor

        Args:
            x (float): x coodinate of the top-left corner of the zoom rectangle 
            y (float): y coodinate of the top-left corner of the zoom rectangle
        """

        # Pour la ressaisie, on sait plus précisément où se trouvent les points, donc on peut zoomer plus précisément
        if self.flag:
            size = 200
        else:
            size = 1000

        zoom_rect = QRectF(
            x-size/2, 
            y-size/2, 
            size,
            size
        )        
        # Adjust the view to show only the zoomed rectangle
        self.view.fitInView(zoom_rect, mode=Qt.AspectRatioMode.KeepAspectRatio)
     
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

    def sort_points(self):
        """
        Dans le cas de la ressaisie, remet dans le bon ordre les points saisis pour qu'ils correspondent à l'ordre des points saisis sur l'image maîtresse
        """
        points_ordered = []
        for point_maitre in self.points_maitres:
            d_min = 1e10
            point_min = self.points[0]
            for point in self.points:
                distance = np.sqrt((point_maitre[0]-point[0])**2+(point_maitre[1]-point[1])**2)
                if distance < d_min:
                    d_min = distance
                    point_min = point
            points_ordered.append(point_min)
        self.points = points_ordered
    
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

        # S'il s'agit de la ressaisie de points, on met les points saisis dans le même ordre que les points maitres
        if self.flag:
            self.sort_points()
       
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
    parser.add_argument('--nb_fiducial_marks', help='Nombre de repères de fond de chambre', required=False, type=int)
    args = parser.parse_args()
    
    image_path = args.image_name
    out_xml = args.output_file
    flag = args.flag.lower() in ("true", "1", "yes")
    nb_fiducial_marks = args.nb_fiducial_marks
    if hasattr(args, 'input_file') and args.input_file:  # Check existence and value
        in_xml = args.input_file
    else:
        in_xml = None
    

    window = SelectPoints(image_path, out_xml, flag, in_xml, nb_fiducial_marks)
    window.show()
    window.first_zoom()
    sys.exit(app.exec_())
    
