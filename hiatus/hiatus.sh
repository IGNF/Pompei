# Chaîne de traitement complète pour Hiatus


metadonnees_xml=$1
nb_reperes_fiduciaux=$2 #int
cibles=$3 # [0, 1]
Kugelhupf_image_seuillee=$4 #[0, 1]
presence_artefacts=$5 #[0, 1]
forcer_verticale=$6 #[0, 1]
ortho=$7 # storeref, wms, histo, dalles
algo=$8 # a pour Aubry, srtm pour SRTM
pt_appuis_filtres=$9 #[0, 1]
create_ortho_mns=${10} #[0, 1]
create_ortho_mnt=${11} #[0, 1]
CPU=${12}




if test "$#" = 0; then
    echo "hiatus.sh : Chaîne de traitement complète"
    echo "metadonnees_xml : path"
    echo "nb_reperes_fiduciaux : int"
    echo "cibles : [0, 1]"
    echo "Kugelhupf_image_seuillee : [0, 1]"
    echo "presence_artefacts : [0, 1]"
    echo "forcer_verticale : [0, 1]"
    echo "ortho : [storeref, wms, histo, dalles]"
    echo "algo : [a, s, srtm] : a pour Aubry, srtm pour SRTM"
    echo "pt_appuis_filtres : [0, 1]"
    echo "create_ortho_mns : [0, 1]"
    echo "create_ortho_mnt : [0, 1]"
    echo "CPU : int"
else

    repertoire_chantier=$(dirname ${metadonnees_xml})
    repertoire_scripts=$(realpath "scripts")
    cd ${repertoire_chantier}
    metadonnees_xml=$(basename ${metadonnees_xml})

    mkdir rapports
    if test ${ortho} = "storeref"; then
        echo "N'oubliez pas de monter store-ref sur votre ordinateur"
    fi

    sh ${repertoire_scripts}/convert_jp2.sh
    echo "A partir de maintenant, on peut utiliser hiatus_after_convert_jp2.sh"

    python ${repertoire_scripts}/preparer_chantier.py --scripts ${repertoire_scripts} --TA ${metadonnees_xml} --nb_fiduciaux ${nb_reperes_fiduciaux} --resolution_scannage 0.021 --presence_artefacts ${presence_artefacts} --cibles ${cibles} --images_seuillees ${Kugelhupf_image_seuillee} 

    sh correction_cliches.sh ${repertoire_scripts}

    sh tapioca.sh ${repertoire_scripts}

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