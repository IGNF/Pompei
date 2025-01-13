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
nb_fiducial_marks=$2 #int
targets=$3 # [0, 1]
Kugelhupf_apply_threshold=$4 #[0, 1]
remove_artefacts=$5 #[0, 1]



if test "$#" = 0; then
    echo "pompei_interface.sh : début de la chaîne contenant toutes les étapes avec des interfaces"
    echo "TA : path"
    echo "nb_fiducial_marks : int"
    echo "targets : [0, 1]"
    echo "Kugelhupf_image_filtree : [0, 1]"
    echo "remove_artefacts : [0, 1]"
else

    workspace=$(dirname ${TA})
    rm workspace.txt
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
    mkdir reports

    sh ${scripts_dir}/convert_jp2_to_tif.sh
    echo "A partir de maintenant, vous pouvez utiliser pompei_after_convert_jp2_to_tif.sh"

    python ${scripts_dir}/initialize_files.py --scripts ${scripts_dir} --TA ${TA} --nb_fiducial_marks ${nb_fiducial_marks} --remove_artefacts ${remove_artefacts} --targets ${targets} --apply_threshold ${Kugelhupf_apply_threshold} 

    sh correct_geometrically_images.sh ${scripts_dir}

    echo "Prochain script à lancer : pompei_after_interface.sh"
fi