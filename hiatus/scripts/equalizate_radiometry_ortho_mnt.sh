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

nbCouleurs=`cat metadata/nb_colors.txt`

mkdir radiom_ortho_mnt

python ${scripts_dir}/compute_pas_radiometric_equalization.py
pasEgalisationRadiometrique=`cat metadata/pas_egalisation_radiometrique.txt`


ls ortho_mnt/Ort_*tif > radiom_ortho_mnt/liste_cliches.txt
ls ortho_mnt/Ort_*tif > radiom_ortho_mnt/temp.txt

#Nettoyage du fichier : on passe de "rep/Ort_nomcliche.tif" a "nomcliche"
echo -n "" > radiom_ortho_mnt/liste_cliches.txttmp 
for i in `cat radiom_ortho_mnt/liste_cliches.txt` ; do
    fichier=$(basename ${i});
    fichiersansext=`echo ${fichier}|cut -d"." -f1`
    fichier=`echo ${fichiersansext}|cut -b 5- ` ; 
    echo ${fichier} >> radiom_ortho_mnt/liste_cliches.txttmp 
done
mv radiom_ortho_mnt/liste_cliches.txttmp radiom_ortho_mnt/liste_cliches.txt

echo -n "" > radiom_ortho_mnt/monbash 
for i in `cat radiom_ortho_mnt/liste_cliches.txt ` ; do 
    echo "${scripts_dir}/Ech_noif.LINUX SousEchMoy ortho_mnt/Ort_${i}.tif radiom_ortho_mnt/Ort_${i}.tif  10 ;  \
    ${scripts_dir}/convert_ori.LINUX tfw2ori ortho_mnt/Ort_${i}.tfw radiom_ortho_mnt/Ort_${i}.ini.ori ; \
    ${scripts_dir}/HIATUS.LINUX SousechOri radiom_ortho_mnt/Ort_${i}.ini.ori 10 radiom_ortho_mnt/Ort_${i}.ori ; \
    ${scripts_dir}/Ech_noif.LINUX HIATUS CorrectionRadiometrie:PreparerMasques ortho_mnt/Incid_${i}.tif 10 3 5 radiom_ortho_mnt/Incid_${i}.tif ; 
    " >> radiom_ortho_mnt/monbash
done
echo ${scripts_dir}/Bash2Make.LINUX
${scripts_dir}/Bash2Make.LINUX radiom_ortho_mnt/monbash radiom_ortho_mnt/monmake 
make -f radiom_ortho_mnt/monmake -j ${CPU}



mkdir radiom_ortho_mnt/ini
repertoire_ini=radiom_ortho_mnt/ini
mv radiom_ortho_mnt/Ort_*tif ${repertoire_ini}/
cp radiom_ortho_mnt/Ort_* ${repertoire_ini}/

cp radiom_ortho_mnt/liste_cliches.txt ${repertoire_ini}/

for b in $(seq 1 $nbCouleurs); do 
    mkdir ${repertoire_ini}/${b} ; 
    for i in `cat radiom_ortho_mnt/liste_cliches.txt` ; do 
        gdal_translate -b ${b} ${repertoire_ini}/Ort_${i}.tif ${repertoire_ini}/${b}/Ort_${i}.tif  ; 
    done ; 
    cp ${repertoire_ini}/*.ori ${repertoire_ini}/${b} ; 
done

for b in $(seq 1 $nbCouleurs) ; do
    repertoire_b=${repertoire_ini}/${b}
    cp ${repertoire_ini}/liste_cliches.txt ${repertoire_b}

    echo -n "${scripts_dir}/Egalise.LINUX " > ${repertoire_b}/monbash
    for i in `cat ${repertoire_b}/liste_cliches.txt ` ; do echo -n "${repertoire_b}/${i}.tif "  >> ${repertoire_b}/monbash ; done
    echo "--reference:moyenne --fusion:moyenne --modele:additif --ssechfinal 1 --noegal" >> ${repertoire_b}/monbash
    echo "mv big_image.tif ${repertoire_b}/big_image.noegal_moyenne.tif" >> ${repertoire_b}/monbash
    echo "" >> ${repertoire_b}/monbash
    echo -n "${scripts_dir}/Egalise.LINUX " >> ${repertoire_b}/monbash
    for i in `cat ${repertoire_b}/liste_cliches.txt ` ; do echo -n "${repertoire_b}/${i}.tif "  >> ${repertoire_b}/monbash ; done
    echo "--reference:moyenne --fusion:voronoi --modele:additif --ssechfinal 1 --noegal" >> ${repertoire_b}/monbash
    echo "mv big_image.tif ${repertoire_b}/big_image.noegal_voronoi.tif" >> ${repertoire_b}/monbash
    echo "" >> ${repertoire_b}/monbash
    echo -n "${scripts_dir}/Egalise.LINUX " >> ${repertoire_b}/monbash
    for i in `cat ${repertoire_b}/liste_cliches.txt ` ; do echo -n "${repertoire_b}/${i}.tif "  >> ${repertoire_b}/monbash ; done
    echo "--reference:moyenne --fusion:moyenne --modele:additif --ssechfinal 1 --pas ${pasEgalisationRadiometrique}" >> ${repertoire_b}/monbash
    echo "mv big_image.tif ${repertoire_b}/big_image.additif_moyenne.tif" >> ${repertoire_b}/monbash
    echo "" >> ${repertoire_b}/monbash
    echo -n "${scripts_dir}/Egalise.LINUX " >> ${repertoire_b}/monbash
    for i in `cat ${repertoire_b}/liste_cliches.txt ` ; do echo -n "${repertoire_b}/${i}.tif "  >> ${repertoire_b}/monbash ; done
    echo "--reference:moyenne --fusion:voronoi --modele:additif --ssechfinal 1 --pas ${pasEgalisationRadiometrique}" >> ${repertoire_b}/monbash
    echo "mv big_image.tif ${repertoire_b}/big_image.additif_voronoi.tif" >> ${repertoire_b}/monbash
    echo "" >> ${repertoire_b}/monbash

    sh ${repertoire_b}/monbash	
    ${scripts_dir}/Ech_noif.LINUX Int2Char ${repertoire_b}/big_image.noegal_voronoi.tif 0 255 ${repertoire_b}/big_image.noegal_voronoi.tif
    ${scripts_dir}/Ech_noif.LINUX Int2Char ${repertoire_b}/big_image.noegal_moyenne.tif 0 255 ${repertoire_b}/big_image.noegal_moyenne.tif

    rm ${repertoire_b}/Solution_*

    ${scripts_dir}/Ech_noif.LINUX Bool ${repertoire_b}/big_image.noegal_moyenne.tif ${repertoire_b}/big_image.mask.tif
    ${scripts_dir}/Ech_noif.LINUX Walis ${repertoire_b}/big_image.noegal_moyenne.tif ${repertoire_b}/big_image.mask.tif ${repertoire_b}/big_image.additif_moyenne.tif ${repertoire_b}/big_image.mask.tif ${repertoire_b}/big_image.walis.tif >> ${repertoire_b}/coef_reetal_walis.txt
    python ${scripts_dir}/correct.py --chemin ${repertoire_b}/coef_reetal_walis.txt
    mv log.txt ${repertoire_b}/log_walis.txt
    ${scripts_dir}/Ech_noif.LINUX Int2Char ${repertoire_b}/big_image.walis.tif 0 255 ${repertoire_b}/big_image.walis.tif

done


if test ${nbCouleurs} -eq 1;
then
    ${scripts_dir}/Ech_noif.LINUX Format ${repertoire_ini}/1/big_image.additif_moyenne.tif ${repertoire_ini}/big_image.additif_moyenne.tif 
    ${scripts_dir}/Ech_noif.LINUX Format ${repertoire_ini}/1/big_image.walis.tif ${repertoire_ini}/big_image.walis.tif 
    ${scripts_dir}/Ech_noif.LINUX Format ${repertoire_ini}/1/big_image.noegal_voronoi.tif ${repertoire_ini}/big_image.noegal_voronoi.tif 
    ${scripts_dir}/Ech_noif.LINUX Format ${repertoire_ini}/1/big_image.noegal_moyenne.tif ${repertoire_ini}/big_image.noegal_moyenne.tif
    mv big_image.ori ${repertoire_ini}/big_image.additif_moyenne.ori
    mv ${repertoire_ini}/1/coef_reetal_walis.txt ${repertoire_ini}
else
    ${scripts_dir}/Ech_noif.LINUX AssembleCanaux:UChar ${repertoire_ini}/1/big_image.noegal_voronoi.tif ${repertoire_ini}/2/big_image.noegal_voronoi.tif ${repertoire_ini}/3/big_image.noegal_voronoi.tif  ${repertoire_ini}/big_image.noegal_voronoi.tif 
    ${scripts_dir}/Ech_noif.LINUX AssembleCanaux:UChar ${repertoire_ini}/1/big_image.noegal_moyenne.tif ${repertoire_ini}/2/big_image.noegal_moyenne.tif ${repertoire_ini}/3/big_image.noegal_moyenne.tif  ${repertoire_ini}/big_image.noegal_moyenne.tif 
    ${scripts_dir}/Ech_noif.LINUX AssembleCanaux:Float ${repertoire_ini}/1/big_image.additif_voronoi.tif ${repertoire_ini}/2/big_image.additif_voronoi.tif ${repertoire_ini}/3/big_image.additif_voronoi.tif  ${repertoire_ini}/big_image.additif_voronoi.tif 
    ${scripts_dir}/Ech_noif.LINUX AssembleCanaux:Float ${repertoire_ini}/1/big_image.additif_moyenne.tif ${repertoire_ini}/2/big_image.additif_moyenne.tif ${repertoire_ini}/3/big_image.additif_moyenne.tif  ${repertoire_ini}/big_image.additif_moyenne.tif 
    ${scripts_dir}/Ech_noif.LINUX AssembleCanaux:UChar ${repertoire_ini}/1/big_image.walis.tif ${repertoire_ini}/2/big_image.walis.tif ${repertoire_ini}/3/big_image.walis.tif ${repertoire_ini}/big_image.walis.tif 
    cp ${repertoire_ini}/1/big_image.mask.tif ${repertoire_ini}/big_image.mask.tif
    cp big_image.ori ${repertoire_ini}/big_image.ori
    cp big_image.ori ${repertoire_ini}/big_image.additif_moyenne.ori
    #cp ${repertoire_ini}/liste_cliches.txt ${repertoire_ini}
    #rm -r ${repertoire_ini}/1 ${repertoire_ini}/2 ${repertoire_ini}/3
    echo -n "" > ${repertoire_ini}/coef_reetal_walis.txt
    for i in 1 2 3 ; do 
        cat ${repertoire_ini}/${i}/coef_reetal_walis.txt >> ${repertoire_ini}/coef_reetal_walis.txt ; 
    done
fi


mkdir ${repertoire_ini}/corr
echo -n "" > ${repertoire_ini}/monbash1 ;
for i in `cat ${repertoire_ini}/liste_cliches.txt ` ; do 
    echo ${i} ; 
    echo "${scripts_dir}/Ech_noif.LINUX HIATUS CorrectionRadiometrie:Appliquer ${repertoire_ini}/big_image.additif_moyenne.tif ${repertoire_ini}/Ort_${i}.tif ${repertoire_ini}/Ort_${i}.ini.ori ortho_mnt/Ort_${i}.tif 5 ${repertoire_ini}/coef_reetal_walis.txt ${repertoire_ini}/corr/Ort_${i}.tif" >> ${repertoire_ini}/monbash1
done
${scripts_dir}/Bash2Make.LINUX ${repertoire_ini}/monbash1 ${repertoire_ini}/monmake 
make -f ${repertoire_ini}/monmake -j ${CPU}