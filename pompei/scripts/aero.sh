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
filter_GCP=$2
algo=$3





cd TraitementAPP


EPSG=`cat ../metadata/EPSG.txt`
python ${scripts_dir}/reduction_resultpifreproj.py --input_resultpifreproj resultpifreproj
#On va aller chercher les z associe a ces points
${scripts_dir}/POMPEI.LINUX ExportAsTxt resultpifreproj pts_bdortho.txt pts_orthomicmac_abs.txt
${scripts_dir}/POMPEI.LINUX ExportAsGJson resultpifreproj pts_bdortho.geojson pts_orthomicmac_abs.geojson ${EPSG}

python ${scripts_dir}/add_GCP.py --appuis_BDOrtho_existants pts_bdortho.txt --appuis_histo_existants pts_orthomicmac_abs.txt --appuis_BDOrtho_ajout ../ajout_appuis_BDortho.shp --appuis_histo_ajout ../ajout_appuis_histo.shp

#On aborde maintenant la partie avec MNS...
ls ../metadata/mns/*.HDR ../metadata/mns/*.hdr > liste_mns_bdortho.txt
for i in `cat liste_mns_bdortho.txt` ; do ${scripts_dir}/convert_ori.LINUX hdr2ori ${i} ; done
ls ../metadata/mns/*.tif > liste_mns_bdortho.txt



#On applique un gdal translate sur le MNS calculé par MicMac car sinon cela coince dans AssocierZ_fichierpts2D
ls ../MEC-Malt-Abs-Ratafia/MNS_pyramide*.tif > liste_mnsmicmac.txt
for i in `cat liste_mnsmicmac.txt` ; do 
    mv ${i}  "${i}_copie.tif"; 
    gdal_translate "${i}_copie.tif" ${i};
    rm "${i}_copie.tif";
done

#Creation de la liste des MNS MICMAC a utiliser
ls ../MEC-Malt-Abs-Ratafia/MNS_pyramide*.tfw > liste_mnsmicmac.txt
for i in `cat liste_mnsmicmac.txt` ; do ${scripts_dir}/convert_ori.LINUX tfw2ori ${i} ; done
ls ../MEC-Malt-Abs-Ratafia/MNS_pyramide*.tif > liste_mnsmicmac.txt
${scripts_dir}/POMPEI.LINUX AssocierZ_fichierpts2D:multiMNS pts_bdortho.txt liste_mns_bdortho.txt pts3D_bdortho.txt >> ../logfile
${scripts_dir}/POMPEI.LINUX AssocierZ_fichierpts2D:multiMNS pts_orthomicmac_abs.txt liste_mnsmicmac.txt pts3D_orthomicmac_abs.txt >> ../logfile


#On recharge les deux fichiers 3D pour nettoyage des valeurs aberrantes (nodata = 9999) et preparation de letape suivante.
${scripts_dir}/POMPEI.LINUX BilanPts3D pts3D_bdortho.txt pts3D_orthomicmac_abs.txt pts3D_bdortho_net.txt pts3D_orthomicmac_abs_net.txt >> ../logfile


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
${scripts_dir}/POMPEI.LINUX BilanApp2MICMAC pts3D_bdortho_net.txt liste_cliches.txt ../GCP_before_filtering-S2D.xml ../GCP-S3D.xml ../GCP_before_filtering.xml ../id_GCP.txt >>../logfile
cd ..

cp GCP_before_filtering-S2D.xml GCP-S2D_0.xml;
cp GCP_before_filtering.xml GCP_0.xml;


#Si on choisit de filtrer les points d'appuis pour ne conserver que ceux qui sont dans des villages
if test ${filter_GCP} -eq 1; then
    python ${scripts_dir}/filter_GCP.py --appuis GCP_before_filtering.xml --S2D GCP_before_filtering-S2D.xml --metadata metadata --GCP_save GCP_0.xml --S2D_save GCP-S2D_0.xml --etape 1
fi


#Dans le cas où les points d'appuis ont été trouvés avec le SRTM, il faut être beaucoup plus souple sur les points d'appuis qu'avec les autres méthodes 
if test ${algo} = "srtm"; then
    factor=10
else
    factor=3
fi

# Première itération : ne sert qu'à supprimer les points d'appuis les plus faux
echo "Campari 10_10_10_tmp"
mm3d Campari OIS.*tif Abs-Ratafia-AllFree TerrainFinal_10_10_10_tmp GCP=[GCP_0.xml,10,GCP-S2D_0.xml,10]  SigmaTieP=10 RapTxt=ResidualsReport_0.txt| tee reports/rapport_CampariAero_10_10_10_tmp.txt >> logfile
python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_10_10_10_tmp.txt
python ${scripts_dir}/delete_GCP.py --factor ${factor} --GCP GCP_0.xml --S2D GCP-S2D_0.xml --GCP_save GCP_1.xml --S2D_save GCP-S2D_1.xml --report_residuals ResidualsReport_0.txt


# Deuxième itérations : on supprime des points d'appuis jusqu'à ce que le campari AllFree=true fonctionne
python ${scripts_dir}/aero_first_step.py --scripts ${scripts_dir} --facteur ${factor}

# Troisième itération : on permet la modification des paramètres internes. cette itération ne sert qu'à supprimer les points d'appuis les plus faux
echo "Campari 10_10_10_AllFree"
mm3d Campari OIS.*tif TerrainFinal_10_10_10 TerrainFinal_10_10_10_AllFree_temp GCP=[GCP_AF_0.xml,10,GCP-S2D_AF_0.xml,10]  SigmaTieP=10 AllFree=true RapTxt=ResidualsReport_AF_0.txt| tee reports/rapport_CampariAero_10_10_10_AllFree_temp.txt >> logfile
python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_10_10_10_AllFree_temp.txt
python ${scripts_dir}/delete_GCP.py --factor ${factor} --GCP GCP_AF_0.xml --S2D GCP-S2D_AF_0.xml --GCP_save GCP_AF_1.xml --S2D_save GCP-S2D_AF_1.xml --report_residuals ResidualsReport_AF_0.txt


# Quatrième itération : on permet la modification des paramètres internes. Pas de suppression de points d'appuis
mm3d Campari OIS.*tif TerrainFinal_10_10_10 TerrainFinal_10_10_10_AllFree GCP=[GCP_AF_1.xml,10,GCP-S2D_AF_1.xml,10]  SigmaTieP=10 AllFree=true RapTxt=ResidualsReport_AF_1.txt| tee reports/rapport_CampariAero_10_10_10_AllFree.txt >> logfile
python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_10_10_10_AllFree.txt

# Cinquième itération : on réduit l'écart-type sur les points de liaisons
echo "Campari 10_10_0.5_AllFree"
mm3d Campari OIS.*tif TerrainFinal_10_10_10_AllFree TerrainFinal_10_10_0.5_AllFree GCP=[GCP_AF_1.xml,10,GCP-S2D_AF_1.xml,10]  SigmaTieP=0.5 AllFree=true RapTxt=ResidualsReport_AF_2.txt | tee reports/rapport_CampariAero_10_10_0.5_AllFree.txt >> logfile
python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_10_10_0.5_AllFree.txt
python ${scripts_dir}/delete_GCP.py --factor ${factor} --GCP GCP_AF_1.xml --S2D GCP-S2D_AF_1.xml --GCP_save GCP_AF_2.xml --S2D_save GCP-S2D_AF_2.xml --report_residuals ResidualsReport_AF_2.txt

# Sixième itération : aéro finale
echo "Campari 10_10_0.5_AllFree_Final"
mm3d Campari OIS.*tif TerrainFinal_10_10_10_AllFree TerrainFinal_10_10_0.5_AllFree_Final GCP=[GCP_AF_2.xml,10,GCP-S2D_AF_2.xml,10]  SigmaTieP=0.5 AllFree=true RapTxt=ResidualsReport_AF_3.txt | tee reports/rapport_CampariAero_10_10_0.5_AllFree_Final.txt >> logfile
${scripts_dir}/AnalyseRapportMicMac.LINUX AnalyseRapportResidusMICMAC ResidualsReport_AF_3.txt --export_ogr_appuis_mesure PtsAppuiMesure.geojson --export_ogr_appuis_calcul PtsAppuiCalcul.geojson --export_ogr_residus_appuis VecteursResidusAppui.geojson --epsg ${EPSG} >> logfile
python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_10_10_0.5_AllFree_Final.txt

#Analyse des résidus sur les points d'appuis
#Dans le cas où l'erreur est trop grande, alors on utilise les points d'appuis trouvés dans le sous-échantillonnage 10. Cela peut arriver lorsque les dalles ne se superposent pas correctement
python ${scripts_dir}/analyze_residual_vectors.py --input_geojson VecteursResidusAppui.geojson --input_appuis GCP_AF_2.xml --scripts ${scripts_dir} --etape 1  --filter_GCP ${filter_GCP}
