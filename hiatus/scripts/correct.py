import argparse


parser = argparse.ArgumentParser(description="Correction du fichier coef_reetal_walis.txt")
parser.add_argument('--chemin', help="Répertoire du chantier")
args = parser.parse_args()



x0_float = None
x1_float = None
with open(args.chemin, "r") as f:
    for line in f:
        line_splitted = line.split()
        if len(line) ==2:
            x0 = line_splitted[0]
            x1 = line_splitted[1]
            try:
                x0_float = float(x0)
                x1_float = float(x1)
                break
            except:
                pass

if x0_float is not None and x1_float is not None:
    with open(args.chemin, "w") as f:
        f.write("{} {}".format(x0_float, x1_float))