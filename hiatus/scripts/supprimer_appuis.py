from lxml import etree
import numpy as np
import argparse
import os


parser = argparse.ArgumentParser(description="Suppression des points d'appuis les moins bons")
parser.add_argument('--appuis', help="Points d'appuis de la BD Ortho")
parser.add_argument('--S2D', help="Points d'appuis de l'orthomosaïque")
parser.add_argument('--appuis_save', help="Points d'appuis de la BD Ortho")
parser.add_argument('--S2D_save', help="Points d'appuis de l'orthomosaïque")
parser.add_argument('--rapportResidus', help="Rapport Campari sur les résidus")
parser.add_argument('--facteur', help="Seuil sur l'écart-type")
parser.add_argument('--supprimer', help="Supprimer les points d'appuis", type=bool, default=True)# Si false, permet de voir uniquement les écart-types et erreur sur les points d'appuis. Utile juste après la dernière aéro
args = parser.parse_args()

def lecture_appui_xml(path):
    liste_plani = []
    liste_alti = []
    
    tree = etree.parse(path)
    root = tree.getroot()
    liste_appuis = root.findall(".//OneAppuisDAF")
    
    for appui in liste_appuis:
        nomPoint = appui.find("NamePt").text
        incertitude = appui.find("Incertitude").text
        if "-1" in incertitude:
            liste_alti.append(nomPoint)
        else:
            liste_plani.append(nomPoint)
    return liste_alti, liste_plani


def lecture_rapport_residus(path, liste_plani):

    dict_appuis = []
    delta_plani = []
    delta_alti = []

    with open(path, "r") as f:
        for line in f:
            if "*APP" in line:
                line_splitted = line.split()
                nom_point = line_splitted[0][1:]
                ZTer = float(line_splitted[3])
                Zcomp = float(line_splitted[6])
                if nom_point in liste_plani:
                    XTer = float(line_splitted[1])
                    Xcomp = float(line_splitted[4])
                    YTer = float(line_splitted[2])
                    Ycomp = float(line_splitted[5])

                    delta = np.sqrt((XTer - Xcomp)**2 + (YTer - Ycomp)**2 + (ZTer - Zcomp)**2)
                    dict_appuis.append({"nom":nom_point, "delta":delta, "plani":True})
                    delta_plani.append(delta)
                else:
                    delta = np.abs(ZTer - Zcomp)
                    dict_appuis.append({"nom":nom_point, "delta":delta, "plani":False})
                    delta_alti.append(delta)
    return dict_appuis, delta_plani, delta_alti
                
def calcul_ecart_type(delta_plani):
    if len(delta_plani)>0:
        delta_numpy = np.array(delta_plani)
        return np.std(delta_numpy)
    return 0

def definir_suppression_point(dict_appuis, ecart_type_plani, ecart_type_alti, facteur):
    liste_points_a_supprimer = []
    compte_plani = 0
    compte_alti = 0
    for point in dict_appuis:
        if point["plani"]:
            if point["delta"] > ecart_type_plani * facteur:
                liste_points_a_supprimer.append(point["nom"])
                compte_plani += 1
        else:
            if point["delta"] > ecart_type_alti * facteur:
                liste_points_a_supprimer.append(point["nom"])
                compte_alti += 1
    print("Points plani supprimés : ", compte_plani)
    print("Points alti supprimés : ", compte_alti)
    print("Points supprimés : ", len(liste_points_a_supprimer))
    with open(os.path.join("rapports", "rapport_complet.txt"), 'a') as f:
        f.write("Points plani supprimés : {}\n".format(compte_plani))
        f.write("Points alti supprimés : {}\n".format(compte_alti))
        f.write("Points supprimés : {}\n".format(len(liste_points_a_supprimer)))
        f.write("\n\n\n")


    return liste_points_a_supprimer


def supprimer_appuis(liste_points_a_supprimer, path_appuis, path_appuis_save):
    tree = etree.parse(path_appuis)
    root = tree.getroot()
    liste_appuis = root.findall(".//OneAppuisDAF")
    
    #On supprime les points d'appuis qui sont dans la liste des points à supprimer
    for appui in liste_appuis:
        if appui.find("NamePt").text in liste_points_a_supprimer:
            appui.getparent().remove(appui)

    #On sauvegarde le fichier
    with open(path_appuis_save, "w") as f:
        f.write("<?xml version=\"1.0\" ?>\n")
        f.write(str(etree.tostring(tree, encoding='unicode')))

def supprimer_appuis_S2D(liste_points_a_supprimer, path_S2D, path_S2D_save):
    #On supprime les points d'appuis qui ont été supprimés dans appuis.xml
    tree = etree.parse(path_S2D)
    root = tree.getroot()

    for appui in root.findall(".//OneMesureAF1I"):
        nom_point = appui.find("NamePt").text
        if nom_point in liste_points_a_supprimer:
            appui.getparent().remove(appui)

    print("Nombre de points d'appuis restants : ")
    for mesureImage in root.findall(".//MesureAppuiFlottant1Im"):
        image = mesureImage.find(".//NameIm").text
        nb_points = len(mesureImage.findall(".//OneMesureAF1I"))
        print("{} : {}".format(image, nb_points))

    #On sauvegarde le fichier
    with open(path_S2D_save, "w") as f:
        f.write("<?xml version=\"1.0\" ?>\n")
        f.write(str(etree.tostring(tree, encoding='unicode')))


path_appuis_xml = args.appuis
path_appuis_save = args.appuis_save
path_rapport_residus = args.rapportResidus
path_S2D = args.S2D
path_S2D_save = args.S2D_save

facteur = float(args.facteur)

#On parcourt la liste des points d'appuis et on les sépare en deux catégories : ceux qui sont dépondérés en plani et les autres
liste_alti, liste_plani = lecture_appui_xml(path_appuis_xml)
print("Nombre de points alti : {}".format(len(liste_alti)))
print("Nombre de points plani : {}".format(len(liste_plani)))

#On calcule les résidus pour chaque point d'appui
dict_appuis, delta_plani, delta_alti = lecture_rapport_residus(path_rapport_residus, liste_plani)

#On calcule les écart-types pour les points plani et les points alti
ecart_type_plani = calcul_ecart_type(delta_plani)
ecart_type_alti = calcul_ecart_type(delta_alti)
print("Ecart-type des points plani : {} mètres".format(ecart_type_plani))
print("Ecart-type des points alti : {} mètres".format(ecart_type_alti))

with open(os.path.join("rapports", "rapport_complet.txt"), 'a') as f:
    f.write("Nombre de points plani : {}\n".format(len(liste_plani)))
    f.write("Nombre de points alti : {}\n".format(len(liste_alti)))
    f.write("Ecart-type des points plani : {} mètres\n".format(ecart_type_plani))
    f.write("Ecart-type des points alti : {} mètres\n".format(ecart_type_alti))


if args.supprimer:
    #On établit la liste des points d'appuis à supprimer 
    liste_points_a_supprimer = definir_suppression_point(dict_appuis, ecart_type_plani, ecart_type_alti, facteur)

    #On supprime les points d'appuis du fichier appuis.xml
    supprimer_appuis(liste_points_a_supprimer, path_appuis_xml, path_appuis_save)

    #On supprime les points d'appuis du fichier MesuresAppuis-S2D.xml
    supprimer_appuis_S2D(liste_points_a_supprimer, path_S2D, path_S2D_save)