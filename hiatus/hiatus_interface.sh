metadonnees_xml=$1
nb_reperes_fiduciaux=$2 #int
cibles=$3 # [0, 1]
Kugelhupf_image_seuillee=$4 #[0, 1]
presence_artefacts=$5 #[0, 1]



if test "$#" = 0; then
    echo "hiatus_interface.sh : début de la chaîne contenant toutes les étapes avec des interfaces"
    echo "metadonnees_xml : path"
    echo "nb_reperes_fiduciaux : int"
    echo "cibles : [0, 1]"
    echo "Kugelhupf_image_filtree : [0, 1]"
    echo "presence_artefacts : [0, 1]"
else

    repertoire_chantier=$(dirname ${metadonnees_xml})
    repertoire_scripts=$(realpath "scripts")
    cd ${repertoire_chantier}
    metadonnees_xml=$(basename ${metadonnees_xml})

    mkdir rapports

    sh ${repertoire_scripts}/convert_jp2.sh ${repertoire_scripts}

    python ${repertoire_scripts}/preparer_chantier.py --scripts ${repertoire_scripts} --TA ${metadonnees_xml} --nb_fiduciaux ${nb_reperes_fiduciaux} --resolution_scannage 0.021 --presence_artefacts ${presence_artefacts} --cibles ${cibles} --images_seuillees ${Kugelhupf_image_seuillee} 

    sh ${repertoire_chantier}/correction_cliches.sh ${repertoire_scripts}

    echo "Prochain script à lancer : hiatus_after_interface.sh"
fi