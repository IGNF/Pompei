#Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/
#
#File main authors:
#- Célestin Huet
#This file is part of Hiatus: https://github.com/IGNF/Hiatus
#
#Hiatus is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#Hiatus is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#You should have received a copy of the GNU General Public License along with Hiatus. If not, see <https://www.gnu.org/licenses/>.


scripts_dir=$1
TA=$2
CPU=$3

pasdallage="1000"

mkdir appuisSousEch10
mkdir appuisSousEch10/dallage
# Création des couples d'imagettes ortho de référence/image ancienne
# Ces imagettes sont sous-échantillonnées d'un factor 10
# Cette étape permet uniquement de déterminer une translation à appliquer sur les 
# imagettes pour ensuite faire la recherche de points d'appuis sur des imagettes qui se chevauchent suffisamment
# Le risque étant que le géoréférencement des métadonnées soient trop approximatif et qu'il n'y ait pas assez de recouvrement entre les imagettes
python ${scripts_dir}/hiatus_rapide/create_one_ortho_per_image.py --metadata metadata --ta_xml ${TA} --factor 10 --workdir appuisSousEch10 --decalage False



cd appuisSousEch10

# On écrit dans liste_dalles.txt la liste des dalles sans leur extension
ls dallage/OIS*.tif > liste_dalles.txt
for i in `cat liste_dalles.txt` ; do
    fichier=$(basename ${i})
    fichiersansext=`echo ${fichier}|cut -d"." -f1`
    echo $fichiersansext >> liste_dalles_tmp
done
mv liste_dalles_tmp liste_dalles.txt


# pour chaque dalle
for i in `cat liste_dalles.txt` ; do 
    #Détection des points d intérêt
    echo -n "${scripts_dir}/MethodeAubry.LINUX dallage/bdortho_${i}.tif dallage/bdortho_${i}.kaub --maxlocaux --Mu ${scripts_dir}/MuAubry.tif --SigmaInv ${scripts_dir}/SigmaInvAubry.tif > /dev/null ; " >> bashtmp ;
    echo -n "${scripts_dir}/FiltrageMasqueDilat.LINUX --image dallage/bdortho_${i}.tif --rayon 10 --kp:bin dallage/bdortho_${i}.kaub --out dallage/bdortho_${i}.kaub > /dev/null ; " >> bashtmp ;
    #Mise en correspondance 
    echo -n "${scripts_dir}/MethodeAubryAppariement.LINUX Points:Image dallage/bdortho_${i}.kaub dallage/${i}.tif dallage/${i}.resultpi --Mu ${scripts_dir}/MuAubry.tif --SigmaInv ${scripts_dir}/SigmaInvAubry.tif > /dev/null ; " >> bashtmp 
    #On supprime les points situés dans les zones "noires"
    echo -n "${scripts_dir}/HIATUS.LINUX NettoyageResultZoneNoire  dallage/${i}.resultpi dallage/${i}.tif dallage/${i}.resultpi > /dev/null ; " >> bashtmp 
done
# On parallélise les calculs
${scripts_dir}/Bash2Make.LINUX bashtmp monmaketmp
make -k -f monmaketmp -j ${CPU};

# on reprojette les points trouvés en coordonnées terrain
python ${scripts_dir}/hiatus_rapide/reproj_appuis.py --factor 10 --regroupe False

# Pour chaque dalle, on applique un RANSAC pour sélectionner les points corrects.
# En effet, dans la méthode Aubry, il peut y avoir beaucoup de points faux
EPSG=`cat ../metadata/EPSG.txt`
ls dallage/*.resultpireproj > liste_resultpireproj.txt
for i in `cat liste_resultpireproj.txt` ; do
    fichier=$(basename ${i})
    fichiersansext=`echo ${fichier}|cut -d"." -f1`
    ${scripts_dir}/RANSAC dallage/${fichiersansext}.resultpireproj dallage/${fichiersansext}.ransac --taille_case 5000 > /dev/null
    ${scripts_dir}/HIATUS.LINUX ExportAsGJson dallage/${fichiersansext}.ransac pts_bdortho_${fichiersansext}.geojson pts_orthomicmac_${fichiersansext}.geojson ${EPSG}
done


#On rassemble tous les appariements dans un meme fichier
echo -n "" > resultpi
for i in `cat liste_resultpireproj.txt` ; do 
    cat ${i} >> resultpi ;
done