import argparse
from math import sqrt
import os

parser = argparse.ArgumentParser(description="Analyse du rapport de CenterBascule pour vérifier qu'il n'y a pas de problèmes lors du passage en coordonnées absolues approximatives")

parser.add_argument('--input_report', help='Rapport CenterBascule')
args = parser.parse_args()



def find_problem(chemin_rapport):
    distance_max = 0
    image_distance_min = ""

    with open(chemin_rapport, "r") as f:
        for line in f:
            if "Basc-Residual" in line:
                line_splitted = line.split()
                coordinate = line_splitted[2].replace("[", "").replace("]", "")
                coordinate_splitted = coordinate.split(",")
                dx = float(coordinate_splitted[0])
                dy = float(coordinate_splitted[1])
                dz = float(coordinate_splitted[2])
                distance = sqrt(dx**2 + dy**2 + dz**2)
                if distance > distance_max:
                    distance_max = distance
                    image_distance_min = line_splitted[1]

    print("Le plus gros résidu concerne l'image {} : {} mètres".format(image_distance_min, distance_max))
    
    
    with open(os.path.join("reports", "rapport_complet.txt"), 'a') as f:
        f.write("Analyse de CenterBascule\n")
        f.write("Le plus gros résidu concerne l'image {} : {} mètres\n".format(image_distance_min, distance_max))
        f.write("\n\n\n")



if __name__ == "__main__":

    print("")
    print("Analyse du rapport Tapas")

    find_problem(args.input_report)
    print("")


    