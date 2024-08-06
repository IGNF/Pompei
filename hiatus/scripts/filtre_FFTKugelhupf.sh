repertoire_scripts=$1 

ls *.tif > liste_cliches.txt

for i in `cat liste_cliches.txt ` ; do 

${repertoire_scripts}/filtre_FFTKugelHupf.bin ${i} filtre_FFTKugelHupf_${i}

done