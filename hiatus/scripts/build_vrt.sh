repertoire_scripts=$1
metadata=$2

#On calcul le MNS
echo "Calcul du MNS"
echo ${repertoire_scripts}
python ${repertoire_scripts}/create_Z_Num_tfw.py --input_Malt MEC-Malt-Final
python ${repertoire_scripts}/build_mns_micmac.py --input_Malt MEC-Malt-Final  >> logfile

cd MEC-Malt-Final
mkdir -p mns_sans_masque
mv MNS_Final_Num8_DeZoom2_STD-MALT* mns_sans_masque/
mv MNS_Final_Num9_DeZoom2_STD-MALT* mns_sans_masque/
cd ..
#On applique le masque sur le MNS historique et on l'enregistre en Lambert 93
python ${repertoire_scripts}/appliquer_masque.py --orthoHistoPath MEC-Malt-Final/mns_sans_masque/  --orthoHistoResultPath  MEC-Malt-Final/ --masque MEC-Malt-Final/Masq_STD-MALT_DeZoom2.tif --metadata ${metadata}
#On calcule la différence de MNS entre le MNS historique et le MNS actuel
python ${repertoire_scripts}/soustraction.py --mnsHistoPath MEC-Malt-Final/  --mnsPath  ${metadata}/mns/ --masque MEC-Malt-Final/Masq_STD-MALT_DeZoom2.tif --metadata ${metadata}

cd Ortho-MEC-Malt-Final-Corr
mkdir ortho_sans_masque
mv Orthophotomosaic_Tile*.tif ortho_sans_masque
mv Orthophotomosaic_Tile*.tif.ovr ortho_sans_masque
cp Orthophotomosaic_Tile*.tfw ortho_sans_masque
cd ..
#On applique le masque aux dalles de l'orthophoto historique et on l'enregistre en Lambert 93
python ${repertoire_scripts}/appliquer_masque.py --orthoHistoPath Ortho-MEC-Malt-Final-Corr/ortho_sans_masque/  --orthoHistoResultPath  Ortho-MEC-Malt-Final-Corr/ --masque MEC-Malt-Final/Masq_STD-MALT_DeZoom1.tif --metadata ${metadata}


cd MEC-Malt-Final/
ls MNS*.tif > malsite
for i in `cat malsite` ; do gdaladdo -ro ${i} 8 16 ; done
rm malsite
cd ..

if test ! -f Ortho-MEC-Malt-Final/Orthophotomosaic_Tile_0_0.tif; then
    cp  Ortho-MEC-Malt-Final/Orthophotomosaic.tif Ortho-MEC-Malt-Final/Orthophotomosaic_Tile_0_0.tif
    cp  Ortho-MEC-Malt-Final/Orthophotomosaic.tfw Ortho-MEC-Malt-Final/Orthophotomosaic_Tile_0_0.tfw
fi

if test ! -f Ortho-MEC-Malt-Final-Corr/Orthophotomosaic_Tile_0_0.tif; then
    cp  Ortho-MEC-Malt-Final-Corr/Orthophotomosaic.tif Ortho-MEC-Malt-Final-Corr/Orthophotomosaic_Tile_0_0.tif
    cp  Ortho-MEC-Malt-Final-Corr/Orthophotomosaic.tfw Ortho-MEC-Malt-Final-Corr/Orthophotomosaic_Tile_0_0.tfw
fi

for k in Ortho-MEC-Malt-Final Ortho-MEC-Malt-Final-Corr ; do 
cd ${k}
ls Orthophot*Tile*.tif > malsite
for i in `cat malsite` ; do gdaladdo -r average -ro ${i} 8 16 ; done
rm malsite

#On construit le vrt sur l'ortho historique
gdalbuildvrt Orthophotomosaic.vrt Orthoph*Tile*tif
cd ..
done

