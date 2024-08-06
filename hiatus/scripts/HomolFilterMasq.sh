presence_artefacts=$1
repertoire_scripts=$2 


#Suppression des points homologues présents dans les contours
echo "HomolFilterMasq"

if test ${presence_artefacts} -eq 1;
then
    mm3d HomolFilterMasq "OIS-Reech_.*tif" GlobalMasq=filtre_artefacts.tif ExpTxtOut=true >> logfile
    mm3d HomolFilterMasq "OIS-Reech_.*tif" GlobalMasq=filtre_artefacts.tif >> logfile
else
    mm3d HomolFilterMasq "OIS-Reech_.*tif" GlobalMasq=filtre.tif ExpTxtOut=true >> logfile
    mm3d HomolFilterMasq "OIS-Reech_.*tif" GlobalMasq=filtre.tif >> logfile
fi
mv Homol HomolTA_safe >> logfile

python ${repertoire_scripts}/supprimer_points_homologues.py --homol_input HomolMasqFiltered --homol_output Homol --emprises Analyse_Plan_Vol/chantier.shp
python ${repertoire_scripts}/visualiser_points_liaisons.py --homol Homol --emprises Analyse_Plan_Vol/chantier.shp --rapports rapports/