#Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/
#
#File main authors:
#- Célestin Huet
#- Arnaud Le Bris
#This file is part of Pompei: https://github.com/IGNF/Pompei
#
#Pompei is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#Pompei is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#You should have received a copy of the GNU General Public License along with Pompei. If not, see <https://www.gnu.org/licenses/>.


scripts_dir=$1
CPU=$2
TA=$3

#Calcul de l'orthophoto


# Création des masques pour chaque image
python ${scripts_dir}/create_mask_per_image.py --TA ${TA}

# On passe à Malt un MNS sous-échantillonné pour qu'il sache à quelle altitude chercher. Cela permet d'améliorer un peu la reconstruction du MNS dans les zones de montagne
echo "Malt"
mm3d Malt Ortho "OIS.*([0-9]).tif" TerrainFinal_10_10_0.5_AllFree_Final MasqIm=Masq NbVI=2 UseTA=0 NbProc=${CPU} EZA=1 DirMEC=MEC-Malt-Final DEMInitIMG=metadata/mns/MNS_ssech4.tif DEMInitXML=metadata/mns/MNS_ssech4.xml >> logfile
rm OIS*Masq.tif

python ${scripts_dir}/create_Z_Num_tfw.py --input_Malt MEC-Malt-Final
python ${scripts_dir}/build_mns_micmac.py --input_Malt MEC-Malt-Final
python ${scripts_dir}/improve_mns.py --mns_input MEC-Malt-Final/MNS_pyramide.tif --indicateur MEC-Malt-Final/indicateur.tif --cpu ${CPU}

# Création d'un nouveau fichier TA avec les orientations et focales mises à jour.
echo "Création du fichier TA_xml_updated.xml"
python ${scripts_dir}/convert_ori_ta.py --ta_xml ${TA} --ori Ori-TerrainFinal_10_10_0.5_AllFree_Final  --imagesSave imagesWithoutDistorsion  --result TA_xml_updated.xml  


echo "Création d'une ortho pour chaque image OIS-Reech"
python ${scripts_dir}/create_orthos_OIS_Reech.py --mnt MEC-Malt-Final/MNS_Final.tif --ori Ori-TerrainFinal_10_10_0.5_AllFree_Final --outdir ortho_mns --cpu ${CPU} --mask MEC-Malt-Final/indicateur.tif --ta ${TA}

echo "Egalisation radiométrique"
sh ${scripts_dir}/equalizate_radiometry_ortho_mnt.sh ${scripts_dir} ${CPU} radiom_ortho_mns ortho_mns >> logfile

echo "Calcul de la mosaïque"
python ${scripts_dir}/mosaiquage.py --ori Ori-TerrainFinal_10_10_0.5_AllFree_Final --cpu ${CPU} --metadata metadata --mosaic ortho_mns/mosaic.gpkg --ortho ortho_mns --ta ${TA}

echo "Création de l'ortho vraie"
python ${scripts_dir}/create_big_Ortho.py --ori Ori-TerrainFinal_10_10_0.5_AllFree_Final --cpu ${CPU} --mnt MEC-Malt-Final/MNS_Final.tif --outdir ortho_mns --radiom radiom_ortho_mns --mosaic ortho_mns/mosaic.gpkg --ta ${TA}

echo "Création de fichiers vrt"
# On crée un fichier vrt sur les orthos et le graphe de mosaïquage
gdalbuildvrt ortho_mns/ortho.vrt ortho_mns/*_ortho.tif


python ${scripts_dir}/compute_MNS_diff.py --mnsHistoPath MEC-Malt-Final/  --mnsPath  metadata/mns/ --masque MEC-Malt-Final/Masq_STD-MALT_DeZoom2.tif --metadata metadata

mkdir ortho_mns/carte_correlation
mv MEC-Malt-Final/carte_interpolation.tif ortho_mns/carte_correlation/
mv MEC-Malt-Final/correlation.tif ortho_mns/carte_correlation/
mv MEC-Malt-Final/indicateur.tif ortho_mns/carte_correlation/
mv MEC-Malt-Final/MNS_Final*.tif ortho_mns/carte_correlation/
