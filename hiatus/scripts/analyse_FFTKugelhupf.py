import argparse
import os
from lxml import etree

parser = argparse.ArgumentParser(description='Analyse du rapport de FFTKugelhupf pour vérifier que tous les repères de fond de chambre ont été trouvés')

parser.add_argument('--input_rapport', help='Rapport FFTKugelhupf')
args = parser.parse_args()



def find_problem(chemin_rapport):
    liste_probleme = []

    with open(chemin_rapport, "r") as f:
        for line in f:
            line_splitted = line.split()
            if line_splitted[0] == "RESIDU":
                value = float(line_splitted[2])
                if value > 20:
                    name_splitted = line_splitted[4].split("_")
                    if name_splitted[-1] != "Masq.tif":
                        print("Attention : le résidu de l'image {} est trop élevé : {}".format(line_splitted[4], value))
                        liste_probleme.append(line_splitted[4])
    return liste_probleme

def SaisieAppuisInit(liste_probleme):
    for image in liste_probleme:
        commande = "mm3d SaisieAppuisInit {} NONE id_reperes.txt MeasuresIm-{}.xml Gama=2".format(image, image)
        os.system(commande)

def SaisieAppuisInit_to_InterneScan(liste_probleme):
    for image in liste_probleme:
        MesureAppui = etree.Element("MesureAppuiFlottant1Im")
        idReperes = etree.SubElement(MesureAppui, "NameIm")
        idReperes.text = image

        PrecPointeByIm = etree.SubElement(MesureAppui, "PrecPointeByIm")
        PrecPointeByIm.text = str(0.5)



        listRep=[]
        listPtImCoor=[]
        #On parcourt les fichiers contenant les positions des repères de fond de chambre
        xml_file = "MeasuresIm-{}-S2D.xml".format(image)
        tree = etree.parse(xml_file)
        root = tree.getroot()
        #On récupère la position des points
        for PtIm in root.getiterator("PtIm"):
            listPtImCoor.append(PtIm.text)

        #On récupère le nom des points
        for NamePt in root.getiterator("NamePt"):
            listRep.append(NamePt.text)


        for i in range(len(listRep)):        
            OneMesure = etree.SubElement(MesureAppui, "OneMesureAF1I")
            NamePt = etree.SubElement(OneMesure, "NamePt")
            NamePt.text=listRep[i]
            PtIm = etree.SubElement(OneMesure, "PtIm")
            PtIm.text=listPtImCoor[i]


        with open("Ori-InterneScan/MeasuresIm-{}.xml".format(image),"w") as f:
            f.write("<?xml version=\"1.0\" ?>\n")
            f.write(str(etree.tostring(MesureAppui,encoding='unicode')))



if __name__ == "__main__":

    liste_probleme = find_problem(args.input_rapport)
    SaisieAppuisInit(liste_probleme)
    SaisieAppuisInit_to_InterneScan(liste_probleme)

    