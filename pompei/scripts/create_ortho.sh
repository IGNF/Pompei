#Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/
#
#File main authors:
#- Célestin Huet
#This file is part of Pompei: https://github.com/IGNF/Pompei
#
#Pompei is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#Pompei is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#You should have received a copy of the GNU General Public License along with Pompei. If not, see <https://www.gnu.org/licenses/>.

set -e

scripts_dir=$1
TA=$2
ortho=$3
CPU=$4
delete=$5

if test ${delete} -eq 1; then
    rm -rf Tmp-MM-Dir
fi

# Création d'un nouveau fichier TA avec les orientations et focales mises à jour.
echo "Création du fichier TA_xml_updated.xml"
python ${scripts_dir}/convert_ori_ta.py --ta_xml ${TA} --ori Ori-TerrainFinal_10_10_0.5_AllFree_Final  --imagesSave imagesWithoutDistorsion  --result TA_xml_updated.xml  

# On récupére le MNT de la zone
echo "Récupération du MNT"
python ${scripts_dir}/download_mnt.py --ortho ${ortho}


echo "Création d'une ortho pour chaque image OIS-Reech"
python ${scripts_dir}/create_orthos_OIS_Reech.py --mnt metadata/mnt/mnt.vrt --ori Ori-TerrainFinal_10_10_0.5_AllFree_Final --outdir ortho_mnt --cpu ${CPU} --ta ${TA}

echo "Egalisation radiométrique"
sh ${scripts_dir}/equalizate_radiometry_ortho_mnt.sh ${scripts_dir} ${CPU} radiom_ortho_mnt ortho_mnt >> logfile

if test ${delete} -eq 1; then
    rm -rf ortho_mns/Incid*
fi

echo "Calcul de la mosaïque"
python ${scripts_dir}/mosaiquage.py --ori Ori-TerrainFinal_10_10_0.5_AllFree_Final --cpu ${CPU} --metadata metadata --mosaic ortho_mnt/mosaic.gpkg --ortho ortho_mnt --ta ${TA}

echo "Création de l'ortho sur mnt"
python ${scripts_dir}/create_big_Ortho.py --ori Ori-TerrainFinal_10_10_0.5_AllFree_Final --cpu ${CPU} --mnt metadata/mnt/mnt.vrt --outdir ortho_mnt --radiom radiom_ortho_mnt --mosaic ortho_mnt/mosaic.gpkg --ta ${TA}

echo "Création de fichiers vrt"
# On crée un fichier vrt sur les orthos et le graphe de mosaïquage
gdalbuildvrt ortho_mnt/ortho.vrt ortho_mnt/*_ortho.tif