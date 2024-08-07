scripts_dir=$1
filter_GCP=$2
algo=$3





cd TraitementAPP


EPSG=`cat ../metadata/EPSG.txt`
python ${scripts_dir}/reduction_resultpifreproj.py --input_resultpifreproj resultpifreproj
#On va aller chercher les z associe a ces points
${scripts_dir}/HIATUS.LINUX ExportAsTxt resultpifreproj pts_bdortho.txt pts_orthomicmac_abs.txt
${scripts_dir}/HIATUS.LINUX ExportAsGJson resultpifreproj pts_bdortho.geojson pts_orthomicmac_abs.geojson ${EPSG}

python ${scripts_dir}/add_GCP.py --appuis_BDOrtho_existants pts_bdortho.txt --appuis_histo_existants pts_orthomicmac_abs.txt --appuis_BDOrtho_ajout ../ajout_appuis_BDortho.shp --appuis_histo_ajout ../ajout_appuis_histo.shp

#On aborde maintenant la partie avec MNS...
ls ../metadata/mns/*.HDR ../metadata/mns/*.hdr > liste_mns_bdortho.txt
for i in `cat liste_mns_bdortho.txt` ; do ${scripts_dir}/convert_ori.LINUX hdr2ori ${i} ; done
ls ../metadata/mns/*.tif > liste_mns_bdortho.txt



#On applique un gdal translate sur le MNS calculé par MicMac car sinon cela coince dans AssocierZ_fichierpts2D
ls ../MEC-Malt-Abs-Ratafia/MNS_Final*.tif > liste_mnsmicmac.txt
for i in `cat liste_mnsmicmac.txt` ; do 
    mv ${i}  "${i}_copie.tif"; 
    gdal_translate "${i}_copie.tif" ${i};
    rm "${i}_copie.tif";
done

#Creation de la liste des MNS MICMAC a utiliser
ls ../MEC-Malt-Abs-Ratafia/MNS_Final*.tfw > liste_mnsmicmac.txt
for i in `cat liste_mnsmicmac.txt` ; do ${scripts_dir}/convert_ori.LINUX tfw2ori ${i} ; done
ls ../MEC-Malt-Abs-Ratafia/MNS_Final*.tif > liste_mnsmicmac.txt
${scripts_dir}/HIATUS.LINUX AssocierZ_fichierpts2D:multiMNS pts_bdortho.txt liste_mns_bdortho.txt pts3D_bdortho.txt >> ../logfile
${scripts_dir}/HIATUS.LINUX AssocierZ_fichierpts2D:multiMNS pts_orthomicmac_abs.txt liste_mnsmicmac.txt pts3D_orthomicmac_abs.txt >> ../logfile


#On recharge les deux fichiers 3D pour nettoyage des valeurs aberrantes (nodata = 9999) et preparation de letape suivante.
${scripts_dir}/HIATUS.LINUX BilanPts3D pts3D_bdortho.txt pts3D_orthomicmac_abs.txt pts3D_bdortho_net.txt pts3D_orthomicmac_abs_net.txt >> ../logfile


#On va mettre en forme pour Apero/micmac
#Faire la liste des cliches
ls ../OIS-*.tif > liste_cliches.txt
echo -n "" > liste_cliches_tmp
for i in `cat liste_cliches.txt` ; do
fichier=$(basename ${i})
fichiersansext=`echo ${fichier}|cut -d"." -f1`
echo $fichiersansext >> liste_cliches_tmp
done
mv liste_cliches_tmp liste_cliches.txt


#Pour chaque cliche, reprojeter les differents points
#Relire sur l ensemble des cliches
cd ..
for i in `cat TraitementAPP/liste_cliches.txt` ; do 
mm3d Tenor Ori-Abs-Ratafia-AllFree/Orientation-${i}.tif.xml TraitementAPP/pts3D_orthomicmac_abs_net.txt TraitementAPP/${i}.tif.pts2d >>../logfile
done
cd TraitementAPP


#Maintenant, on peut relire tous les fichiers et ecrire ce qui est attendu par micmac..
${scripts_dir}/HIATUS.LINUX BilanApp2MICMAC pts3D_bdortho_net.txt liste_cliches.txt ../GCP-S2D.xml ../GCP-S3D.xml ../GCP.xml ../id_GCP.txt >>../logfile
cd ..

cp GCP-S2D.xml GCP_before_filtering-S2D.xml;
cp GCP.xml GCP_before_filtering.xml;






#Si on choisit de filtrer les points d'appuis pour ne conserver que ceux qui sont dans des villages
if test ${filter_GCP} -eq 1; then
    python ${scripts_dir}/filter_GCP.py --appuis GCP_before_filtering.xml --S2D GCP_before_filtering-S2D.xml --metadata metadata --GCP_save GCP.xml --S2D_save GCP-S2D.xml --etape 1
fi


#Dans le cas où les points d'appuis ont été trouvés avec le SRTM, il faut être beaucoup plus souple sur les points d'appuis qu'avec les autres méthodes 
if test ${algo} = "srtm"; then
    factor=10
else
    factor=3
fi


#Mise en place avec les points d'appuis
echo "Campari 10_10_10"
mm3d Campari OIS.*tif Abs-Ratafia-AllFree TerrainFinal_10_10_10 GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=10 RapTxt=ResidualsReport.txt| tee reports/rapport_CampariAero_10_10_10.txt >> logfile
#mm3d Campari OIS.*tif Abs TerrainFinal_10_10_10 GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=10 RapTxt=ResidualsReport.txt| tee reports/rapport_CampariAero_10_10_10.txt >> logfile

#Analyse de rapport_CampariAero_10_10_10 
python ${scripts_dir}/analyze_Campari.py --input_report reports/rapport_CampariAero_10_10_10.txt

mkdir iter0
mv GCP-S2D.xml iter0/
mv GCP.xml iter0/
mv ResidualsReport.txt iter0/
python ${scripts_dir}/delete_GCP.py --factor ${factor} --GCP iter0/GCP.xml --S2D iter0/GCP-S2D.xml --GCP_save GCP.xml --S2D_save GCP-S2D.xml --report_residuals iter0/ResidualsReport.txt


#On permet la modification sur les paramètres de la caméra
echo "Campari 10_10_10_AllFree"
mm3d Campari OIS.*tif TerrainFinal_10_10_10 TerrainFinal_10_10_10_AllFree_temp GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=10 AllFree=true RapTxt=ResidualsReport.txt| tee reports/rapport_CampariAero_10_10_10_AllFree_temp.txt >> logfile

#Analyse de rapport_CampariAero_10_10_10_AllFree_temp
python ${scripts_dir}/analyze_Campari.py --input_report reports/rapport_CampariAero_10_10_10_AllFree_temp.txt

mkdir iter0
mv GCP-S2D.xml iter0/
mv GCP.xml iter0/
mv ResidualsReport.txt iter0/
python ${scripts_dir}/delete_GCP.py --factor ${factor} --GCP iter0/GCP.xml --S2D iter0/GCP-S2D.xml --GCP_save GCP.xml --S2D_save GCP-S2D.xml --report_residuals iter0/ResidualsReport.txt

mm3d Campari OIS.*tif TerrainFinal_10_10_10 TerrainFinal_10_10_10_AllFree GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=10 AllFree=true RapTxt=ResidualsReport.txt| tee reports/rapport_CampariAero_10_10_10_AllFree.txt >> logfile

#Analyse de rapport_CampariAero_10_10_10_AllFree 
python ${scripts_dir}/analyze_Campari.py --input_report reports/rapport_CampariAero_10_10_10_AllFree.txt

#On réduit l'écart-type
echo "Campari 10_10_0.5_AllFree"
mm3d Campari OIS.*tif TerrainFinal_10_10_10_AllFree TerrainFinal_10_10_0.5_AllFree GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=0.5 AllFree=true RapTxt=ResidualsReport.txt | tee reports/rapport_CampariAero_10_10_0.5_AllFree.txt >> logfile

#Analyse de rapport_CampariAero_10_10_0.5_AllFree 
python ${scripts_dir}/analyze_Campari.py --input_report reports/rapport_CampariAero_10_10_0.5_AllFree.txt


mkdir iter1
mv GCP-S2D.xml iter1/
mv GCP.xml iter1/
mv ResidualsReport.txt iter1/
python ${scripts_dir}/delete_GCP.py --factor ${factor} --GCP iter1/GCP.xml --S2D iter1/GCP-S2D.xml --GCP_save GCP.xml --S2D_save GCP-S2D.xml --report_residuals iter1/ResidualsReport.txt

#On relance les calculs
echo "Campari 10_10_0.5_AllFree_Final"
mm3d Campari OIS.*tif TerrainFinal_10_10_10_AllFree TerrainFinal_10_10_0.5_AllFree_Final GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=0.5 AllFree=true RapTxt=ResidualsReport.txt | tee reports/rapport_CampariAero_10_10_0.5_AllFree_Final.txt >> logfile
${scripts_dir}/AnalyseRapportMicMac.LINUX AnalyseRapportResidusMICMAC ResidualsReport.txt --export_ogr_appuis_mesure PtsAppuiMesure.geojson --export_ogr_appuis_calcul PtsAppuiCalcul.geojson --export_ogr_residus_appuis VecteursResidusAppui.geojson --epsg ${EPSG} >> logfile

#Analyse de rapport_CampariAero_10_10_0.5_AllFree_Final
python ${scripts_dir}/analyze_Campari.py --input_report reports/rapport_CampariAero_10_10_0.5_AllFree_Final.txt

#Analyse des résidus sur les points d'appuis
#Dans le cas où l'erreur est trop grande, alors on utilise les points d'appuis trouvés dans le sous-échantillonnage 10. Cela peut arriver lorsque les dalles ne se superposent pas correctement
python ${scripts_dir}/analyze_residual_vectors.py --input_geojson VecteursResidusAppui.geojson --input_appuis GCP.xml --scripts ${scripts_dir} --etape 1  --filter_GCP ${filter_GCP}

