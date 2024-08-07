scripts_dir=$1
TA=$2
ortho=$3
CPU=$4

# Création d'un nouveau fichier TA avec les orientations et focales mises à jour.
echo "Création du fichier TA_xml_updated.xml"
python ${scripts_dir}/convert_ori_ta.py --ta_xml ${TA} --ori Ori-TerrainFinal_10_10_0.5_AllFree_Final  --imagesSave imagesWithoutDistorsion  --result TA_xml_updated.xml  

# On récupére le MNT de la zone
echo "Récupération du MNT"
python ${scripts_dir}/download_mnt.py --ortho ${ortho}


echo "Création d'une ortho pour chaque image OIS-Reech"
python ${scripts_dir}/create_orthos_OIS_Reech.py --ta_xml TA_xml_updated.xml --mnt metadata/mnt/mnt.vrt --ori Ori-TerrainFinal_10_10_0.5_AllFree_Final

echo "Egalisation radiométrique"
sh ${scripts_dir}/equalizate_radiometry_ortho_mnt.sh ${scripts_dir} ${CPU} >> logfile

echo "Création de l'ortho sur mnt"
python ${scripts_dir}/create_big_Ortho.py --ta_xml TA_xml_updated.xml --ori Ori-TerrainFinal_10_10_0.5_AllFree_Final

echo "Création de fichiers vrt"
# On crée un fichier vrt sur les orthos et le graphe de mosaïquage
gdalbuildvrt ortho_mnt/mosaic.vrt ortho_mnt/*_mosaic.tif
gdalbuildvrt ortho_mnt/ortho.vrt ortho_mnt/*_ortho.tif