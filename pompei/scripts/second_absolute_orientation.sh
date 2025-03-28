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

#Filtrage des points homologues
echo "TesLib NO_AllOri2Im"
mm3d TestLib NO_AllOri2Im OIS.*tif >> logfile

echo "Ratafia"
mm3d Ratafia OIS.*tif >> logfile

#Déplacement des points homologues filtrés dans Homol
rm -rf Homol
mv Homol-Ratafia Homol

#Mise en place
echo "Campari"
mm3d Campari OIS.*tif Abs Abs-Ratafia | tee reports/report_CampariRatafia.txt >> logfile

#Analyse de report_CampariRatafia 
python ${scripts_dir}/analyze_Tapas.py --input_report reports/report_CampariRatafia.txt

echo "Campari"
mm3d Campari OIS.*tif Abs-Ratafia Abs-Ratafia-AllFree AllFree=true | tee reports/report_CampariRatafia_2.txt >> logfile

# Il ne faut pas le mettre avant car le Campari dans certain cas peut ne pas fonctionner.
# Dans ce cas, analyze_campari_ratafia.py permet de rattraper.
set -e

python ${scripts_dir}/analyze_campari_ratafia.py --input_ratafia_before Ori-Abs-Ratafia --input_ratafia_after Ori-Abs-Ratafia-AllFree
if [ $? != 0 ]; then
  exit 1
fi

#Analyse de report_CampariRatafia_2 
python ${scripts_dir}/analyze_Tapas.py --input_report reports/report_CampariRatafia_2.txt

# Création des masques pour chaque image
python ${scripts_dir}/create_mask_per_image.py --TA ${TA}

#Calcul d'une première orthophoto
echo "Malt"
mm3d Malt Ortho "OIS.*([0-9]).tif" Abs-Ratafia-AllFree MasqIm=Masq NbVI=2 UseTA=0 NbProc=13 EZA=1 DirMEC=MEC-Malt-Abs-Ratafia >> logfile

echo "Tawny"
mm3d Tawny Ortho-MEC-Malt-Abs-Ratafia/ RadiomEgal=false >> logfile

rm -f OIS*Masq.tif

#Calcul du MNS
echo "Calcul du MNS"
python ${scripts_dir}/create_Z_Num_tfw.py --input_Malt MEC-Malt-Abs-Ratafia
python ${scripts_dir}/build_mns_micmac.py --input_Malt MEC-Malt-Abs-Ratafia
gdalbuildvrt MEC-Malt-Abs-Ratafia/MNS_pyramide.vrt  MEC-Malt-Abs-Ratafia/MNS_pyramide*tif