#Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/
#
#File main authors:
#- Célestin Huet
#- Arnaud Le Bris
#This file is part of Hiatus: https://github.com/IGNF/Hiatus
#
#Hiatus is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#Hiatus is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#You should have received a copy of the GNU General Public License along with Hiatus. If not, see <https://www.gnu.org/licenses/>.


scripts_dir=$1
CPU=$2


#Calcul de l'orthophoto
# On passe à Malt un MNS sous-échantillonné pour qu'il sache à quelle altitude chercher. Cela permet d'améliorer un peu la reconstruction du MNS dans les zones de montagne
echo "Malt"
mm3d Malt Ortho OIS.*tif TerrainFinal_10_10_0.5_AllFree_Final MasqImGlob=filtre.tif NbVI=2 UseTA=0 NbProc=${CPU} EZA=1 DirMEC=MEC-Malt-Final DEMInitIMG=metadata/mns/MNS_ssech4.tif DEMInitXML=metadata/mns/MNS_ssech4.xml >> logfile

echo "Tawny"
mm3d Tawny Ortho-MEC-Malt-Final/ RadiomEgal=false >> logfile

python ${scripts_dir}/create_Z_Num_tfw.py --input_Malt MEC-Malt-Final


sh ${scripts_dir}/equalize_radiometry.sh ${scripts_dir} ${CPU}

sh ${scripts_dir}/build_vrt.sh ${scripts_dir} metadata

sh ${scripts_dir}/format_results.sh