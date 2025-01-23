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
TA=$2



#Pré-calcule de l'orientation relative
echo "Martini"
mm3d Martini "OIS-Reech_.*tif" OriCalib=CalibNum >> logfile

#Calcule de l'orientation relative
echo "Tapas"
mm3d Tapas FraserBasic "OIS-Reech_.*tif" InOri=MartiniCalibNum InCal=CalibNum Out=Rel @ExitOnWarn | tee reports/report_Tapas.txt >> logfile

#Analyse de report_Tapas 
python ${scripts_dir}/analyze_Tapas.py --input_report reports/report_Tapas.txt --scripts_dir ${scripts_dir}


#Crée un nuage de points
echo "AperiCloud"
mm3d AperiCloud "OIS-Reech_.*tif" Rel >> logfile


#Approche les sommets de prise de vue au plus près des coordonnées contenues dans le fichier SommetsNav.csv
echo "CenterBascule"
python ${scripts_dir}/centerBascule.py --ta_xml ${TA}


#Analyse de report_CenterBascule
python ${scripts_dir}/analyze_CenterBascule.py --input_report reports/report_CenterBascule.txt --ori_abs Ori-Abs
if [ $? != 0 ]; then
  exit 1
fi


#Produit une première orthophoto qui donne un aperçu de cette première mise en place
echo "Tarama"
mm3d Tarama "OIS-Reech_.*tif" Abs Out=TA-Abs >> logfile