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


TA=$1
remove_artefacts=$2 #[0, 1]
force_vertical=$3 #[0, 1]
ortho=$4 # storeref, wms, histo, dalles
algo=$5 # a pour Aubry, srtm pour SRTM
filter_GCP=$6 #[0, 1]
create_ortho_mns=$7 #[0, 1]
create_ortho_mnt=$8 #[0, 1]
CPU=$9


if test "$#" = 0; then
    echo "pompei_after_interface.sh : Partie de Pompei sans aucune interface. A lancer impérativement après pompei_interface.sh"
    echo "TA : path"
    echo "remove_artefacts : [0, 1]"
    echo "force_vertical : [0, 1]"
    echo "ortho : [storeref, wms, histo, dalles]"
    echo "algo : [a, srtm] : a pour Aubry, srtm pour SRTM"
    echo "filter_GCP : [0, 1]"
    echo "create_ortho_mns : [0, 1]"
    echo "create_ortho_mnt : [0, 1]"
    echo "CPU : int"
else

    if test ${ortho} = "storeref"; then
    echo "N'oubliez pas de monter store-ref sur votre ordinateur"
    fi

    workspace=$(dirname ${TA})
    rm workspace.txt
    echo $workspace >> workspace.txt
    scripts_dir=$(realpath "scripts")
    cd ${workspace}
    TA=$(basename ${TA})

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

        sh ${scripts_dir}/find_GCP.sh ${scripts_dir} ${CPU} >> logfile

    fi

    echo "A partir de maintenant, vous pouvez utiliser pompei_before_aero.sh"
    sh ${scripts_dir}/aero.sh ${scripts_dir} ${filter_GCP} ${algo}

    if test ${create_ortho_mns} = "1"; then

        sh ${scripts_dir}/create_ortho_mns.sh ${scripts_dir} ${CPU} ${TA}
    
    fi

    if test ${create_ortho_mnt} = "1"; then

        sh ${scripts_dir}/create_ortho.sh ${scripts_dir} ${TA} ${ortho} ${CPU}

    fi
fi