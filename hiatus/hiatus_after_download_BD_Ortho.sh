# Chaîne de traitement Hiatus après le téléchargement de la BD Ortho et du MNS
# Utile lorsque l'on veut refaire la recherche de points d'appuis

repertoire_chantier=$1
metadonnees_xml=$2
ortho=$3 # storeref, wms, histo, dalles
algo=$4 # a pour Aubry, srtm pour SRTM
pt_appuis_filtres=$5 #[0, 1]
create_ortho_mns=$6 #[0, 1]
create_ortho_mnt=$7 #[0, 1]
CPU=$8

if test "$#" = 0; then
    echo "hiatus_after_download_BD_Ortho.sh : reprend Hiatus après le téléchargement de la BD Ortho et avant la recherche de points d'appuis. Permet notamment de changer d'algorithme de recherche de points d'appuis"
    echo "repertoire_chantier : path"
    echo "metadonnees_xml : path"
    echo "algo : [a, srtm] : a pour Aubry, srtm pour SRTM"
    echo "pt_appuis_filtres : [0, 1]"
    echo "create_ortho_mns : [0, 1]"
    echo "create_ortho_mnt : [0, 1]"
    echo "CPU : int"
else

    rm -f ${repertoire_chantier}
    mkdir ${repertoire_chantier}
    repertoire_scripts=$(realpath "scripts")
    ancien_repertoire=$(dirname ${metadonnees_xml})

    cp ${ancien_repertoire}/OIS-Reech*.tif ${repertoire_chantier}
    cp ${metadonnees_xml} ${repertoire_chantier}
    metadonnees_xml=$(basename ${metadonnees_xml})
    cp -r ${ancien_repertoire}/metadata ${repertoire_chantier}
    cp -r ${ancien_repertoire}/Homol ${repertoire_chantier}
    cp -r ${ancien_repertoire}/rapports ${repertoire_chantier}
    cp -r ${ancien_repertoire}/Ori-Abs-Ratafia-AllFree ${repertoire_chantier}
    cp -r ${ancien_repertoire}/MEC-Malt-Abs-Ratafia ${repertoire_chantier}
    cp -r ${ancien_repertoire}/Ortho-MEC-Malt-Abs-Ratafia ${repertoire_chantier}
    cp ${ancien_repertoire}/filtre.xml ${repertoire_chantier}
    cp ${ancien_repertoire}/filtre.tif ${repertoire_chantier}
    cp ${ancien_repertoire}/filtre_artefacts.xml ${repertoire_chantier}
    cp ${ancien_repertoire}/filtre_artefacts.tif ${repertoire_chantier}
    cp ${ancien_repertoire}/logfile ${repertoire_chantier}
    cp ${ancien_repertoire}/MicMac-LocalChantierDescripteur.xml ${repertoire_chantier}

    cd ${repertoire_chantier}
    repertoire_chantier=./

    if test ${algo} = "srtm"; then
        sh ${repertoire_scripts}/points_appuis_SRTM.sh ${repertoire_scripts}
    else
        
        sh ${repertoire_scripts}/points_appuis_sous_echantillonnage_10.sh ${repertoire_scripts} ${CPU} >> logfile

        sh ${repertoire_scripts}/points_appuis.sh ${repertoire_scripts} ${CPU} >> logfile

    fi

    sh ${repertoire_scripts}/aero.sh ${repertoire_scripts} ${pt_appuis_filtres} ${algo}

    if test ${create_ortho_mns} = "1"; then

        sh ${repertoire_scripts}/create_ortho_mns.sh ${repertoire_scripts} ${repertoire_chantier} ${CPU}
    
    fi

    if test ${create_ortho_mnt} = "1"; then

        sh ${repertoire_scripts}/create_ortho.sh ${repertoire_scripts} ${metadonnees_xml} ${ortho} ${CPU}

    fi
fi