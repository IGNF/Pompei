repertoire_scripts=$1
pt_appuis_filtres=$2

#Ce code est utilisé dans le cas où l'erreur à l'issue de la première aéro est trop grande (plus de 25 pixels d'erreur en planimétrie).
#On utilise alors l'aéro sur les points d'appuis trouvés dans le sous-échantillonnage 10 

cd TraitementAPPssech10


#On aborde maintenant la partie traitee en local
#Prise en compte de la version corrigee precedemment par "nouveau RANSAC"
mv resultpi resultpt



#Sur les petits chantiers, il n'y a qu'une seule dalle qui s'appelle Orthophotomosaic.tif
if test -f ../Ortho-MEC-Malt-Abs-Ratafia/Orthophotomosaic_Tile_0_0.tif; then
    ${repertoire_scripts}/HIATUS.LINUX Reproj resultpt bidon bidon Orthophotomosaic_Tile_0_0.ori Orthophotomosaic_Tile_0_0.ori resultpi
    ${repertoire_scripts}/RANSAC resultpi resultpif --taille_case 5000 > /dev/null
    #On reprojette en terrain
    ${repertoire_scripts}/HIATUS.LINUX ReprojTerrain resultpif Orthophotomosaic_Tile_0_0.ori Orthophotomosaic_Tile_0_0.ori resultpifreproj
else
    ${repertoire_scripts}/HIATUS.LINUX Reproj resultpt bidon bidon Orthophotomosaic_Tile.ori Orthophotomosaic_Tile.ori resultpi
    ${repertoire_scripts}/RANSAC resultpi resultpif --taille_case 5000 > /dev/null
    #On reprojette en terrain
    ${repertoire_scripts}/HIATUS.LINUX ReprojTerrain resultpif Orthophotomosaic_Tile.ori Orthophotomosaic_Tile.ori resultpifreproj
fi

EPSG=`cat ../metadata/EPSG.txt`


#On aborde maintenant la partie avec MNS...
ls ../metadata/mns/*.tif > liste_mns_bdortho.txt

python ${repertoire_scripts}/ajouter_points_appuis.py --appuis_BDOrtho_existants pts_bdortho.txt --appuis_histo_existants pts_orthomicmac_abs.txt --appuis_BDOrtho_ajout ajout_appuis_BDortho.shp --appuis_histo_ajout ajout_appuis_histo.shp


ls ../MEC-Malt-Abs-Ratafia/MNS_Final*.tif > liste_mnsmicmac.txt
${repertoire_scripts}/HIATUS.LINUX AssocierZ_fichierpts2D:multiMNS pts_bdortho.txt liste_mns_bdortho.txt pts3D_bdortho.txt ; 
${repertoire_scripts}/HIATUS.LINUX AssocierZ_fichierpts2D:multiMNS pts_orthomicmac_abs.txt liste_mnsmicmac.txt pts3D_orthomicmac_abs.txt


#On recharge les deux fichiers 3D pour nettoyage des valeurs aberrantes (nodata = 9999) et preparation de letape suivante.
${repertoire_scripts}/HIATUS.LINUX BilanPts3D pts3D_bdortho.txt pts3D_orthomicmac_abs.txt pts3D_bdortho_net.txt pts3D_orthomicmac_abs_net.txt


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
${repertoire_scripts}/HIATUS.LINUX BilanApp2MICMAC pts3D_bdortho_net.txt liste_cliches.txt ../MesuresAppuis-S2D.xml ../MesuresAppuis-S3D.xml ../appuis.xml ../id_appuis.txt 
cd ..

cp MesuresAppuis-S2D.xml MesuresAvantFiltrageAppuis-S2D.xml;
cp appuis.xml appuis_avant_filtrage.xml;


cd TraitementAPPssech10
#Si on choisit de filtrer les points d'appuis pour ne conserver que ceux qui sont dans des villages
if test ${pt_appuis_filtres} -eq 1; then
    python ${repertoire_scripts}/filtrer_points_appuis.py --appuis ../appuis_avant_filtrage.xml --S2D ../MesuresAvantFiltrageAppuis-S2D.xml --metadata ../metadata --appuis_save ../appuis.xml --S2D_save ../MesuresAppuis-S2D.xml --etape 10;
fi

cd ..


#Mise en place avec les points d'appuis
echo "Campari 10_10_10"
mm3d Campari OIS.*tif Abs-Ratafia-AllFree TerrainFinal_10_10_10 GCP=[appuis.xml,10,MesuresAppuis-S2D.xml,10]  SigmaTieP=10 RapTxt=RapportResidus.txt| tee rapports/rapport_CampariAero_10_10_10.txt >> logfile

#Analyse de rapport_CampariAero_10_10_10 
python ${repertoire_scripts}/analyse_Campari.py --input_rapport rapports/rapport_CampariAero_10_10_10.txt

mkdir iter0
mv MesuresAppuis-S2D.xml iter0/
mv appuis.xml iter0/
mv RapportResidus.txt iter0/
python ${repertoire_scripts}/supprimer_appuis.py --facteur 3 --appuis iter0/appuis.xml --S2D iter0/MesuresAppuis-S2D.xml --appuis_save appuis.xml --S2D_save MesuresAppuis-S2D.xml --rapportResidus iter0/RapportResidus.txt


#On permet la modification sur les paramètres de la caméra
echo "Campari 10_10_10_AllFree"
mm3d Campari OIS.*tif TerrainFinal_10_10_10 TerrainFinal_10_10_10_AllFree_temp GCP=[appuis.xml,10,MesuresAppuis-S2D.xml,10]  SigmaTieP=10 AllFree=true RapTxt=RapportResidus.txt| tee rapports/rapport_CampariAero_10_10_10_AllFree_temp.txt >> logfile

#Analyse de rapport_CampariAero_10_10_10_AllFree_temp
python ${repertoire_scripts}/analyse_Campari.py --input_rapport rapports/rapport_CampariAero_10_10_10_AllFree_temp.txt

mkdir iter0
mv MesuresAppuis-S2D.xml iter0/
mv appuis.xml iter0/
mv RapportResidus.txt iter0/
python ${repertoire_scripts}/supprimer_appuis.py --facteur 3 --appuis iter0/appuis.xml --S2D iter0/MesuresAppuis-S2D.xml --appuis_save appuis.xml --S2D_save MesuresAppuis-S2D.xml --rapportResidus iter0/RapportResidus.txt

mm3d Campari OIS.*tif TerrainFinal_10_10_10 TerrainFinal_10_10_10_AllFree GCP=[appuis.xml,10,MesuresAppuis-S2D.xml,10]  SigmaTieP=10 AllFree=true RapTxt=RapportResidus.txt| tee rapports/rapport_CampariAero_10_10_10_AllFree.txt >> logfile

#Analyse de rapport_CampariAero_10_10_10_AllFree 
python ${repertoire_scripts}/analyse_Campari.py --input_rapport rapports/rapport_CampariAero_10_10_10_AllFree.txt

#On réduit l'écart-type
echo "Campari 10_10_0.5_AllFree"
mm3d Campari OIS.*tif TerrainFinal_10_10_10_AllFree TerrainFinal_10_10_0.5_AllFree GCP=[appuis.xml,10,MesuresAppuis-S2D.xml,10]  SigmaTieP=0.5 AllFree=true RapTxt=RapportResidus.txt | tee rapports/rapport_CampariAero_10_10_0.5_AllFree.txt >> logfile

#Analyse de rapport_CampariAero_10_10_0.5_AllFree 
python ${repertoire_scripts}/analyse_Campari.py --input_rapport rapports/rapport_CampariAero_10_10_0.5_AllFree.txt


mkdir iter1
mv MesuresAppuis-S2D.xml iter1/
mv appuis.xml iter1/
mv RapportResidus.txt iter1/
python ${repertoire_scripts}/supprimer_appuis.py --facteur 3 --appuis iter1/appuis.xml --S2D iter1/MesuresAppuis-S2D.xml --appuis_save appuis.xml --S2D_save MesuresAppuis-S2D.xml --rapportResidus iter1/RapportResidus.txt

#On relance les calculs
echo "Campari 10_10_0.5_AllFree_Final"
mm3d Campari OIS.*tif TerrainFinal_10_10_10_AllFree TerrainFinal_10_10_0.5_AllFree_Final GCP=[appuis.xml,10,MesuresAppuis-S2D.xml,10]  SigmaTieP=0.5 AllFree=true RapTxt=RapportResidus.txt | tee rapports/rapport_CampariAero_10_10_0.5_AllFree_Final.txt >> logfile
${repertoire_scripts}/AnalyseRapportMicMac.LINUX AnalyseRapportResidusMICMAC RapportResidus.txt --export_ogr_appuis_mesure PtsAppuiMesure.geojson --export_ogr_appuis_calcul PtsAppuiCalcul.geojson --export_ogr_residus_appuis VecteursResidusAppui.geojson --epsg ${EPSG} >> logfile

#Analyse de rapport_CampariAero_10_10_0.5_AllFree_Final
python ${repertoire_scripts}/analyse_Campari.py --input_rapport rapports/rapport_CampariAero_10_10_0.5_AllFree_Final.txt

#Analyse des résidus sur les points d'appuis
python ${repertoire_scripts}/analyse_Vecteurs_Residus.py --input_geojson VecteursResidusAppui.geojson --input_appuis appuis.xml --scripts ${repertoire_scripts} --etape 10