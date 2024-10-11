#Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/
#
#File main authors:
#- Célestin Huet
#This file is part of Pompei: https://github.com/IGNF/Pompei
#
#Pompei is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#Pompei is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#You should have received a copy of the GNU General Public License along with Pompei. If not, see <https://www.gnu.org/licenses/>.


# Chaîne de traitement Pompei sans la conversion en tif des images jpg
# Utile lorsque l'on s'est trompé dans les paramètres pour la recherche des repères de fond de chambre

workspace=$1
TA=$2
nb_fiducial_marks=$3 #int
targets=$4 # [0, 1]
Kugelhupf_apply_threshold=$5 #[0, 1]
remove_artefacts=$6 #[0, 1]
force_vertical=$7 #[0, 1]
ortho=$8 # storeref, wms, histo, dalles
algo=$9 # a pour Aubry, srtm pour SRTM
filter_GCP=${10} #[0, 1]
create_ortho_mns=${11} #[0, 1]
create_ortho_mnt=${12} #[0, 1]
CPU=${13}


if test "$#" = 0; then
    echo "pompei_after_convert_jp2_to_tif.sh : permet de reprendre Pompei après la conversion des images numérisées de jp2 à tiff. Permet notamment de changer les paramètres pour la détection des repères de fond de chambre"
    echo "workspace : path : nouveau répertoire de travail"
    echo "TA : path : doit être dans l'ancien répertoire de travail"
    echo "nb_fiducial_marks : int"
    echo "targets : [0, 1]"
    echo "Kugelhupf_apply_threshold : [0, 1]"
    echo "remove_artefacts : [0, 1]"
    echo "force_vertical : [0, 1]"
    echo "ortho : [storeref, wms, histo, dalles]"
    echo "algo : [a, srtm] : a pour Aubry, srtm pour SRTM"
    echo "filter_GCP : [0, 1]"
    echo "create_ortho_mns : [0, 1]"
    echo "create_ortho_mnt : [0, 1]"
    echo "CPU : int"
else
    mkdir ${workspace}
    rm workspace.txt
    echo $workspace >> workspace.txt
    scripts_dir=$(realpath "scripts")
    ancien_repertoire=$(dirname ${TA})

    cp ${ancien_repertoire}/*.tif ${workspace}
    rm ${workspace}/*_Masq.tif 
    rm ${workspace}/OIS-Reech*.tif
    rm ${workspace}/filtre.tif
    cp ${TA} ${workspace}
    TA=$(basename ${TA})
    mkdir ${workspace}/metadata
    cp -r ${ancien_repertoire}/metadata/*.txt ${workspace}/metadata/


    cd ${workspace}
    workspace=./
    mkdir reports

    python ${scripts_dir}/initialize_files.py --scripts ${scripts_dir} --TA ${TA} --nb_fiducial_marks ${nb_fiducial_marks} --scan_resolution 0.021 --remove_artefacts ${remove_artefacts} --targets ${targets} --apply_threshold ${Kugelhupf_apply_threshold} 
    sh correct_geometrically_images.sh ${scripts_dir}

    sh find_tie_points.sh ${scripts_dir}

    sh ${scripts_dir}/filter_tie_points.sh ${remove_artefacts} ${scripts_dir}

    sh ${scripts_dir}/first_absolute_orientation.sh ${scripts_dir} ${force_vertical}

    sh ${scripts_dir}/second_absolute_orientation.sh ${scripts_dir} ${CPU}


    if test ${algo} = "srtm"; then
        sh ${scripts_dir}/GCP_SRTM.sh ${scripts_dir}
    else

        sh ${scripts_dir}/download_ortho_MNS.sh ${scripts_dir} ${ortho} ${TA} >> logfile
        
        sh ${scripts_dir}/find_GCP_downsampled_10.sh ${scripts_dir} ${CPU} >> logfile

        sh ${scripts_dir}/find_GCP.sh ${scripts_dir} ${CPU} >> logfile
        
    fi

    sh ${scripts_dir}/aero.sh ${scripts_dir} ${filter_GCP} ${algo}

    if test ${create_ortho_mns} = "1"; then

        sh ${scripts_dir}/create_ortho_mns.sh ${scripts_dir} ${CPU} ${TA}
    
    fi

    if test ${create_ortho_mnt} = "1"; then

        sh ${scripts_dir}/create_ortho.sh ${scripts_dir} ${TA} ${ortho} ${CPU}

    fi
fi