# Chaîne de traitement Hiatus après avoir recherché les points d'appuis
# Utile lorsque l'on veut refaire le filtrage des points d'appuis

repertoire_chantier=$1
metadonnees_xml=$2
ortho=$3 # storeref, wms, histo, dalles
algo=$4 # a pour Aubry, srtm pour SRTM
pt_appuis_filtres=$5 #[0, 1]
create_ortho_mns=$6 #[0, 1]
create_ortho_mnt=$7 #[0, 1]
CPU=$8

if test "$#" = 0; then
    echo "hiatus_before_aero.sh : pour reprendre Hiatus une fois les points d'appuis trouvés. Sert notamment si l'on veut changer le paramètre pt_appuis_filtres"
    echo "repertoire_chantier : path : nouveau répertoire de travail"
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
    cp -r ${ancien_repertoire}/TraitementAPP ${repertoire_chantier}
    cp -r ${repertoire_chantier}/TraitementAPP/resultpifreproj_save ${repertoire_chantier}/TraitementAPP/resultpifreproj
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

    sh ${repertoire_scripts}/aero.sh ${repertoire_scripts} ${pt_appuis_filtres} ${algo}

    if test ${create_ortho_mns} = "1"; then

        sh ${repertoire_scripts}/create_ortho_mns.sh ${repertoire_scripts} ${repertoire_chantier} ${CPU}
    
    fi

    if test ${create_ortho_mnt} = "1"; then

        sh ${repertoire_scripts}/create_ortho.sh ${repertoire_scripts} ${metadonnees_xml} ${ortho} ${CPU}

    fi
fi