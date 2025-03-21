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



# Chaîne de traitement Pompei après avoir recherché les points d'appuis
# Utile lorsque l'on veut refaire le filtrage des points d'appuis

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
    echo "pompei_before_aero.sh : pour reprendre Pompei une fois les points d'appuis trouvés. Sert notamment si l'on veut changer le paramètre filter_GCP"
    echo "workspace : path : nouveau répertoire de travail"
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

    sh ${scripts_dir}/aero.sh ${scripts_dir} ${filter_GCP} ${algo} ${delete}

    if test ${create_ortho_mns} = "1"; then

        sh ${scripts_dir}/create_ortho_mns.sh ${scripts_dir} ${CPU} ${TA} ${delete}
    
    fi

    if test ${create_ortho_mnt} = "1"; then

        sh ${scripts_dir}/create_ortho.sh ${scripts_dir} ${TA} ${ortho} ${CPU} ${delete}

    fi
fi