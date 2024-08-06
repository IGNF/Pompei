repertoire_scripts=$1


#Saisie des repères de fond de chambre sur une image
echo "Saisie des repères de fonds de chambre"
mm3d SaisieAppuisInit IGNF_PVA_1-0__1979-10-10__C0145-0501_1979_F1-23-6_0334.tif NONE id_reperes.txt MeasuresIm-IGNF_PVA_1-0__1979-10-10__C0145-0501_1979_F1-23-6_0334.tif.xml Gama=2 >> logfile

#Saisie d'un masque indiquant où les repères de fond de chambre peuvent se trouver
echo "Saisie du masque où les repères du fond de chambre se trouvent"
mm3d SaisieMasq IGNF_PVA_1-0__1979-10-10__C0145-0501_1979_F1-23-6_0334.tif Gama=2 >> logfile

#Recherche des repères de fond de chambre
echo "FFTKugelhupf"
mm3d FFTKugelhupf IGNF.*tif MeasuresIm-IGNF_PVA_1-0__1979-10-10__C0145-0501_1979_F1-23-6_0334.tif-S2D.xml Masq=Masq | tee rapports/rapport_FFTKugelhupf.txt >> logfile 

echo "Analyse du rapport FFTKugelhupf"
python ${repertoire_scripts}/analyse_FFTKugelhupf.py --input_rapport rapports/rapport_FFTKugelhupf.txt

#Suppression de fichiers de masques sinon ils sont traités comme faisant partie des images
rm IGNF_PVA_1-0__1979-10-10__C0145-0501_1979_F1-23-6_0334_Masq.tif
rm IGNF_PVA_1-0__1979-10-10__C0145-0501_1979_F1-23-6_0334_Masq.xml
rm MeasuresIm-IGNF_PVA_1-0__1979-10-10__C0145-0501_1979_F1-23-6_0334.tif-S2D.xml
rm MeasuresIm-IGNF_PVA_1-0__1979-10-10__C0145-0501_1979_F1-23-6_0334.tif-S3D.xml
rm Ori-InterneScan/MeasuresIm-IGNF_PVA_1-0__1979-10-10__C0145-0501_1979_F1-23-6_0334_Masq.tif.xml

#Recherche des positions moyennes des repères de fond de chambre
echo "Recherche des positions moyennes des repères de fonds de chambre"
python ${repertoire_scripts}/reperemoyen_resoscan.py --input_micmac_folder=./ --input_resolutionscan=0.021166666666666667 --input_idreperesfile=id_reperes.txt >> logfile

#Rééchantillonnage des clichés
echo "Rééchantillonnage des clichés"
mm3d ReSampFid IGNF.*tif 0.021166666666666667 | tee rapports/rapport_ReSampFid.txt >> logfile

#Analyse du rapport de ReSampFid
python ${repertoire_scripts}/analyse_ReSampFid.py --input_rapport rapports/rapport_ReSampFid.txt

#Mise à jour du fichier de calibration
python ${repertoire_scripts}/maj_calibNum.py --input_micmac_folder=./ >> logfile