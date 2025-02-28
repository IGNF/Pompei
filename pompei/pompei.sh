#Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/
#
#File main authors:
#- Célestin Huet
#- Arnaud Le Bris
#This file is part of Pompei: https://github.com/IGNF/Pompei
#
#Pompei is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#Pompei is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#You should have received a copy of the GNU General Public License along with Pompei. If not, see <https://www.gnu.org/licenses/>.


# Chaîne de traitement complète pour Pompei

set -e

TA=$1
nb_fiducial_marks=$2 #int
targets=$3 # [0, 1]
Kugelhupf_apply_threshold=$4 #[0, 1]
remove_artefacts=$5 #[0, 1]
ortho=$6 # storeref, wms, histo, dalles
algo=$7 # a pour Aubry, srtm pour SRTM
filter_GCP=$8 #[0, 1]
create_ortho_mns=$9 #[0, 1]
create_ortho_mnt=${10} #[0, 1]
CPU=${11}
delete=${12}


if test "$#" = 0; then
    echo "pompei.sh : Chaîne de traitement complète"
    echo "TA : path"
    echo "nb_fiducial_marks : int"
    echo "targets : [0, 1]"
    echo "Kugelhupf_apply_threshold : [0, 1]"
    echo "remove_artefacts : [0, 1]"
    echo "ortho : [storeref, wms, histo, dalles]"
    echo "algo : [a, s, srtm] : a pour Aubry, srtm pour SRTM"
    echo "filter_GCP : [0, 1]"
    echo "create_ortho_mns : [0, 1]"
    echo "create_ortho_mnt : [0, 1]"
    echo "CPU : int"
    echo "delete : [0, 1]"
else

    workspace=$(dirname ${TA})
    rm -f workspace.txt
    echo $workspace >> workspace.txt
    scripts_dir=$(realpath "scripts")

    if test ${ortho} = "storeref"; then
        if [ ! -d "/media/store-ref/modeles-numeriques-3D" ]; then
            echo "Vous devez monter store-ref sur votre ordinateur dans /media/store-ref/"
            exit 1
        fi
    fi

    if [ ! -f "scripts/api_key.env" ]; then
        echo "Vous devez avoir un fichier api_key.env dans scripts. Voyez le readme.md"
        exit 1
    fi

    cd ${workspace}
    TA=$(basename ${TA})
    mkdir -p reports

    sh ${scripts_dir}/convert_jp2_to_tif.sh
    echo "A partir de maintenant, vous pouvez utiliser pompei_after_convert_jp2_to_tif.sh"

    python ${scripts_dir}/initialize_files.py --scripts ${scripts_dir} --TA ${TA} --nb_fiducial_marks ${nb_fiducial_marks} --remove_artefacts ${remove_artefacts} --targets ${targets} --apply_threshold ${Kugelhupf_apply_threshold} 

    sh correct_geometrically_images.sh ${scripts_dir}

    sh find_tie_points.sh ${scripts_dir}

    sh ${scripts_dir}/filter_tie_points.sh ${remove_artefacts} ${scripts_dir} >> logfile
    echo "A partir de maintenant, vous pouvez utiliser pompei_after_homolFilterMasq.sh"

    sh ${scripts_dir}/first_absolute_orientation.sh ${scripts_dir} ${TA}

    sh ${scripts_dir}/second_absolute_orientation.sh ${scripts_dir} ${CPU} ${TA}
    echo "A partir de maintenant, vous pouvez utiliser pompei_after_Tawny.sh"


    if test ${algo} = "srtm"; then
        sh ${scripts_dir}/GCP_SRTM.sh ${scripts_dir}
    else

        sh ${scripts_dir}/download_ortho_MNS.sh ${scripts_dir} ${ortho} ${TA} >> logfile
        echo "A partir de maintenant, vous pouvez utiliser pompei_after_download_BD_Ortho.sh"
        
        sh ${scripts_dir}/find_GCP_downsampled_10.sh ${scripts_dir} ${CPU} >> logfile

        
        sh ${scripts_dir}/find_GCP.sh ${scripts_dir} ${CPU} ${delete} >> logfile
    fi

    echo "A partir de maintenant, vous pouvez utiliser pompei_before_aero.sh"
    sh ${scripts_dir}/aero.sh ${scripts_dir} ${filter_GCP} ${algo} ${delete}

    if test ${create_ortho_mns} = "1"; then

        sh ${scripts_dir}/create_ortho_mns.sh ${scripts_dir} ${CPU} ${TA} ${delete}
    
    fi

    if test ${create_ortho_mnt} = "1"; then

        sh ${scripts_dir}/create_ortho.sh ${scripts_dir} ${TA} ${ortho} ${CPU} ${delete}

    fi

    
fi