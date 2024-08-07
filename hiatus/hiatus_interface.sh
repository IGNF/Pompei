TA=$1
nb_fiducial_marks=$2 #int
targets=$3 # [0, 1]
Kugelhupf_apply_threshold=$4 #[0, 1]
remove_artefacts=$5 #[0, 1]



if test "$#" = 0; then
    echo "hiatus_interface.sh : début de la chaîne contenant toutes les étapes avec des interfaces"
    echo "TA : path"
    echo "nb_fiducial_marks : int"
    echo "targets : [0, 1]"
    echo "Kugelhupf_image_filtree : [0, 1]"
    echo "remove_artefacts : [0, 1]"
else

    workspace=$(dirname ${TA})
    scripts_dir=$(realpath "scripts")
    cd ${workspace}
    TA=$(basename ${TA})

    mkdir reports

    sh ${scripts_dir}/convert_jp2_to_tif.sh ${scripts_dir}

    python ${scripts_dir}/initialize_files.py --scripts ${scripts_dir} --TA ${TA} --nb_fiducial_marks ${nb_fiducial_marks} --scan_resolution 0.021 --remove_artefacts ${remove_artefacts} --targets ${targets} --apply_threshold ${Kugelhupf_apply_threshold} 

    sh ${workspace}/correct_geometrically_images.sh ${scripts_dir}

    echo "Prochain script à lancer : hiatus_after_interface.sh"
fi