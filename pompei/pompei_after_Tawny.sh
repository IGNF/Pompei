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


# Chaîne de traitement Pompei après la première orthophoto géoréférencée à une centaine de mètres près
# Utile lorsque l'on veut refaire le téléchargement de la BD Ortho et du MNS

workspace=$1
TA=$2
ortho=$3 # storeref, wms, histo, dalles
algo=$4 # a pour Aubry, srtm pour SRTM
filter_GCP=$5 #[0, 1]
create_ortho_mns=$6 #[0, 1]
create_ortho_mnt=$7 #[0, 1]
CPU=$8
delete=$9


if test "$#" = 0; then
    echo "pompei_after_Tawny.sh : pour reprendre Pompei après la création de la première orthophoto (celle à 100 près). Sert notamment si l'on veut reprendre le téléchargement de l'ortho de référence"
    echo "workspace : path : nouveau répertoire de travail"
    echo "TA : path"
    echo "ortho : [storeref, wms, histo, dalles]"
    echo "algo : [a, srtm] : a pour Aubry, srtm pour SRTM"
    echo "filter_GCP : [0, 1]"
    echo "create_ortho_mns : [0, 1]"
    echo "create_ortho_mnt : [0, 1]"
    echo "CPU : int"
    echo "delete : [0, 1]"
else

    rm -f ${workspace}
    mkdir ${workspace}
    rm workspace.txt
    echo $workspace >> workspace.txt
    scripts_dir=$(realpath "scripts")
    ancien_repertoire=$(dirname ${TA})

    cp ${ancien_repertoire}/OIS-Reech*.tif ${workspace}
    cp ${TA} ${workspace}
    TA=$(basename ${TA})

    mkdir ${workspace}/metadata
    cp -r ${ancien_repertoire}/metadata/*.txt ${workspace}/metadata/
    cp -r ${ancien_repertoire}/Homol ${workspace}
    cp -r ${ancien_repertoire}/reports ${workspace}
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


    if test ${algo} = "srtm"; then
        sh ${scripts_dir}/GCP_SRTM.sh ${scripts_dir}
    else

        sh ${scripts_dir}/download_ortho_MNS.sh ${scripts_dir} ${ortho} ${TA} >> logfile
        
        sh ${scripts_dir}/find_GCP_downsampled_10.sh ${scripts_dir} ${CPU} >> logfile

        sh ${scripts_dir}/find_GCP.sh ${scripts_dir} ${CPU} >> logfile
        
    fi

    sh ${scripts_dir}/aero.sh ${scripts_dir} ${filter_GCP} ${algo} ${delete}

    if test ${create_ortho_mns} = "1"; then

        sh ${scripts_dir}/create_ortho_mns.sh ${scripts_dir} ${CPU} ${TA} ${delete}
    
    fi

    if test ${create_ortho_mnt} = "1"; then

        sh ${scripts_dir}/create_ortho.sh ${scripts_dir} ${TA} ${ortho} ${CPU} ${delete}

    fi
fi