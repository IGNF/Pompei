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
CPU=$2
delete=$3

pasdallage="1000"

rm -rf TraitementAPP
mkdir TraitementAPP
cd TraitementAPP

mkdir dallage
ls ../Ortho-MEC-Malt-Abs-Ratafia/Orthophotomosaic_Tile_*tif > liste_tile.txt

#On commence par daller les differentes orthoimages deja generees
for i in `cat liste_tile.txt` ; do
    fichier=$(basename ${i})
    nomdalle=${fichier%.*}
    cp ../Ortho-MEC-Malt-Abs-Ratafia/${nomdalle}.tif .
    ${scripts_dir}/convert_ori.LINUX tfw2ori ../Ortho-MEC-Malt-Abs-Ratafia/${nomdalle}.tfw ${nomdalle}.ori
    ${scripts_dir}/Split.LINUX ${nomdalle}.tif ${pasdallage} ${pasdallage} dallage/${nomdalle}
done

python ${scripts_dir}/delete_black_images.py --path dallage --seuil_value 0 --seuil_prop 0.98

#On fait la liste des dalles creees
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
    ${scripts_dir}/convert_ori.LINUX tfw2ori ${i} 
done
ls ../metadata/ortho/*.tif > liste_bdortho.txt


#On écrit dans un fichier les commandes à appliquer pour chaque dalle
echo -n "" > bashtmp
for i in `cat liste_dalles.txt` ; do 
    #On cree une dalle d ortho superposable en tenant compte du décalage calculé dans find_GCP_downsampled_10.sh
    echo -n "${scripts_dir}/POMPEI.LINUX DecalageDalle:CropResult dallage/${i}.ori ../TraitementAPPssech10/resultpi dallage/${i}.pregeoref 5000 ; " >> bashtmp ;
    echo -n "${scripts_dir}/RANSAC dallage/${i}.pregeoref dallage/${i}.pregeoreff --adresse_export_best_modele dallage/${i}.pregeoref_modsim > /dev/null ; " >> bashtmp ;
    echo -n "${scripts_dir}/POMPEI.LINUX DecalageDalle:FromSim dallage/${i}.ori dallage/${i}.pregeoref_modsim > dallage/${i}.T.txt ; " >> bashtmp ;
    echo -n "${scripts_dir}/POMPEI.LINUX TranslatOri:m dallage/${i}.ori dallage/${i}.T.txt dallage/${i}.decal.ori ; " >> bashtmp ;
    echo -n "${scripts_dir}/Decoupage.LINUX dallage/${i}.decal.ori liste_bdortho.txt dallage/bdortho_${i}.tif > /dev/null ; " >> bashtmp ;
    echo -n "${scripts_dir}/Ech_noif.LINUX Format dallage/bdortho_${i}.tif dallage/bdortho_${i}.tif ; " >> bashtmp ;
    #Detection des points d interet
    echo -n "${scripts_dir}/MethodeAubry.LINUX dallage/bdortho_${i}.tif dallage/bdortho_${i}.kaub --maxlocaux --Mu ${scripts_dir}/MuAubry.tif --SigmaInv ${scripts_dir}/SigmaInvAubry.tif > /dev/null ; " >> bashtmp ;
    echo -n "${scripts_dir}/FiltrageMasqueDilat.LINUX --image dallage/bdortho_${i}.tif --rayon 10 --kp:bin dallage/bdortho_${i}.kaub --out dallage/bdortho_${i}.kaub > /dev/null ; " >> bashtmp ;
    #Mise en correspondance 
    echo -n "${scripts_dir}/MethodeAubryAppariement.LINUX Points:Image dallage/bdortho_${i}.kaub dallage/${i}.tif dallage/${i}.resultpi --Mu ${scripts_dir}/MuAubry.tif --SigmaInv ${scripts_dir}/SigmaInvAubry.tif > /dev/null ; " >> bashtmp 
    #On supprime les points situes dans les zones "noires"
    echo -n "${scripts_dir}/POMPEI.LINUX NettoyageResultZoneNoire  dallage/${i}.resultpi dallage/${i}.tif dallage/${i}.resultpi > /dev/null ; " >> bashtmp 
    #On reprojette les coordonnees dans un referentiel commun (coordonnees images dans l ori de Orthophotomosaic) --> A faire en mieux
    echo "${scripts_dir}/POMPEI.LINUX Reproj dallage/${i}.resultpi dallage/bdortho_${i}.ori dallage/${i}.ori Orthophotomosaic.ori Orthophotomosaic.ori dallage/${i}.resultpireproj " >> bashtmp
done


#On exécute les commandes pour chaque dalle
${scripts_dir}/Bash2Make.LINUX bashtmp monmaketmp
make -k -f monmaketmp -j ${CPU} >> ../logfile;


#On rassemble tous les appariements dans un meme fichier
echo -n "" > resultpi
for i in `cat liste_dalles.txt` ; do 
    cat dallage/${i}.resultpireproj >> resultpi ;
done


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

python ${scripts_dir}/reduction_resultpifreproj.py --input_resultpifreproj resultpifreproj

if test ${delete} -eq 1; then
    rm -rf Tmp-MM-Dir
fi