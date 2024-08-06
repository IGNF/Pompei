# Chaîne de traitement Hiatus après la recherche de points de liaisons
# Utile lorsque l'on veut refaire l'étape du Tapas en voulant supprimer certaines photos ou en supprimant l'étape de compensation

repertoire_chantier=$1
metadonnees_xml=$2
forcer_verticale=$3 #[0, 1]
ortho=$4 # storeref, wms, histo, dalles
algo=$5 # a pour Aubry, srtm pour SRTM
pt_appuis_filtres=$6 #[0, 1]
create_ortho_mns=$7 #[0, 1]
create_ortho_mnt=$8 #[0, 1]
CPU=$9


if test "$#" = 0; then
    echo "hiatus_after_homolFilterMasq.sh : reprend Hiatus après la recherche des points de liaisons et avant l'orientation relative. Permet de supprimer manuellement d'éventuelles images avant de relancer le calcul de l'orientation relative"
    echo "repertoire_chantier : path : nouveau répertoire de travail"
    echo "metadonnees_xml : path : doit être dans l'ancien répertoire de travail"
    echo "forcer_verticale : [0, 1]"
    echo "ortho : [storeref, wms, histo, dalles]"
    echo "algo : [a, srtm] : a pour Aubry, srtm pour SRTM"
    echo "pt_appuis_filtres : [0, 1]"
    echo "create_ortho_mns : [0, 1]"
    echo "create_ortho_mnt : [0, 1]"
    echo "CPU : int"
else

    mkdir ${repertoire_chantier}
    repertoire_scripts=$(realpath "scripts")
    ancien_repertoire=$(dirname ${metadonnees_xml})

    rm -f ${repertoire_chantier}
    mkdir ${repertoire_chantier}
    mkdir ${repertoire_chantier}/metadata/
    mkdir ${repertoire_chantier}/Homol

    cp ${ancien_repertoire}/OIS-Reech*.tif ${repertoire_chantier}
    cp ${metadonnees_xml} ${repertoire_chantier}
    metadonnees_xml=$(basename ${metadonnees_xml})
    cp -r ${ancien_repertoire}/metadata/*.txt ${repertoire_chantier}/metadata/
    cp -r ${ancien_repertoire}/Homol/* ${repertoire_chantier}/Homol
    cp -r ${ancien_repertoire}/Homol-Ini/* ${repertoire_chantier}/Homol
    cp -r ${ancien_repertoire}/Ori-Rel ${repertoire_chantier}
    cp -r ${ancien_repertoire}/Ori-Nav ${repertoire_chantier}
    cp -r ${ancien_repertoire}/Ori-CalibNum ${repertoire_chantier}
    cp -r ${ancien_repertoire}/rapports ${repertoire_chantier}
    cp ${ancien_repertoire}/CouplesTA.xml ${repertoire_chantier}
    cp ${ancien_repertoire}/filtre.xml ${repertoire_chantier}
    cp ${ancien_repertoire}/filtre.tif ${repertoire_chantier}
    cp ${ancien_repertoire}/filtre_artefacts.xml ${repertoire_chantier}
    cp ${ancien_repertoire}/filtre_artefacts.tif ${repertoire_chantier}
    cp ${ancien_repertoire}/MicMac-LocalChantierDescripteur.xml ${repertoire_chantier}
    cp ${ancien_repertoire}/SommetsNav.csv ${repertoire_chantier}


    cd ${repertoire_chantier}
    repertoire_chantier=./

    sh ${repertoire_scripts}/premiere_mise_en_place.sh ${repertoire_scripts} ${forcer_verticale}

    sh ${repertoire_scripts}/deuxieme_mise_en_place.sh ${repertoire_scripts}


    if test ${algo} = "srtm"; then
        sh ${repertoire_scripts}/points_appuis_SRTM.sh ${repertoire_scripts}
    else

        sh ${repertoire_scripts}/download_ortho_MNS.sh ${repertoire_scripts} ${ortho} ${metadonnees_xml} >> logfile
        
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