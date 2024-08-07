# Chaîne de traitement Hiatus après la recherche de points de liaisons
# Utile lorsque l'on veut refaire l'étape du Tapas en voulant supprimer certaines photos ou en supprimant l'étape de compensation

workspace=$1
TA=$2
force_vertical=$3 #[0, 1]
ortho=$4 # storeref, wms, histo, dalles
algo=$5 # a pour Aubry, srtm pour SRTM
filter_GCP=$6 #[0, 1]
create_ortho_mns=$7 #[0, 1]
create_ortho_mnt=$8 #[0, 1]
CPU=$9


if test "$#" = 0; then
    echo "hiatus_after_homolFilterMasq.sh : reprend Hiatus après la recherche des points de liaisons et avant l'orientation relative. Permet de supprimer manuellement d'éventuelles images avant de relancer le calcul de l'orientation relative"
    echo "workspace : path : nouveau répertoire de travail"
    echo "TA : path : doit être dans l'ancien répertoire de travail"
    echo "force_vertical : [0, 1]"
    echo "ortho : [storeref, wms, histo, dalles]"
    echo "algo : [a, srtm] : a pour Aubry, srtm pour SRTM"
    echo "filter_GCP : [0, 1]"
    echo "create_ortho_mns : [0, 1]"
    echo "create_ortho_mnt : [0, 1]"
    echo "CPU : int"
else

    mkdir ${workspace}
    scripts_dir=$(realpath "scripts")
    ancien_repertoire=$(dirname ${TA})

    rm -f ${workspace}
    mkdir ${workspace}
    mkdir ${workspace}/metadata/
    mkdir ${workspace}/Homol

    cp ${ancien_repertoire}/OIS-Reech*.tif ${workspace}
    cp ${TA} ${workspace}
    TA=$(basename ${TA})
    cp -r ${ancien_repertoire}/metadata/*.txt ${workspace}/metadata/
    cp -r ${ancien_repertoire}/Homol/* ${workspace}/Homol
    cp -r ${ancien_repertoire}/Homol-Ini/* ${workspace}/Homol
    cp -r ${ancien_repertoire}/Ori-Rel ${workspace}
    cp -r ${ancien_repertoire}/Ori-Nav ${workspace}
    cp -r ${ancien_repertoire}/Ori-CalibNum ${workspace}
    cp -r ${ancien_repertoire}/reports ${workspace}
    cp ${ancien_repertoire}/CouplesTA.xml ${workspace}
    cp ${ancien_repertoire}/filtre.xml ${workspace}
    cp ${ancien_repertoire}/filtre.tif ${workspace}
    cp ${ancien_repertoire}/filtre_artefacts.xml ${workspace}
    cp ${ancien_repertoire}/filtre_artefacts.tif ${workspace}
    cp ${ancien_repertoire}/MicMac-LocalChantierDescripteur.xml ${workspace}
    cp ${ancien_repertoire}/SommetsNav.csv ${workspace}


    cd ${workspace}
    workspace=./

    sh ${scripts_dir}/first_absolute_orientation.sh ${scripts_dir} ${force_vertical}

    sh ${scripts_dir}/second_absolute_orientation.sh ${scripts_dir}


    if test ${algo} = "srtm"; then
        sh ${scripts_dir}/GCP_SRTM.sh ${scripts_dir}
    else

        sh ${scripts_dir}/download_ortho_MNS.sh ${scripts_dir} ${ortho} ${TA} >> logfile
        
        sh ${scripts_dir}/find_GCP_downsampled_10.sh ${scripts_dir} ${CPU} >> logfile

        sh ${scripts_dir}/find_GCP.sh ${scripts_dir} ${CPU} >> logfile
        
    fi

    sh ${scripts_dir}/aero.sh ${scripts_dir} ${filter_GCP} ${algo}

    if test ${create_ortho_mns} = "1"; then

        sh ${scripts_dir}/create_ortho_mns.sh ${scripts_dir} ${workspace} ${CPU}
    
    fi

    if test ${create_ortho_mnt} = "1"; then

        sh ${scripts_dir}/create_ortho.sh ${scripts_dir} ${TA} ${ortho} ${CPU}

    fi
fi