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
metadata=$2

#On calcul le MNS
echo "Calcul du MNS"
echo ${scripts_dir}
python ${scripts_dir}/create_Z_Num_tfw.py --input_Malt MEC-Malt-Final
python ${scripts_dir}/build_mns_micmac.py --input_Malt MEC-Malt-Final  >> logfile

cd MEC-Malt-Final
mkdir -p mns_sans_masque
mv MNS_Final_Num8_DeZoom2_STD-MALT* mns_sans_masque/
cd ..
#On applique le masque sur le MNS historique et on l'enregistre en Lambert 93
python ${scripts_dir}/apply_mask.py --orthoHistoPath MEC-Malt-Final/mns_sans_masque/  --orthoHistoResultPath  MEC-Malt-Final/ --masque MEC-Malt-Final/Masq_STD-MALT_DeZoom2.tif --metadata ${metadata}
#On calcule la différence de MNS entre le MNS historique et le MNS actuel
python ${scripts_dir}/compute_MNS_diff.py --mnsHistoPath MEC-Malt-Final/  --mnsPath  ${metadata}/mns/ --masque MEC-Malt-Final/Masq_STD-MALT_DeZoom2.tif --metadata ${metadata}

cd Ortho-MEC-Malt-Final-Corr
mkdir ortho_sans_masque
mv Orthophotomosaic_Tile*.tif ortho_sans_masque
mv Orthophotomosaic_Tile*.tif.ovr ortho_sans_masque
cp Orthophotomosaic_Tile*.tfw ortho_sans_masque
cd ..
#On applique le masque aux dalles de l'orthophoto historique et on l'enregistre en Lambert 93
python ${scripts_dir}/apply_mask.py --orthoHistoPath Ortho-MEC-Malt-Final-Corr/ortho_sans_masque/  --orthoHistoResultPath  Ortho-MEC-Malt-Final-Corr/ --masque MEC-Malt-Final/Masq_STD-MALT_DeZoom1.tif --metadata ${metadata}


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

