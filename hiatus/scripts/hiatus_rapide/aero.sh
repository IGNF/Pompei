repertoire_scripts=$1



# On recopie le fichier de calibration initial dans l'orientation approchée issue des métadonnées
ls Ori-CalibNum  | grep '.*.xml' > calibNum.txt
for file in `cat calibNum.txt` ; do
    cp Ori-CalibNum/${file} Ori-Nav/${file}
done


# Pour chaque image, on calcule ses paramètres externes, puis les paramètres internes de la caméra qui lui conviennent le mieux
# Si dès ce moment, il est impossible de mener le calcul jusqu'au bout pour une image, alors on la retire du chantier
# et est considérée comme irrécupérable
ls OIS*.tif > images.txt
for image in `cat images.txt` ; do
    echo ""
    echo ${image}
    mm3d Campari ${image} Nav ${image}_0 GCP=[appuis.xml,10,MesuresAppuis-S2D.xml,10]  SigmaTieP=10 RapTxt=${image}_0.txt | tee rapports/${image}_0.txt >> logfile
    python ${repertoire_scripts}/hiatus_rapide/analyse_campari.py --appuis appuis.xml --rapportResidus ${image}_0.txt
    mm3d Campari ${image} ${image}_0 ${image}_1 GCP=[appuis.xml,10,MesuresAppuis-S2D.xml,10]  SigmaTieP=10 PoseFigee=true AllFree=true RapTxt=${image}_1.txt | tee rapports/${image}_1.txt >> logfile
    python ${repertoire_scripts}/hiatus_rapide/analyse_campari.py --appuis appuis.xml --rapportResidus ${image}_1.txt
done

# On fait une moyenne de tous les paramètres de calibration interne trouvés
python ${repertoire_scripts}/hiatus_rapide/compute_mean_calib.py

# On fait deux aéros, d'abord sur les paramètres externes, puis sur les paramètres internes. On utilise la même caméra pour tous les clichés
mm3d Campari OIS.*tif Aero_0 Aero_1 GCP=[appuis.xml,10,MesuresAppuis-S2D.xml,10]  SigmaTieP=10 RapTxt=RapportResidus.txt | tee rapports/rapport_CampariAero_1.txt >> logfile
python ${repertoire_scripts}/analyse_Campari.py --input_rapport rapports/rapport_CampariAero_1.txt

if [ -d Ori-Aero_1 ];then
    mm3d Campari OIS.*tif Aero_1 Aero_2 GCP=[appuis.xml,10,MesuresAppuis-S2D.xml,10]  SigmaTieP=10 RapTxt=RapportResidus.txt PoseFigee=true AllFree=true | tee rapports/rapport_CampariAero_2.txt >> logfile
    python ${repertoire_scripts}/analyse_Campari.py --input_rapport rapports/rapport_CampariAero_2.txt
fi


if [ -d Ori-Aero_2 ];then
# On supprime une première fois les points d'appuis les plus faux
    mkdir iter0
    mv MesuresAppuis-S2D.xml iter0/
    mv appuis.xml iter0/
    cp RapportResidus.txt iter0/
    python ${repertoire_scripts}/supprimer_appuis.py --facteur 3 --appuis iter0/appuis.xml --S2D iter0/MesuresAppuis-S2D.xml --appuis_save appuis.xml --S2D_save MesuresAppuis-S2D.xml --rapportResidus iter0/RapportResidus.txt

    # On fait deux aéros, d'abord sur les paramètres externes, puis sur les paramètres internes
    mm3d Campari OIS.*tif Aero_2 Aero_3 GCP=[appuis.xml,10,MesuresAppuis-S2D.xml,10]  SigmaTieP=10 RapTxt=RapportResidus.txt | tee rapports/rapport_CampariAero_3.txt >> logfile
    python ${repertoire_scripts}/analyse_Campari.py --input_rapport rapports/rapport_CampariAero_3.txt
fi

if [ -d Ori-Aero_3 ];then
    mm3d Campari OIS.*tif Aero_3 Aero_4 GCP=[appuis.xml,10,MesuresAppuis-S2D.xml,10]  SigmaTieP=10 RapTxt=RapportResidus.txt PoseFigee=true AllFree=true | tee rapports/rapport_CampariAero_4.txt >> logfile
    python ${repertoire_scripts}/analyse_Campari.py --input_rapport rapports/rapport_CampariAero_4.txt
fi

if [ -d Ori-Aero_4 ];then
    # On supprime une deuxième fois les points d'appuis les plus faux
    mkdir iter1
    mv MesuresAppuis-S2D.xml iter1/
    mv appuis.xml iter1/
    cp RapportResidus.txt iter1/
    python ${repertoire_scripts}/supprimer_appuis.py --facteur 3 --appuis iter1/appuis.xml --S2D iter1/MesuresAppuis-S2D.xml --appuis_save appuis.xml --S2D_save MesuresAppuis-S2D.xml --rapportResidus iter1/RapportResidus.txt

    # On fait deux aéros, d'abord sur les paramètres externes, puis sur les paramètres internes. On réduit cette fois l'écart-type sur les points de liaisons
    mm3d Campari OIS.*tif Aero_4 Aero_5 GCP=[appuis.xml,10,MesuresAppuis-S2D.xml,10]  SigmaTieP=0.5 RapTxt=RapportResidus.txt | tee rapports/rapport_CampariAero_5.txt >> logfile
    python ${repertoire_scripts}/analyse_Campari.py --input_rapport rapports/rapport_CampariAero_5.txt
fi

if [ -d Ori-Aero_5 ];then
    mm3d Campari OIS.*tif Aero_5 Aero_6 GCP=[appuis.xml,10,MesuresAppuis-S2D.xml,10]  SigmaTieP=0.5 RapTxt=RapportResidus.txt AllFree=true | tee rapports/rapport_CampariAero_6.txt >> logfile
    python ${repertoire_scripts}/analyse_Campari.py --input_rapport rapports/rapport_CampariAero_6.txt
fi

if [ -d Ori-Aero_6 ];then
    # On supprime une troisième fois les points d'appuis les plus faux
    mkdir iter2
    mv MesuresAppuis-S2D.xml iter2/
    mv appuis.xml iter2/
    cp RapportResidus.txt iter2/
    python ${repertoire_scripts}/supprimer_appuis.py --facteur 3 --appuis iter2/appuis.xml --S2D iter2/MesuresAppuis-S2D.xml --appuis_save appuis.xml --S2D_save MesuresAppuis-S2D.xml --rapportResidus iter2/RapportResidus.txt

    # On fait une aéro sur tous les paramètres
    mm3d Campari OIS.*tif Aero_6 Aero_7 GCP=[appuis.xml,10,MesuresAppuis-S2D.xml,10]  SigmaTieP=0.5 RapTxt=RapportResidus.txt AllFree=true | tee rapports/rapport_CampariAero_7.txt >> logfile
    python ${repertoire_scripts}/analyse_Campari.py --input_rapport rapports/rapport_CampariAero_7.txt
fi 

if [ -d Ori-Aero_7 ];then
    # On analyse les résidus, sans supprimer de points d'appuis
    mkdir iter3
    mv MesuresAppuis-S2D.xml iter3/
    mv appuis.xml iter3/
    cp RapportResidus.txt iter3/
    python ${repertoire_scripts}/supprimer_appuis.py --facteur 3 --appuis iter3/appuis.xml --S2D iter3/MesuresAppuis-S2D.xml --appuis_save appuis.xml --S2D_save MesuresAppuis-S2D.xml --rapportResidus iter3/RapportResidus.txt --supprimer False
fi

# On récupère le résultat de la meilleure aéro faite par le calcul
python ${repertoire_scripts}/hiatus_rapide/get_best_aero.py 

# On calcule la résolution terrain qu'il faudra utiliser pour produire l'ortho
python ${repertoire_scripts}/compute_resolution.py --input_ori Ori-TerrainFinal_10_10_0.5_AllFree_Final/ --metadata metadata/
${repertoire_scripts}/AnalyseRapportMicMac.LINUX AnalyseRapportResidusMICMAC RapportResidus.txt --export_ogr_appuis_mesure PtsAppuiMesure.geojson --export_ogr_appuis_calcul PtsAppuiCalcul.geojson --export_ogr_residus_appuis VecteursResidusAppui.geojson --epsg 2154 >> rapports/rapport_complet.txt