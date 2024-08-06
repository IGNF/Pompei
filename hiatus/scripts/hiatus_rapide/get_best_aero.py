import shutil
import os



"""
Sur les chantiers un peu compliqués, il est possible de ne pas pouvoir réussir à faire toutes les aéros.

Chaque aéro étant en théorie un peu plus précise, on récupère pour la suite la dernière aéro calculée avec succès
"""



for i in range(8, -1, -1):
    ori_dir = "Ori-Aero_{}".format(i)
    if os.path.isdir(ori_dir):
        if os.path.exists("Ori-TerrainFinal_10_10_0.5_AllFree_Final/"):
            shutil.rmtree("Ori-TerrainFinal_10_10_0.5_AllFree_Final/")
        shutil.copytree(ori_dir, "Ori-TerrainFinal_10_10_0.5_AllFree_Final/")
        break