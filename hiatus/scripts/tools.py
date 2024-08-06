import os


def getEPSG(metadata):
    with open(os.path.join(metadata, "EPSG.txt"), "r") as f:
        for line in f:
            return int(line)

def load_bbox(metadata):
    #Charge la bounding box créée lorsqu'on a lancé sh.visualisation.sh
    bbox = []
    with open(os.path.join(metadata, "bbox.txt"), "r") as f:
        for line in f:
            bbox.append(float(line.strip()))
    return bbox

def getNbCouleurs(metadata):
    with open(os.path.join(metadata, "nbCouleurs.txt"), "r") as f:
        for line in f:
            return int(line)

def getResolution():
    path = os.path.join("Ortho-MEC-Malt-Abs-Ratafia", "Orthophotomosaic.tfw")
    if not os.path.exists(path):# Cas de hiatus_rapide.sh
        path = os.path.join("metadata", "resolution.txt")
    if not os.path.exists(path):
        raise Exception("Impossible de récupérer la résolution du chantier")
    
    with open(path, "r") as f:
        for line in f:
            resolution = float(line)
            print("Résolution du chantier : {} mètres".format(resolution))
            return float(resolution)
