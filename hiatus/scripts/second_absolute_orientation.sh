scripts_dir=$1

#Filtrage des points homologues
echo "TesLib NO_AllOri2Im"
mm3d TestLib NO_AllOri2Im OIS.*tif >> logfile

echo "Ratafia"
mm3d Ratafia OIS.*tif >> logfile

#Déplacement des points homologues filtrés dans Homol
mv Homol Homol-Ini
mv Homol-Ratafia Homol

#Mise en place
echo "Campari"
mm3d Campari OIS.*tif Abs Abs-Ratafia | tee reports/report_CampariRatafia.txt >> logfile

#Analyse de report_CampariRatafia 
python ${scripts_dir}/analyze_Campari.py --input_report reports/report_CampariRatafia.txt

echo "Campari"
mm3d Campari OIS.*tif Abs-Ratafia Abs-Ratafia-AllFree AllFree=true | tee reports/report_CampariRatafia_2.txt >> logfile

#Analyse de report_CampariRatafia_2 
python ${scripts_dir}/analyze_Campari.py --input_report reports/report_CampariRatafia_2.txt

#Calcul d'une première orthophoto
echo "Malt"
mm3d Malt Ortho OIS.*tif Abs-Ratafia-AllFree MasqImGlob=filtre.tif NbVI=2 UseTA=0 NbProc=30 EZA=1 DirMEC=MEC-Malt-Abs-Ratafia >> logfile

echo "Tawny"
mm3d Tawny Ortho-MEC-Malt-Abs-Ratafia/ RadiomEgal=false >> logfile

#Calcul du MNS
echo "Calcul du MNS"
python ${scripts_dir}/create_Z_Num_tfw.py --input_Malt MEC-Malt-Abs-Ratafia
python ${scripts_dir}/build_mns_micmac.py --input_Malt MEC-Malt-Abs-Ratafia