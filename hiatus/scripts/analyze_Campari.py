import argparse
import os
from lxml import etree

parser = argparse.ArgumentParser(description="Analyse du rapport de Campari pour vérifier qu'il n'y a pas de problèmes lors du calcul de l'orientation absolue")

parser.add_argument('--input_report', help='Rapport Campari')
args = parser.parse_args()



def find_problem(chemin_rapport):
    line_residual = ""
    line_worst = ""   

    with open(chemin_rapport, "r") as f:
        for line in f:
            if "Residual" in line:
                line_residual = line
            if "Worst" in line:
                line_worst = line

    print(line_residual)
    print(line_worst)


    with open(os.path.join("reports", "rapport_complet.txt"), 'a') as f:
        f.write("Analyse de Campari\n")
        f.write(line_residual)
        f.write(line_worst)
        f.write("\n\n\n")


if __name__ == "__main__":

    print("")
    print("Analyse du rapport Campari")

    find_problem(args.input_report)
    print("")


    