# Chaîne de traitement Hiatus après avoir recherché les points d'appuis
# Utile lorsque l'on veut refaire le filtrage des points d'appuis

workspace=$1
TA=$2
ortho=$3 # storeref, wms, histo, dalles
algo=$4 # a pour Aubry, srtm pour SRTM
filter_GCP=$5 #[0, 1]
create_ortho_mns=$6 #[0, 1]
create_ortho_mnt=$7 #[0, 1]
CPU=$8

if test "$#" = 0; then
    echo "hiatus_before_aero.sh : pour reprendre Hiatus une fois les points d'appuis trouvés. Sert notamment si l'on veut changer le paramètre filter_GCP"
    echo "workspace : path : nouveau répertoire de travail"
    echo "algo : [a, srtm] : a pour Aubry, srtm pour SRTM"
    echo "filter_GCP : [0, 1]"
    echo "create_ortho_mns : [0, 1]"
    echo "create_ortho_mnt : [0, 1]"
    echo "CPU : int"
else
    
    rm -f ${workspace}
    mkdir ${workspace}
    scripts_dir=$(realpath "scripts")
    ancien_repertoire=$(dirname ${TA})

    cp ${ancien_repertoire}/OIS-Reech*.tif ${workspace}
    cp ${TA} ${workspace}
    TA=$(basename ${TA})
    cp -r ${ancien_repertoire}/metadata ${workspace}
    cp -r ${ancien_repertoire}/Homol ${workspace}
    cp -r ${ancien_repertoire}/reports ${workspace}
    cp -r ${ancien_repertoire}/TraitementAPP ${workspace}
    cp -r ${workspace}/TraitementAPP/resultpifreproj_save ${workspace}/TraitementAPP/resultpifreproj
    cp -r ${ancien_repertoire}/Ori-Abs-Ratafia-AllFree ${workspace}
    cp -r ${ancien_repertoire}/MEC-Malt-Abs-Ratafia ${workspace}
    cp -r ${ancien_repertoire}/Ortho-MEC-Malt-Abs-Ratafia ${workspace}
    cp ${ancien_repertoire}/filtre.xml ${workspace}
    cp ${ancien_repertoire}/filtre.tif ${workspace}
    cp ${ancien_repertoire}/filtre_artefacts.xml ${workspace}
    cp ${ancien_repertoire}/filtre_artefacts.tif ${workspace}
    cp ${ancien_repertoire}/logfile ${workspace}
    cp ${ancien_repertoire}/MicMac-LocalChantierDescripteur.xml ${workspace}

    cd ${workspace}
    workspace=./

    sh ${scripts_dir}/aero.sh ${scripts_dir} ${filter_GCP} ${algo}

    if test ${create_ortho_mns} = "1"; then

        sh ${scripts_dir}/create_ortho_mns.sh ${scripts_dir} ${workspace} ${CPU}
    
    fi

    if test ${create_ortho_mnt} = "1"; then

        sh ${scripts_dir}/create_ortho.sh ${scripts_dir} ${TA} ${ortho} ${CPU}

    fi
fi