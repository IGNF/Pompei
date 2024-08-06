# Chaîne de traitement Hiatus sans la conversion en tif des images jpg
# Utile lorsque l'on s'est trompé dans les paramètres pour la recherche des repères de fond de chambre

repertoire_chantier=$1
metadonnees_xml=$2
nb_reperes_fiduciaux=$3 #int
cibles=$4 # [0, 1]
Kugelhupf_image_seuillee=$5 #[0, 1]
presence_artefacts=$6 #[0, 1]
forcer_verticale=$7 #[0, 1]
ortho=$8 # storeref, wms, histo, dalles
algo=$9 # a pour Aubry, srtm pour SRTM
pt_appuis_filtres=${10} #[0, 1]
create_ortho_mns=${11} #[0, 1]
create_ortho_mnt=${12} #[0, 1]
CPU=${13}


if test "$#" = 0; then
    echo "hiatus_after_convert_jp2.sh : permet de reprendre Hiatus après la conversion des images numérisées de jp2 à tiff. Permet notamment de changer les paramètres pour la détection des repères de fond de chambre"
    echo "repertoire_chantier : path : nouveau répertoire de travail"
    echo "metadonnees_xml : path : doit être dans l'ancien répertoire de travail"
    echo "nb_reperes_fiduciaux : int"
    echo "cibles : [0, 1]"
    echo "Kugelhupf_image_seuillee : [0, 1]"
    echo "presence_artefacts : [0, 1]"
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

    cp ${ancien_repertoire}/*.tif ${repertoire_chantier}
    rm ${repertoire_chantier}/*_Masq.tif 
    rm ${repertoire_chantier}/OIS-Reech*.tif
    rm ${repertoire_chantier}/filtre.tif
    cp ${metadonnees_xml} ${repertoire_chantier}
    metadonnees_xml=$(basename ${metadonnees_xml})
    mkdir ${repertoire_chantier}/metadata
    cp -r ${ancien_repertoire}/metadata/*.txt ${repertoire_chantier}/metadata/


    cd ${repertoire_chantier}
    repertoire_chantier=./
    mkdir rapports

    python ${repertoire_scripts}/preparer_chantier.py --scripts ${repertoire_scripts} --TA ${metadonnees_xml} --nb_fiduciaux ${nb_reperes_fiduciaux} --resolution_scannage 0.021 --presence_artefacts ${presence_artefacts} --cibles ${cibles} --images_seuillees ${Kugelhupf_image_seuillee} 
    sh correction_cliches.sh ${repertoire_scripts}

    sh tapioca.sh ${repertoire_scripts}

    sh ${repertoire_scripts}/HomolFilterMasq.sh ${presence_artefacts} ${repertoire_scripts}

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