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



# Chaîne de traitement pour traiter les chantiers Pompei compliqués


TA=$1
nb_fiducial_marks=$2 #int
targets=$3 # [0, 1]
Kugelhupf_apply_threshold=$4 #[0, 1]
remove_artefacts=$5 #[0, 1]
ortho=$6 # storeref, wms, histo, dalles
CPU=$7
delete=$8





if test "$#" = 0; then
    echo "pompei_complique.sh : Chaîne de traitement complète"
    echo "TA : path"
    echo "nb_fiducial_marks : int"
    echo "targets : [0, 1]"
    echo "Kugelhupf_apply_threshold : [0, 1]"
    echo "remove_artefacts : [0, 1]"
    echo "ortho : [storeref, wms, histo, dalles]"
    echo "CPU : int"
    echo "delete : [0, 1]"
else

    workspace=$(dirname ${TA})
    rm workspace.txt
    echo $workspace >> workspace.txt
    scripts_dir=$(realpath "scripts")
    cd ${workspace}
    TA=$(basename ${TA})

    mkdir reports
    if test ${ortho} = "storeref"; then
        echo "N'oubliez pas de monter store-ref sur votre ordinateur"
    fi

    sh ${scripts_dir}/convert_jp2_to_tif.sh

    python ${scripts_dir}/initialize_files.py --scripts ${scripts_dir} --TA ${TA} --nb_fiducial_marks ${nb_fiducial_marks} --remove_artefacts ${remove_artefacts} --targets ${targets} --apply_threshold ${Kugelhupf_apply_threshold}

    sh correct_geometrically_images.sh ${scripts_dir}

    sh find_tie_points.sh ${scripts_dir}

    sh ${scripts_dir}/filter_tie_points.sh ${remove_artefacts} ${scripts_dir} >> logfile

    sh ${scripts_dir}/download_ortho_MNS.sh ${scripts_dir} ${ortho} ${TA} >> logfile

    sh ${scripts_dir}/pompei_rapide/appuisSousEch10.sh ${scripts_dir} ${TA} ${CPU}

    sh ${scripts_dir}/pompei_rapide/appuis.sh ${scripts_dir} ${TA} ${CPU}

    sh ${scripts_dir}/pompei_rapide/aero.sh ${scripts_dir}

    sh ${scripts_dir}/create_ortho.sh ${scripts_dir} ${TA} ${ortho} ${CPU} ${delete}

fi

