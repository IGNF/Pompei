repertoire_scripts=$1
repertoire_chantier=$2
CPU=$3


#Calcul d'une première orthophoto
echo "Malt"
mm3d Malt Ortho OIS.*tif TerrainFinal_10_10_0.5_AllFree_Final MasqImGlob=filtre.tif NbVI=2 UseTA=0 NbProc=30 EZA=1 DirMEC=MEC-Malt-Final >> logfile

echo "Tawny"
mm3d Tawny Ortho-MEC-Malt-Final/ RadiomEgal=false >> logfile

python ${repertoire_scripts}/create_Z_Num_tfw.py --input_Malt MEC-Malt-Final


sh ${repertoire_scripts}/radiometrie.sh ${repertoire_scripts} ${CPU}

sh ${repertoire_scripts}/build_vrt.sh ${repertoire_scripts} metadata

sh ${repertoire_scripts}/mise_en_forme_resultat.sh