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

#Ce code est utilisé dans le cas où l'erreur à l'issue de la première aéro est trop grande (plus de 25 pixels d'erreur en planimétrie).
#On utilise alors l'aéro sur les points d'appuis trouvés dans le sous-échantillonnage 10 

cd TraitementAPPssech10


#On aborde maintenant la partie traitee en local
#Prise en compte de la version corrigee precedemment par "nouveau RANSAC"
mv resultpi resultpt



#Sur les petits chantiers, il n'y a qu'une seule dalle qui s'appelle Orthophotomosaic.tif
if test -f ../Ortho-MEC-Malt-Abs-Ratafia/Orthophotomosaic_Tile_0_0.tif; then
    ${scripts_dir}/POMPEI.LINUX Reproj resultpt bidon bidon Orthophotomosaic_Tile_0_0.ori Orthophotomosaic_Tile_0_0.ori resultpi
    ${scripts_dir}/RANSAC resultpi resultpif --taille_case 5000 > /dev/null
    #On reprojette en terrain
    ${scripts_dir}/POMPEI.LINUX ReprojTerrain resultpif Orthophotomosaic_Tile_0_0.ori Orthophotomosaic_Tile_0_0.ori resultpifreproj
else
    ${scripts_dir}/POMPEI.LINUX Reproj resultpt bidon bidon Orthophotomosaic_Tile.ori Orthophotomosaic_Tile.ori resultpi
    ${scripts_dir}/RANSAC resultpi resultpif --taille_case 5000 > /dev/null
    #On reprojette en terrain
    ${scripts_dir}/POMPEI.LINUX ReprojTerrain resultpif Orthophotomosaic_Tile.ori Orthophotomosaic_Tile.ori resultpifreproj
fi

EPSG=`cat ../metadata/EPSG.txt`


#On aborde maintenant la partie avec MNS...
ls ../metadata/mns/*.tif > liste_mns_bdortho.txt

python ${scripts_dir}/add_GCP.py --appuis_BDOrtho_existants pts_bdortho.txt --appuis_histo_existants pts_orthomicmac_abs.txt --appuis_BDOrtho_ajout ajout_appuis_BDortho.shp --appuis_histo_ajout ajout_appuis_histo.shp


ls ../MEC-Malt-Abs-Ratafia/MNS_pyramide*.tif > liste_mnsmicmac.txt
${scripts_dir}/POMPEI.LINUX AssocierZ_fichierpts2D:multiMNS pts_bdortho.txt liste_mns_bdortho.txt pts3D_bdortho.txt ; 
${scripts_dir}/POMPEI.LINUX AssocierZ_fichierpts2D:multiMNS pts_orthomicmac_abs.txt liste_mnsmicmac.txt pts3D_orthomicmac_abs.txt


#On recharge les deux fichiers 3D pour nettoyage des valeurs aberrantes (nodata = 9999) et preparation de letape suivante.
${scripts_dir}/POMPEI.LINUX BilanPts3D pts3D_bdortho.txt pts3D_orthomicmac_abs.txt pts3D_bdortho_net.txt pts3D_orthomicmac_abs_net.txt


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
for i in `cat TraitementAPPssech10/liste_cliches.txt` ; do 
mm3d Tenor Ori-Abs-Ratafia-AllFree/Orientation-${i}.tif.xml TraitementAPPssech10/pts3D_orthomicmac_abs_net.txt TraitementAPPssech10/${i}.tif.pts2d
done
cd TraitementAPPssech10


#Maintenant, on peut relire tous les fichiers et ecrire ce qui est attendu par micmac..
${scripts_dir}/POMPEI.LINUX BilanApp2MICMAC pts3D_bdortho_net.txt liste_cliches.txt ../GCP-S2D.xml ../GCP-S3D.xml ../GCP.xml ../id_GCP.txt 
cd ..

cp GCP-S2D.xml GCP_before_filtering-S2D.xml;
cp GCP.xml GCP_before_filtering.xml;


cd TraitementAPPssech10
#Si on choisit de filtrer les points d'appuis pour ne conserver que ceux qui sont dans des villages
if test ${filter_GCP} -eq 1; then
    python ${scripts_dir}/filter_GCP.py --appuis ../GCP_before_filtering.xml --S2D ../GCP_before_filtering-S2D.xml --metadata ../metadata --GCP_save ../GCP.xml --S2D_save ../GCP-S2D.xml --etape 10;
fi

cd ..


#Mise en place avec les points d'appuis
echo "Campari 10_10_10"
mm3d Campari OIS.*tif Abs-Ratafia-AllFree TerrainFinal_10_10_10 GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=10 RapTxt=ResidualsReport.txt| tee reports/rapport_CampariAero_10_10_10.txt >> logfile

#Analyse de rapport_CampariAero_10_10_10 
python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_10_10_10.txt

mkdir iter0
mv GCP-S2D.xml iter0/
mv GCP.xml iter0/
mv ResidualsReport.txt iter0/
python ${scripts_dir}/delete_GCP.py --factor 3 --GCP iter0/GCP.xml --S2D iter0/GCP-S2D.xml --GCP_save GCP.xml --S2D_save GCP-S2D.xml --report_residuals iter0/ResidualsReport.txt


#On permet la modification sur les paramètres de la caméra
echo "Campari 10_10_10_AllFree"
mm3d Campari OIS.*tif TerrainFinal_10_10_10 TerrainFinal_10_10_10_AllFree_temp GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=10 AllFree=true RapTxt=ResidualsReport.txt| tee reports/rapport_CampariAero_10_10_10_AllFree_temp.txt >> logfile

#Analyse de rapport_CampariAero_10_10_10_AllFree_temp
python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_10_10_10_AllFree_temp.txt

mkdir iter0
mv GCP-S2D.xml iter0/
mv GCP.xml iter0/
mv ResidualsReport.txt iter0/
python ${scripts_dir}/delete_GCP.py --factor 3 --GCP iter0/GCP.xml --S2D iter0/GCP-S2D.xml --GCP_save GCP.xml --S2D_save GCP-S2D.xml --report_residuals iter0/ResidualsReport.txt

mm3d Campari OIS.*tif TerrainFinal_10_10_10 TerrainFinal_10_10_10_AllFree GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=10 AllFree=true RapTxt=ResidualsReport.txt| tee reports/rapport_CampariAero_10_10_10_AllFree.txt >> logfile

#Analyse de rapport_CampariAero_10_10_10_AllFree 
python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_10_10_10_AllFree.txt

#On réduit l'écart-type
echo "Campari 10_10_0.5_AllFree"
mm3d Campari OIS.*tif TerrainFinal_10_10_10_AllFree TerrainFinal_10_10_0.5_AllFree GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=0.5 AllFree=true RapTxt=ResidualsReport.txt | tee reports/rapport_CampariAero_10_10_0.5_AllFree.txt >> logfile

#Analyse de rapport_CampariAero_10_10_0.5_AllFree 
python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_10_10_0.5_AllFree.txt


mkdir iter1
mv GCP-S2D.xml iter1/
mv GCP.xml iter1/
mv ResidualsReport.txt iter1/
python ${scripts_dir}/delete_GCP.py --factor 3 --GCP iter1/GCP.xml --S2D iter1/GCP-S2D.xml --GCP_save GCP.xml --S2D_save GCP-S2D.xml --report_residuals iter1/ResidualsReport.txt

#On relance les calculs
echo "Campari 10_10_0.5_AllFree_Final"
mm3d Campari OIS.*tif TerrainFinal_10_10_10_AllFree TerrainFinal_10_10_0.5_AllFree_Final GCP=[GCP.xml,10,GCP-S2D.xml,10]  SigmaTieP=0.5 AllFree=true RapTxt=ResidualsReport.txt | tee reports/rapport_CampariAero_10_10_0.5_AllFree_Final.txt >> logfile
${scripts_dir}/AnalyseRapportMicMac.LINUX AnalyseRapportResidusMICMAC ResidualsReport.txt --export_ogr_appuis_mesure PtsAppuiMesure.geojson --export_ogr_appuis_calcul PtsAppuiCalcul.geojson --export_ogr_residus_appuis VecteursResidusAppui.geojson --epsg ${EPSG} >> logfile

#Analyse de rapport_CampariAero_10_10_0.5_AllFree_Final
python ${scripts_dir}/analyze_Tapas.py --input_report reports/rapport_CampariAero_10_10_0.5_AllFree_Final.txt

#Analyse des résidus sur les points d'appuis
python ${scripts_dir}/analyze_residual_vectors.py --input_geojson VecteursResidusAppui.geojson --input_appuis GCP.xml --scripts ${scripts_dir} --etape 10