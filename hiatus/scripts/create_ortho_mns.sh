scripts_dir=$1
workspace=$2
CPU=$3


#Calcul d'une première orthophoto
echo "Malt"
mm3d Malt Ortho OIS.*tif TerrainFinal_10_10_0.5_AllFree_Final MasqImGlob=filtre.tif NbVI=2 UseTA=0 NbProc=30 EZA=1 DirMEC=MEC-Malt-Final >> logfile

echo "Tawny"
mm3d Tawny Ortho-MEC-Malt-Final/ RadiomEgal=false >> logfile

python ${scripts_dir}/create_Z_Num_tfw.py --input_Malt MEC-Malt-Final


sh ${scripts_dir}/equalize_radiometry.sh ${scripts_dir} ${CPU}

sh ${scripts_dir}/build_vrt.sh ${scripts_dir} metadata

sh ${scripts_dir}/format_results.sh