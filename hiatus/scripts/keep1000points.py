import argparse
import random

parser = argparse.ArgumentParser(description="On conserve seulement 1000 points d'appuis aléatoirement, sinon le Ransac qui suit est interminable")
parser.add_argument('--file', help="Fichier contenant les points d'appuis")
args = parser.parse_args()

with open(args.file, "r") as f:
    points = []
    for line in f:
        points.append(line)

random.shuffle(points)

with open(args.file, "w") as f:
    for i in range(min(1000, len(points))):
        f.write(points[i])
