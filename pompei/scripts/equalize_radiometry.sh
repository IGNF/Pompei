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
