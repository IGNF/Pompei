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

remove_artefacts=$1
scripts_dir=$2 


#Suppression des points homologues présents dans les contours
echo "HomolFilterMasq"

if test ${remove_artefacts} -eq 1;
then
    mm3d HomolFilterMasq "OIS-Reech_.*tif" GlobalMasq=filtre_artefacts.tif ExpTxtOut=true >> logfile
    mm3d HomolFilterMasq "OIS-Reech_.*tif" GlobalMasq=filtre_artefacts.tif >> logfile
else
    mm3d HomolFilterMasq "OIS-Reech_.*tif" GlobalMasq=filtre.tif ExpTxtOut=true >> logfile
    mm3d HomolFilterMasq "OIS-Reech_.*tif" GlobalMasq=filtre.tif >> logfile
fi
mv Homol HomolTA_safe >> logfile

python ${scripts_dir}/delete_tie_points.py --homol_input HomolMasqFiltered --homol_output Homol --footprints flight_plan/flight_plan.shp
python ${scripts_dir}/visualize_tie_points.py --homol Homol --footprints flight_plan/flight_plan.shp --reports reports/