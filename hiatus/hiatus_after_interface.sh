metadonnees_xml=$1
presence_artefacts=$2 #[0, 1]
forcer_verticale=$3 #[0, 1]
ortho=$4 # storeref, wms, histo, dalles
algo=$5 # a pour Aubry, srtm pour SRTM
pt_appuis_filtres=$6 #[0, 1]
create_ortho_mns=$7 #[0, 1]
create_ortho_mnt=$8 #[0, 1]
CPU=$9


if test "$#" = 0; then
    echo "hiatus_after_interface.sh : Partie de Hiatus sans aucune interface. A lancer impérativement après hiatus_interface.sh"
    echo "metadonnees_xml : path"
    echo "presence_artefacts : [0, 1]"
    echo "forcer_verticale : [0, 1]"
    echo "ortho : [storeref, wms, histo, dalles]"
    echo "algo : [a, srtm] : a pour Aubry, srtm pour SRTM"
    echo "pt_appuis_filtres : [0, 1]"
    echo "create_ortho_mns : [0, 1]"
    echo "create_ortho_mnt : [0, 1]"
    echo "CPU : int"
else

    if test ${ortho} = "storeref"; then
    echo "N'oubliez pas de monter store-ref sur votre ordinateur"
    fi

    repertoire_chantier=$(dirname ${metadonnees_xml})
    repertoire_scripts=$(realpath "scripts")
    cd ${repertoire_chantier}
    metadonnees_xml=$(basename ${metadonnees_xml})

    sh tapioca.sh ${repertoire_scripts} >> logfile

    sh ${repertoire_scripts}/HomolFilterMasq.sh ${presence_artefacts} ${repertoire_scripts} >> logfile
    echo "A partir de maintenant, on peut utiliser hiatus_after_homolFilterMasq.sh"

    sh ${repertoire_scripts}/premiere_mise_en_place.sh ${repertoire_scripts} ${forcer_verticale}

    sh ${repertoire_scripts}/deuxieme_mise_en_place.sh ${repertoire_scripts}
    echo "A partir de maintenant, on peut utiliser hiatus_after_Tawny.sh"


    if test ${algo} = "srtm"; then
        sh ${repertoire_scripts}/points_appuis_SRTM.sh ${repertoire_scripts}
    else

        sh ${repertoire_scripts}/download_ortho_MNS.sh ${repertoire_scripts} ${ortho} ${metadonnees_xml} >> logfile
        echo "A partir de maintenant, on peut utiliser hiatus_after_download_BD_Ortho.sh"
        
        sh ${repertoire_scripts}/points_appuis_sous_echantillonnage_10.sh ${repertoire_scripts} ${CPU} >> logfile

        sh ${repertoire_scripts}/points_appuis.sh ${repertoire_scripts} ${CPU} >> logfile

    fi

    echo "A partir de maintenant, on peut utiliser hiatus_before_aero.sh"
    sh ${repertoire_scripts}/aero.sh ${repertoire_scripts} ${pt_appuis_filtres} ${algo}

    if test ${create_ortho_mns} = "1"; then

        sh ${repertoire_scripts}/create_ortho_mns.sh ${repertoire_scripts} ${repertoire_chantier} ${CPU}
    
    fi

    if test ${create_ortho_mnt} = "1"; then

        sh ${repertoire_scripts}/create_ortho.sh ${repertoire_scripts} ${metadonnees_xml} ${ortho} ${CPU}

    fi
fi