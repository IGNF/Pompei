repertoire_scripts=$1
CPU=$2

nbCouleurs=`cat metadata/nbCouleurs.txt`
python ${repertoire_scripts}/pas_egalisation_radiometrique.py
mkdir tempradiom
cd tempradiom

#Script pour égaliser les orthomosaiques
if test ${nbCouleurs} -eq 1;
then
    sh ${repertoire_scripts}/bash_a_lancer_egalisationradiometrique_serveur_panchro_bis.sh ../Ortho-MEC-Malt-Final ${repertoire_scripts} ${CPU} >> ../logfile
else
    sh ${repertoire_scripts}/bash_a_lancer_egalisationradiometrique_serveur_couleur_bis.sh ../Ortho-MEC-Malt-Final ${repertoire_scripts} ${CPU} >> ../logfile
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
