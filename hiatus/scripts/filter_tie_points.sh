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