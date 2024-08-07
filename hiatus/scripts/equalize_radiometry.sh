scripts_dir=$1
CPU=$2

nbCouleurs=`cat metadata/nb_colors.txt`
python ${scripts_dir}/compute_pas_radiometric_equalization.py
mkdir tempradiom
cd tempradiom

#Script pour égaliser les orthomosaiques
if test ${nbCouleurs} -eq 1;
then
    sh ${scripts_dir}/equalize_radiometry_panchro.sh ../Ortho-MEC-Malt-Final ${scripts_dir} ${CPU} >> ../logfile
else
    sh ${scripts_dir}/equalize_radiometry_colors.sh ../Ortho-MEC-Malt-Final ${scripts_dir} ${CPU} >> ../logfile
    rm -r 1 2 3
fi


#On copie le répertoire contenant les résultats de Malt
cd ..
mkdir Ortho-MEC-Malt-Final-Corr
cp Ortho-MEC-Malt-Final/* Ortho-MEC-Malt-Final-Corr

#On supprime les orthophotos sans la correction radiométrique
cd Ortho-MEC-Malt-Final-Corr
rm Ort_*tif
rm Orthopho*.tif

#On remplace les images sans correction radiométrique par les images avec correction radiométrique
cp ../tempradiom/ini/corr/Ort_*.tif .
cd ..

#On relance le calcul d'orthophoto avec Tawny
echo "Tawny"
mm3d Tawny Ortho-MEC-Malt-Final-Corr/ RadiomEgal=false >> logfile
