import argparse
import os

parser = argparse.ArgumentParser(description="Analyse du rapport de ReSampFid pour vérifier qu'il n'y a pas de problèmes lors du rééchantillonnage des images")

parser.add_argument('--input_report', help='Rapport ReSampFid')
args = parser.parse_args()



def find_problem(chemin_rapport):

    with open(chemin_rapport, "r") as f:
        residu_max = 0
        image_residu_max = ""
        for line in f:
            if "RESIDU" in line:
                line_splitted = line.split()
                residu = float(line_splitted[3])
                if residu > residu_max:
                    residu_max = residu
                    image_residu_max = line_splitted[1]
    print("Le résidu le plus élevé est celui de l'image {} : {}".format(image_residu_max, residu_max))

    with open(os.path.join("reports", "rapport_complet.txt"), 'a') as f:
        f.write("Analyse de ReSampFid\n")
        f.write("Le résidu le plus élevé est celui de l'image {} : {}\n".format(image_residu_max, residu_max))
        f.write("\n\n\n")



if __name__ == "__main__":

    print("")
    print("Analyse du rapport ReSampFid")

    find_problem(args.input_report)
    print("")


    