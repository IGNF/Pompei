# Chaîne de traitement pour traiter les chantiers Hiatus compliqués


metadonnees_xml=$1
nb_reperes_fiduciaux=$2 #int
cibles=$3 # [0, 1]
Kugelhupf_image_seuillee=$4 #[0, 1]
presence_artefacts=$5 #[0, 1]
ortho=$6 # storeref, wms, histo, dalles
CPU=$7





if test "$#" = 0; then
    echo "hiatus_complique.sh : Chaîne de traitement complète"
    echo "metadonnees_xml : path"
    echo "nb_reperes_fiduciaux : int"
    echo "cibles : [0, 1]"
    echo "Kugelhupf_image_seuillee : [0, 1]"
    echo "presence_artefacts : [0, 1]"
    echo "ortho : [storeref, wms, histo, dalles]"
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

    python ${repertoire_scripts}/preparer_chantier.py --scripts ${repertoire_scripts} --TA ${metadonnees_xml} --nb_fiduciaux ${nb_reperes_fiduciaux} --resolution_scannage 0.021 --presence_artefacts ${presence_artefacts} --cibles ${cibles} --images_seuillees ${Kugelhupf_image_seuillee}

    sh correction_cliches.sh ${repertoire_scripts}

    sh tapioca.sh ${repertoire_scripts}

    sh ${repertoire_scripts}/HomolFilterMasq.sh ${presence_artefacts} ${repertoire_scripts} >> logfile

    sh ${repertoire_scripts}/download_ortho_MNS.sh ${repertoire_scripts} ${ortho} ${metadonnees_xml} >> logfile

    sh ${repertoire_scripts}/hiatus_rapide/appuisSousEch10.sh ${repertoire_scripts} ${metadonnees_xml} ${CPU}

    sh ${repertoire_scripts}/hiatus_rapide/appuis.sh ${repertoire_scripts} ${metadonnees_xml} ${CPU}

    sh ${repertoire_scripts}/hiatus_rapide/aero.sh ${repertoire_scripts}

    sh ${repertoire_scripts}/create_ortho.sh ${repertoire_scripts} ${metadonnees_xml} ${ortho} ${CPU}

fi

