repertoire_scripts=$1
metadonnees_xml=$2
CPU=$3

pasdallage="1000"


 On génère un fichier ori pour chaque tuile
python ${repertoire_scripts}/hiatus_rapide/generate_ori.py --metadata metadata --ta_xml ${metadonnees_xml}

cd appuis

# On écrit dans liste_dalles.txt la liste des dalles sans leur extension
ls dallage/*.ori > liste_dalles.txt
for i in `cat liste_dalles.txt` ; do
    fichier=$(basename ${i})
    fichiersansext=`echo ${fichier}|cut -d"." -f1`
    echo $fichiersansext >> liste_dalles_tmp
done
mv liste_dalles_tmp liste_dalles.txt

# Pour chaque tuile
echo -n "" > bashtmp
for i in `cat liste_dalles.txt` ; do
    fichier=$(basename ${i})
    fichiersansext=`echo ${fichier}|cut -d"." -f1`
    # on récupère les points trouvés dans la recherche de points d'appuis sur imagette sous échantillonées et qui sont dans l'emprise de la dalle
    # L'emprise est définie par le fichier ori créé précédemment
    echo -n "${repertoire_scripts}/HIATUS.LINUX DecalageDalle:CropResult dallage/${i}.ori ../appuisSousEch10/resultpi dallage/${i}.pregeoref 5000 ; " >> bashtmp ;
    
    # Avec un Ransac, on calcule la meilleure similitude 2D
    echo -n "${repertoire_scripts}/RANSAC dallage/${i}.pregeoref dallage/${i}.pregeoreff --adresse_export_best_modele dallage/${i}.pregeoref_modsim > /dev/null ; " >> bashtmp ;
    
    # On conserve la translation à appliquer
    echo "${repertoire_scripts}/HIATUS.LINUX DecalageDalle:FromSim dallage/${fichiersansext}.ori dallage/${fichiersansext}.pregeoref_modsim > dallage/${i}.T.txt ; " >> bashtmp ;
done

# On parallélise les calculs
${repertoire_scripts}/Bash2Make.LINUX bashtmp monmaketmp;
make -k -f monmaketmp -j ${CPU} >> ../logfile;

# On crée les paires de tuiles, cette fois sans sous-échantillonnage et en tenant compte du décalage calculé par Ransac
cd ..
python ${repertoire_scripts}/hiatus_rapide/create_one_ortho_per_image.py --metadata metadata --ta_xml ${metadonnees_xml} --facteur 1 --workdir appuis  --decalage True


cd appuis
echo -n "" > bashtmp1
# Pour chaque tuile
for i in `cat liste_dalles.txt` ; do 
    #Detection des points d interet
    echo -n "${repertoire_scripts}/MethodeAubry.LINUX dallage/bdortho_${i}.tif dallage/bdortho_${i}.kaub --maxlocaux --Mu ${repertoire_scripts}/MuAubry.tif --SigmaInv ${repertoire_scripts}/SigmaInvAubry.tif > /dev/null ; " >> bashtmp1 ;
    echo -n "${repertoire_scripts}/FiltrageMasqueDilat.LINUX --image dallage/bdortho_${i}.tif --rayon 10 --kp:bin dallage/bdortho_${i}.kaub --out dallage/bdortho_${i}.kaub > /dev/null ; " >> bashtmp1 ;
    #Mise en correspondance 
    echo -n "${repertoire_scripts}/MethodeAubryAppariement.LINUX Points:Image dallage/bdortho_${i}.kaub dallage/${i}.tif dallage/${i}.resultpi --Mu ${repertoire_scripts}/MuAubry.tif --SigmaInv ${repertoire_scripts}/SigmaInvAubry.tif > /dev/null ; " >> bashtmp1 
    #On supprime les points situes dans les zones "noires"
    echo "${repertoire_scripts}/HIATUS.LINUX NettoyageResultZoneNoire  dallage/${i}.resultpi dallage/${i}.tif dallage/${i}.resultpi > /dev/null" >> bashtmp1 
done


#On parallélise les calculs
${repertoire_scripts}/Bash2Make.LINUX bashtmp1 monmaketmp1;
make -k -f monmaketmp1 -j ${CPU} >> ../logfile;

# On reprojette les points d'appuis en coordonnées terrain
# Les points d'appuis sont regroupés par image (ils étaient jusqu'à présent groupés par dalle), dans des fichiers .imagereproj
python ${repertoire_scripts}/hiatus_rapide/reproj_appuis.py --facteur 1 --regroupe True

EPSG=`cat ../metadata/EPSG.txt`
# Pour chaque fichier .imagereproj
ls dallage/*.imagereproj > liste_imagereproj.txt
for i in `cat liste_imagereproj.txt` ; do
    fichier=$(basename ${i})
    fichiersansext=`echo ${fichier}|cut -d"." -f1`
    # Avec Ransac, on supprime les points qui ne correspondent qu'à du bruit
    ${repertoire_scripts}/RANSAC dallage/${fichiersansext}.imagereproj dallage/${fichiersansext}.ransac --taille_case 5000 > /dev/null
    # On sauvegarde les points en format geojson pour contrôle
    ${repertoire_scripts}/HIATUS.LINUX ExportAsGJson dallage/${fichiersansext}.ransac pts_bdortho_${fichiersansext}.geojson pts_orthomicmac_${fichiersansext}.geojson ${EPSG}
done

# On convertit les points d'appuis en format adapté à MicMac
cd ..
python ${repertoire_scripts}/hiatus_rapide/Aubry_convert_GCP_to_mm3d.py --metadata metadata