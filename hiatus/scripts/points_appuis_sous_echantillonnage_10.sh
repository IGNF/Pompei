repertoire_scripts=$1
CPU=$2

pasdallage="1000"



mkdir TraitementAPPssech10
cd TraitementAPPssech10
#repertoire_scripts=../${repertoire_scripts}

mkdir dallage

#On commence par daller les differentes orthoimages deja generees
ls ../Ortho-MEC-Malt-Abs-Ratafia/Orthophotomosaic_Tile_*tif > liste_tile.txt


for i in `cat liste_tile.txt` ; do
    fichier=$(basename ${i})
    nomdalle=${fichier%.*}
    cp ../Ortho-MEC-Malt-Abs-Ratafia/${nomdalle}.tif .
    ${repertoire_scripts}/convert_ori.LINUX tfw2ori ../Ortho-MEC-Malt-Abs-Ratafia/${nomdalle}.tfw ${nomdalle}.ori
    ${repertoire_scripts}/HIATUS.LINUX SousechOri ${nomdalle}.ori 10 ${nomdalle}.ssech10.ori
    echo "${nomdalle}.tif" > listetmp
    cat listetmp
    ${repertoire_scripts}/Decoupage.LINUX ${nomdalle}.ssech10.ori listetmp ${nomdalle}.ssech10.tif 
    rm listetmp
    ${repertoire_scripts}/Split.LINUX ${nomdalle}.ssech10.tif ${pasdallage} ${pasdallage} dallage/${nomdalle}
done


#On fait la liste des dalles creees en retirant les extensions
ls dallage/*.tif > liste_dalles.txt
for i in `cat liste_dalles.txt` ; do
fichier=$(basename ${i})
fichiersansext=`echo ${fichier}|cut -d"." -f1`
echo $fichiersansext >> liste_dalles_tmp
done
mv liste_dalles_tmp liste_dalles.txt


#Lister la BDOrtho
ls ../metadata/ortho/*.tfw > liste_bdortho.txt
for i in `cat liste_bdortho.txt` ; do 
${repertoire_scripts}/convert_ori.LINUX tfw2ori ${i} 
done
ls ../metadata/ortho/*.tif > liste_bdortho.txt


#On écrit dans un fichier les commandes à appliquer pour chaque dalle
echo -n "" > bashtmp
for i in `cat liste_dalles.txt` ; do 
#On cree une dalle d ortho superposable (a terme rajouter des marges ?)
echo -n "${repertoire_scripts}/Decoupage.LINUX dallage/${i}.ori liste_bdortho.txt dallage/bdortho_${i}.tif  ; " >> bashtmp ;
echo -n "${repertoire_scripts}/Ech_noif.LINUX Format dallage/bdortho_${i}.tif dallage/bdortho_${i}.tif ; " >> bashtmp ;
#Detection des points d interet
echo -n "${repertoire_scripts}/MethodeAubry.LINUX dallage/bdortho_${i}.tif dallage/bdortho_${i}.kaub --maxlocaux --Mu ${repertoire_scripts}/MuAubry.tif --SigmaInv ${repertoire_scripts}/SigmaInvAubry.tif > /dev/null ; " >> bashtmp ;
echo -n "${repertoire_scripts}/FiltrageMasqueDilat.LINUX --image dallage/bdortho_${i}.tif --rayon 10 --kp:bin dallage/bdortho_${i}.kaub --out dallage/bdortho_${i}.kaub > /dev/null ; " >> bashtmp ;
#Mise en correspondance 
echo -n "${repertoire_scripts}/MethodeAubryAppariement.LINUX Points:Image dallage/bdortho_${i}.kaub dallage/${i}.tif dallage/${i}.resultpi --Mu ${repertoire_scripts}/MuAubry.tif --SigmaInv ${repertoire_scripts}/SigmaInvAubry.tif > /dev/null ; " >> bashtmp 
#On supprime les points situes dans les zones "noires"
echo -n "${repertoire_scripts}/HIATUS.LINUX NettoyageResultZoneNoire  dallage/${i}.resultpi dallage/${i}.tif dallage/${i}.resultpi > /dev/null ; " >> bashtmp 
#On reprojette les coordonnees dans un referentiel commun (coordonnees images dans l ori de Orthophotomosaic) --> A faire en mieux
echo "${repertoire_scripts}/HIATUS.LINUX Reproj dallage/${i}.resultpi dallage/bdortho_${i}.ori dallage/${i}.ori Orthophotomosaic.ori Orthophotomosaic.ori dallage/${i}.resultpireproj " >> bashtmp
done

#On exécute les commandes pour chaque dalle
${repertoire_scripts}/Bash2Make.LINUX bashtmp monmaketmp
make -k -f monmaketmp -j ${CPU};


#On rassemble tous les appariements dans un meme fichier
echo -n "" > resultpi
for i in `cat liste_dalles.txt` ; do 
cat dallage/${i}.resultpireproj >> resultpi ;
done

#On ne conserve que 1000 points aléatoirement car si on en garde plus, l'étape Ransac dans points_appuis devient interminable.
#Est-ce que ce serait nécessaire de choisir d'abord les points qui sont en bordure du chantier et ensuite aléatoirement parmi les autres points ? 
python ${repertoire_scripts}/keep1000points.py --file resultpi

EPSG=`cat ../metadata/EPSG.txt`

###################################################################
#On aborde maintenant la partie traitee en local
${repertoire_scripts}/RANSAC resultpi resultpif --taille_case 5000 > /dev/null
#On reprojette en terrain
${repertoire_scripts}/HIATUS.LINUX ReprojTerrain resultpif Orthophotomosaic.ori Orthophotomosaic.ori resultpifreproj
#On va aller chercher les z associe a ces points
${repertoire_scripts}/HIATUS.LINUX ExportAsTxt resultpifreproj pts_bdortho.txt pts_orthomicmac_abs.txt
${repertoire_scripts}/HIATUS.LINUX ExportAsGJson resultpifreproj pts_bdortho.geojson pts_orthomicmac_abs.geojson ${EPSG}
###################################################################

