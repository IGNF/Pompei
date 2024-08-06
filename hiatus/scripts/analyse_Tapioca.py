import argparse


parser = argparse.ArgumentParser(description="Analyse du rapport de Tapioca pour vérifier que tous les clichés disposent d'un nombre suffisant de points de liaison")

parser.add_argument('--input_rapport', help='Rapport Tapioca')
parser.add_argument('--output_rapport', help='Analyse du rapport Tapioca')
args = parser.parse_args()



def analyse(chemin_rapport):
    dictionnaire = {} 

    with open(chemin_rapport, "r") as f:
        for line in f:
            if "matches" in line and "points" in line:
                line_splitted = line.split()
                image1 = line_splitted[0]
                image2 = line_splitted[4]
                nb_pts = line_splitted[9]
                if not image1 in dictionnaire:
                    dictionnaire[image1] = {}
                dictionnaire[image1][image2] = nb_pts
            
    print(dictionnaire)
    return dictionnaire


def save(dictionnaire):
    with open(args.output_rapport, "w") as f:
        liste_images = dictionnaire.keys()
        liste_images_triees = sorted(liste_images)
        for image1 in liste_images_triees:
            f.write("Image : {}\n".format(image1))
            liste_images_image1 = dictionnaire[image1].keys()
            liste_images_image1_triees = sorted(liste_images_image1)
            for image2 in liste_images_image1_triees:
                f.write("        Image {} : {} points de liaison\n".format(image2, dictionnaire[image1][image2]))
            f.write("\n\n\n")




if __name__ == "__main__":

    print("")
    print("Analyse de {}".format(args.input_rapport))

    dictionnaire = analyse(args.input_rapport)
    save(dictionnaire)
    print("")


    