scripts_dir=$1 

ls *.tif > liste_cliches.txt

for i in `cat liste_cliches.txt ` ; do 

${scripts_dir}/filtre_FFTKugelHupf.bin ${i} filtre_FFTKugelHupf_${i}

done