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

repertoire_Ortho_MEC_Malt=$1
scripts_dir=$2
CPU=$3

ls ${repertoire_Ortho_MEC_Malt}/Ort_*.tif > liste_cliches.txt


pasEgalisationRadiometrique=`cat ../metadata/pas_egalisation_radiometrique.txt`

#Nettoyage du fichier : on passe de "rep/Ort_nomcliche.tif" a "nomcliche"
echo -n "" > liste_cliches.txttmp 
for i in `cat liste_cliches.txt` ; do  
fichier=$(basename ${i}); 
fichiersansext=`echo ${fichier}|cut -d"." -f1`
fichier=`echo ${fichiersansext}|cut -b 5- ` ; 
echo ${fichier} >> liste_cliches.txttmp 
done
mv liste_cliches.txttmp liste_cliches.txt

echo -n "" > monbash 
for i in `cat liste_cliches.txt ` ; do 
echo ${i} ; 
echo "${scripts_dir}/Ech_noif.LINUX SousEchMoy ${repertoire_Ortho_MEC_Malt}/Ort_${i}.tif Ort_${i}.tif  10 ;  \
${scripts_dir}/convert_ori.LINUX tfw2ori ${repertoire_Ortho_MEC_Malt}/Ort_${i}.tfw Ort_${i}.ini.ori ; \
${scripts_dir}/HIATUS.LINUX SousechOri Ort_${i}.ini.ori 10 Ort_${i}.ori ; \
${scripts_dir}/Ech_noif.LINUX HIATUS CorrectionRadiometrie:PreparerMasques ${repertoire_Ortho_MEC_Malt}/PC_${i}.tif 10 3 5 Incid_${i}.tif ; 
" >> monbash
done
${scripts_dir}/Bash2Make.LINUX monbash monmake 
make -f monmake -j ${CPU}


#SI PLUSIEURS CANAUX
mkdir ini
mv Ort_*tif ini/
cp Ort_* ini/

for b in 1 2 3; do mkdir ${b} ; for i in `cat liste_cliches.txt ` ; do gdal_translate -b ${b} ini/Ort_${i}.tif ${b}/Ort_${i}.tif  ; done ; cp ini/*.ori ${b} ; done



for b in 1 2 3 ; do 
cd ${b}
cp ../liste_cliches.txt .

#echo -n "/media/Data2/transfert_rks/29/testhotspot/build/Egalise " > monbash

echo -n "${scripts_dir}/Egalise.LINUX " > monbash
for i in `cat liste_cliches.txt ` ; do echo -n "${i}.tif "  >> monbash ; done
echo "--reference:moyenne --fusion:moyenne --modele:additif --ssechfinal 1 --noegal" >> monbash
echo "mv big_image.tif big_image.noegal_moyenne.tif" >> monbash
echo "" >> monbash
echo -n "${scripts_dir}/Egalise.LINUX " >> monbash
for i in `cat liste_cliches.txt ` ; do echo -n "${i}.tif "  >> monbash ; done
echo "--reference:moyenne --fusion:voronoi --modele:additif --ssechfinal 1 --noegal" >> monbash
echo "mv big_image.tif big_image.noegal_voronoi.tif" >> monbash
echo "" >> monbash
echo -n "${scripts_dir}/Egalise.LINUX " >> monbash
for i in `cat liste_cliches.txt ` ; do echo -n "${i}.tif "  >> monbash ; done
echo "--reference:moyenne --fusion:moyenne --modele:additif --ssechfinal 1 --pas ${pasEgalisationRadiometrique}" >> monbash
echo "mv big_image.tif big_image.additif_moyenne.tif" >> monbash
echo "" >> monbash
echo -n "${scripts_dir}/Egalise.LINUX " >> monbash
for i in `cat liste_cliches.txt ` ; do echo -n "${i}.tif "  >> monbash ; done
echo "--reference:moyenne --fusion:voronoi --modele:additif --ssechfinal 1 --pas ${pasEgalisationRadiometrique}" >> monbash
echo "mv big_image.tif big_image.additif_voronoi.tif" >> monbash
echo "" >> monbash

sh ./monbash	
${scripts_dir}/Ech_noif.LINUX Int2Char big_image.noegal_voronoi.tif 0 255 big_image.noegal_voronoi.tif
${scripts_dir}/Ech_noif.LINUX Int2Char big_image.noegal_moyenne.tif 0 255 big_image.noegal_moyenne.tif

rm Solution_*

${scripts_dir}/Ech_noif.LINUX Bool big_image.noegal_moyenne.tif big_image.mask.tif
#echo -n "${scripts_dir}/Pleiades.LINUX MNSMICMAC \$1 \$2 " > bash_applique_walis_tmp
#${scripts_dir}/Ech_noif.LINUX Walis big_image.noegal_moyenne.tif big_image.mask.tif big_image.additif_moyenne.tif big_image.mask.tif big_image.walis.tif >> bash_applique_walis_tmp
${scripts_dir}/Ech_noif.LINUX Walis big_image.noegal_moyenne.tif big_image.mask.tif big_image.additif_moyenne.tif big_image.mask.tif big_image.walis.tif >> coef_reetal_walis.txt
mv log.txt log_walis.txt
${scripts_dir}/Ech_noif.LINUX Int2Char big_image.walis.tif 0 255 big_image.walis.tif

cd ..

done

${scripts_dir}/Ech_noif.LINUX AssembleCanaux:UChar 1/big_image.noegal_voronoi.tif 2/big_image.noegal_voronoi.tif 3/big_image.noegal_voronoi.tif  ini/big_image.noegal_voronoi.tif 
${scripts_dir}/Ech_noif.LINUX AssembleCanaux:UChar 1/big_image.noegal_moyenne.tif 2/big_image.noegal_moyenne.tif 3/big_image.noegal_moyenne.tif  ini/big_image.noegal_moyenne.tif 
${scripts_dir}/Ech_noif.LINUX AssembleCanaux:Float 1/big_image.additif_voronoi.tif 2/big_image.additif_voronoi.tif 3/big_image.additif_voronoi.tif  ini/big_image.additif_voronoi.tif 
${scripts_dir}/Ech_noif.LINUX AssembleCanaux:Float 1/big_image.additif_moyenne.tif 2/big_image.additif_moyenne.tif 3/big_image.additif_moyenne.tif  ini/big_image.additif_moyenne.tif 
${scripts_dir}/Ech_noif.LINUX AssembleCanaux:UChar 1/big_image.walis.tif 2/big_image.walis.tif 3/big_image.walis.tif ini/big_image.walis.tif 
cp 1/big_image.mask.tif ini/big_image.mask.tif
cp 1/big_image.ori ini/big_image.ori
cp ini/big_image.ori ini/big_image.additif_moyenne.ori
cp liste_cliches.txt ini

cd ini

echo -n "" > coef_reetal_walis.txt ; for i in 1 2 3 ; do cat ../${i}/coef_reetal_walis.txt >> coef_reetal_walis.txt ; done


#mkdir ../${repertoire_Ortho_MEC_Malt}/corr
mkdir corr
echo -n "" > monbash ;
for i in `cat liste_cliches.txt ` ; do 
echo ${i} ; 
echo "${scripts_dir}/Ech_noif.LINUX HIATUS CorrectionRadiometrie:Appliquer big_image.additif_moyenne.tif Ort_${i}.tif Ort_${i}.ini.ori ../${repertoire_Ortho_MEC_Malt}/Ort_${i}.tif 5 coef_reetal_walis.txt corr/Ort_${i}.tif" >> monbash
done
${scripts_dir}/Bash2Make.LINUX monbash monmake 
make -f monmake -j ${CPU}

cd ..