repertoire_scripts=$1

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
mm3d Campari OIS.*tif Abs Abs-Ratafia | tee rapports/rapport_CampariRatafia.txt >> logfile

#Analyse de rapport_CampariRatafia 
python ${repertoire_scripts}/analyse_Campari.py --input_rapport rapports/rapport_CampariRatafia.txt

echo "Campari"
mm3d Campari OIS.*tif Abs-Ratafia Abs-Ratafia-AllFree AllFree=true | tee rapports/rapport_CampariRatafia_2.txt >> logfile

#Analyse de rapport_CampariRatafia_2 
python ${repertoire_scripts}/analyse_Campari.py --input_rapport rapports/rapport_CampariRatafia_2.txt

#Calcul d'une première orthophoto
echo "Malt"
mm3d Malt Ortho OIS.*tif Abs-Ratafia-AllFree MasqImGlob=filtre.tif NbVI=2 UseTA=0 NbProc=30 EZA=1 DirMEC=MEC-Malt-Abs-Ratafia >> logfile

echo "Tawny"
mm3d Tawny Ortho-MEC-Malt-Abs-Ratafia/ RadiomEgal=false >> logfile

#Calcul du MNS
echo "Calcul du MNS"
python ${repertoire_scripts}/create_Z_Num_tfw.py --input_Malt MEC-Malt-Abs-Ratafia
python ${repertoire_scripts}/build_mns_micmac.py --input_Malt MEC-Malt-Abs-Ratafia