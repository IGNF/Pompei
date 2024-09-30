#Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/
#
#File main authors:
#- Célestin Huet
#This file is part of Pompei: https://github.com/IGNF/Pompei
#
#Pompei is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#Pompei is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#You should have received a copy of the GNU General Public License along with Pompei. If not, see <https://www.gnu.org/licenses/>.








scripts_dir=$1



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
    mm3d Campari ${image} Nav ${image}_0 GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=10 RapTxt=${image}_0.txt | tee reports/${image}_0.txt >> logfile
    python ${scripts_dir}/pompei_rapide/analyse_campari.py --appuis GCP.xml --report_residuals ${image}_0.txt
    mm3d Campari ${image} ${image}_0 ${image}_1 GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=10 PoseFigee=true AllFree=true RapTxt=${image}_1.txt | tee reports/${image}_1.txt >> logfile
    python ${scripts_dir}/pompei_rapide/analyse_campari.py --appuis GCP.xml --report_residuals ${image}_1.txt
done

# On fait une moyenne de tous les paramètres de calibration interne trouvés
python ${scripts_dir}/pompei_rapide/compute_mean_calib.py

# On fait deux aéros, d'abord sur les paramètres externes, puis sur les paramètres internes. On utilise la même caméra pour tous les clichés
mm3d Campari OIS.*tif Aero_0 Aero_1 GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=10 RapTxt=ResidualsReport.txt | tee reports/rapport_CampariAero_1.txt >> logfile
python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_1.txt

if [ -d Ori-Aero_1 ];then
    mm3d Campari OIS.*tif Aero_1 Aero_2 GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=10 RapTxt=ResidualsReport.txt PoseFigee=true AllFree=true | tee reports/rapport_CampariAero_2.txt >> logfile
    python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_2.txt
fi


if [ -d Ori-Aero_2 ];then
# On supprime une première fois les points d'appuis les plus faux
    mkdir iter0
    mv GCP-S2D.xml iter0/
    mv GCP.xml iter0/
    cp ResidualsReport.txt iter0/
    python ${scripts_dir}/delete_GCP.py --factor 3 --GCP iter0/GCP.xml --S2D iter0/GCP-S2D.xml --GCP_save GCP.xml --S2D_save GCP-S2D.xml --report_residuals iter0/ResidualsReport.txt

    # On fait deux aéros, d'abord sur les paramètres externes, puis sur les paramètres internes
    mm3d Campari OIS.*tif Aero_2 Aero_3 GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=10 RapTxt=ResidualsReport.txt | tee reports/rapport_CampariAero_3.txt >> logfile
    python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_3.txt
fi

if [ -d Ori-Aero_3 ];then
    mm3d Campari OIS.*tif Aero_3 Aero_4 GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=10 RapTxt=ResidualsReport.txt PoseFigee=true AllFree=true | tee reports/rapport_CampariAero_4.txt >> logfile
    python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_4.txt
fi

if [ -d Ori-Aero_4 ];then
    # On supprime une deuxième fois les points d'appuis les plus faux
    mkdir iter1
    mv GCP-S2D.xml iter1/
    mv GCP.xml iter1/
    cp ResidualsReport.txt iter1/
    python ${scripts_dir}/delete_GCP.py --factor 3 --GCP iter1/GCP.xml --S2D iter1/GCP-S2D.xml --GCP_save GCP.xml --S2D_save GCP-S2D.xml --report_residuals iter1/ResidualsReport.txt

    # On fait deux aéros, d'abord sur les paramètres externes, puis sur les paramètres internes. On réduit cette fois l'écart-type sur les points de liaisons
    mm3d Campari OIS.*tif Aero_4 Aero_5 GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=0.5 RapTxt=ResidualsReport.txt | tee reports/rapport_CampariAero_5.txt >> logfile
    python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_5.txt
fi

if [ -d Ori-Aero_5 ];then
    mm3d Campari OIS.*tif Aero_5 Aero_6 GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=0.5 RapTxt=ResidualsReport.txt AllFree=true | tee reports/rapport_CampariAero_6.txt >> logfile
    python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_6.txt
fi

if [ -d Ori-Aero_6 ];then
    # On supprime une troisième fois les points d'appuis les plus faux
    mkdir iter2
    mv GCP-S2D.xml iter2/
    mv GCP.xml iter2/
    cp ResidualsReport.txt iter2/
    python ${scripts_dir}/delete_GCP.py --factor 3 --GCP iter2/GCP.xml --S2D iter2/GCP-S2D.xml --GCP_save GCP.xml --S2D_save GCP-S2D.xml --report_residuals iter2/ResidualsReport.txt

    # On fait une aéro sur tous les paramètres
    mm3d Campari OIS.*tif Aero_6 Aero_7 GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=0.5 RapTxt=ResidualsReport.txt AllFree=true | tee reports/rapport_CampariAero_7.txt >> logfile
    python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_7.txt
fi 

if [ -d Ori-Aero_7 ];then
    # On analyse les résidus, sans supprimer de points d'appuis
    mkdir iter3
    mv GCP-S2D.xml iter3/
    mv GCP.xml iter3/
    cp ResidualsReport.txt iter3/
    python ${scripts_dir}/delete_GCP.py --factor 3 --GCP iter3/GCP.xml --S2D iter3/GCP-S2D.xml --GCP_save GCP.xml --S2D_save GCP-S2D.xml --report_residuals iter3/ResidualsReport.txt --delete False
fi

# On récupère le résultat de la meilleure aéro faite par le calcul
python ${scripts_dir}/pompei_rapide/get_best_aero.py 

# On calcule la résolution terrain qu'il faudra utiliser pour produire l'ortho
python ${scripts_dir}/compute_resolution.py --input_ori Ori-TerrainFinal_10_10_0.5_AllFree_Final/ --metadata metadata/
${scripts_dir}/AnalyseRapportMicMac.LINUX AnalyseRapportResidusMICMAC ResidualsReport.txt --export_ogr_appuis_mesure PtsAppuiMesure.geojson --export_ogr_appuis_calcul PtsAppuiCalcul.geojson --export_ogr_residus_appuis VecteursResidusAppui.geojson --epsg 2154 >> pompei.log