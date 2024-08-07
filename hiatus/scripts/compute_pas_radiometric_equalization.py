"""
Calcule le pas pour le calcul des paramètres de l'égalisation radiométrique.

Le pas est en mètres. Le risque, c'est que ce soit interminable pour des chantiers avec une résolution de l'ordre de 2 mètres, ou que même le calcul n'ait pas assez de points pour des chantiers à haute résolution.
"""

import os
from tools import getResolution

resolution = getResolution()

with open(os.path.join("metadata", "pas_egalisation_radiometrique.txt"), "w") as f:
    f.write(str(int(resolution*100/0.5))) # le pas d'un chantier à 50 centimètres de résolution est de 100 mètres, puis on applique une proportionnalité