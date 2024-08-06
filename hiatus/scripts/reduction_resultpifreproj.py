import argparse
import shutil

parser = argparse.ArgumentParser(description="Suppression d'un point sur quatre")
parser.add_argument('--input_resultpifreproj', default='', help='Dossier MEC-Malt')
args = parser.parse_args()

shutil.copy(args.input_resultpifreproj, "resultpifreproj_save")

with open("resultpifreproj_save", "r") as f:
    with open(args.input_resultpifreproj, "w") as f2:
        compte = 0
        for line in f:
            if compte%4==0:
                f2.write(line)
            compte += 1

