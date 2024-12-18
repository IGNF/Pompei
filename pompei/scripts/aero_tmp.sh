
filter_GCP=$1
algo=$2
CPU=$3
ortho=$4
TA=$5

EPSG=2154


workspace=$(dirname ${TA})
rm workspace.txt
echo $workspace >> workspace.txt
scripts_dir=$(realpath "scripts")
cd ${workspace}
TA=$(basename ${TA})

if test ${filter_GCP} -eq 1; then
    python ${scripts_dir}/filter_GCP.py --appuis GCP_before_filtering.xml --S2D GCP_before_filtering-S2D.xml --metadata metadata --GCP_save GCP_0.xml --S2D_save GCP-S2D_0.xml --etape 0
fi

#Dans le cas où les points d'appuis ont été trouvés avec le SRTM, il faut être beaucoup plus souple sur les points d'appuis qu'avec les autres méthodes 
if test ${algo} = "srtm"; then
    factor=10
else
    factor=2
fi

# Première itération : ne sert qu'à supprimer les points d'appuis les plus faux
echo "Campari 10_10_10_tmp"
mm3d Campari OIS.*tif Abs-Ratafia-AllFree TerrainFinal_10_10_10_tmp GCP=[GCP_0.xml,10,GCP-S2D_0.xml,10]  SigmaTieP=10 RapTxt=ResidualsReport_0.txt| tee reports/rapport_CampariAero_10_10_10_tmp.txt >> logfile
python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_10_10_10_tmp.txt
python ${scripts_dir}/delete_GCP.py --factor ${factor} --GCP GCP_0.xml --S2D GCP-S2D_0.xml --GCP_save GCP_1.xml --S2D_save GCP-S2D_1.xml --report_residuals ResidualsReport_0.txt


# Deuxième itération itération : on ne touche pas à l'orientation interne. On déplace le bloc pour qu'il colle au mieux aux points d'appuis
echo "Campari 10_10_10"
mm3d Campari OIS.*tif Abs-Ratafia-AllFree TerrainFinal_10_10_10 GCP=[GCP_1.xml,10,GCP-S2D_1.xml,10]  SigmaTieP=10 RapTxt=ResidualsReport_1.txt| tee reports/rapport_CampariAero_10_10_10.txt >> logfile
python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_10_10_10.txt
python ${scripts_dir}/delete_GCP.py --factor ${factor} --GCP GCP_1.xml --S2D GCP-S2D_1.xml --GCP_save GCP_2.xml --S2D_save GCP-S2D_2.xml --report_residuals ResidualsReport_1.txt


# Troisième itération : on permet la modification des paramètres internes. cette itération ne sert qu'à supprimer les points d'appuis les plus faux
echo "Campari 10_10_10_AllFree"
mm3d Campari OIS.*tif TerrainFinal_10_10_10 TerrainFinal_10_10_10_AllFree_temp GCP=[GCP_2.xml,10,GCP-S2D_2.xml,10]  SigmaTieP=10 AllFree=true RapTxt=ResidualsReport_2.txt| tee reports/rapport_CampariAero_10_10_10_AllFree_temp.txt >> logfile
python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_10_10_10_AllFree_temp.txt
python ${scripts_dir}/delete_GCP.py --factor ${factor} --GCP GCP_2.xml --S2D GCP-S2D_2.xml --GCP_save GCP_3.xml --S2D_save GCP-S2D_3.xml --report_residuals ResidualsReport_2.txt


# Quatrième itération : on permet la modification des paramètres internes. Pas de suppression de points d'appuis
mm3d Campari OIS.*tif TerrainFinal_10_10_10 TerrainFinal_10_10_10_AllFree GCP=[GCP_3.xml,10,GCP-S2D_3.xml,10]  SigmaTieP=10 AllFree=true RapTxt=ResidualsReport.txt| tee reports/rapport_CampariAero_10_10_10_AllFree.txt >> logfile
python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_10_10_10_AllFree.txt

# Cinquième itération : on réduit l'écart-type sur les points de liaisons
echo "Campari 10_10_0.5_AllFree"
mm3d Campari OIS.*tif TerrainFinal_10_10_10_AllFree TerrainFinal_10_10_0.5_AllFree GCP=[GCP_3.xml,10,GCP-S2D_3.xml,10]  SigmaTieP=0.5 AllFree=true RapTxt=ResidualsReport_4.txt | tee reports/rapport_CampariAero_10_10_0.5_AllFree.txt >> logfile
python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_10_10_0.5_AllFree.txt
python ${scripts_dir}/delete_GCP.py --factor ${factor} --GCP GCP_3.xml --S2D GCP-S2D_3.xml --GCP_save GCP_4.xml --S2D_save GCP-S2D_4.xml --report_residuals ResidualsReport_4.txt

# Sixième itération : aéro finale
echo "Campari 10_10_0.5_AllFree_Final"
mm3d Campari OIS.*tif TerrainFinal_10_10_10_AllFree TerrainFinal_10_10_0.5_AllFree_Final GCP=[GCP_4.xml,10,GCP-S2D_4.xml,10]  SigmaTieP=0.5 AllFree=true RapTxt=ResidualsReport_5.txt | tee reports/rapport_CampariAero_10_10_0.5_AllFree_Final.txt >> logfile
${scripts_dir}/AnalyseRapportMicMac.LINUX AnalyseRapportResidusMICMAC ResidualsReport_5.txt --export_ogr_appuis_mesure PtsAppuiMesure.geojson --export_ogr_appuis_calcul PtsAppuiCalcul.geojson --export_ogr_residus_appuis VecteursResidusAppui.geojson --epsg ${EPSG} >> logfile
python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_10_10_0.5_AllFree_Final.txt

#Analyse des résidus sur les points d'appuis
#Dans le cas où l'erreur est trop grande, alors on utilise les points d'appuis trouvés dans le sous-échantillonnage 10. Cela peut arriver lorsque les dalles ne se superposent pas correctement
python ${scripts_dir}/analyze_residual_vectors.py --input_geojson VecteursResidusAppui.geojson --input_appuis GCP_4.xml --scripts ${scripts_dir} --etape 1  --filter_GCP ${filter_GCP}

sh ${scripts_dir}/create_ortho_mns.sh ${scripts_dir} ${CPU} ${TA}

sh ${scripts_dir}/create_ortho.sh ${scripts_dir} ${TA} ${ortho} ${CPU}