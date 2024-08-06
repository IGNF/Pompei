repertoire_scripts=$1
forcer_verticale=$2




#Pré-calcule de l'orientation relative
echo "Martini"
mm3d Martini "OIS-Reech_.*tif" OriCalib=CalibNum >> logfile

#Calcule de l'orientation relative
echo "Tapas"
mm3d Tapas FraserBasic "OIS-Reech_.*tif" InOri=MartiniCalibNum InCal=CalibNum Out=Rel @ExitOnWarn | tee rapports/rapport_Tapas.txt >> logfile

#mm3d Tapas FraserBasic "OIS-Reech_.*tif" InCal=CalibNum Out=Rel | tee rapports/rapport_Tapas.txt >> logfile

#Analyse de rapport_Tapas 
python ${repertoire_scripts}/analyse_Tapas.py --input_rapport rapports/rapport_Tapas.txt --repertoire_scripts ${repertoire_scripts}


#Crée un nuage de points
echo "AperiCloud"
mm3d AperiCloud "OIS-Reech_.*tif" Rel >> logfile


#Approche les sommets de prise de vue au plus près des coordonnées contenues dans le fichier SommetsNav.csv
if test ${forcer_verticale} -eq 1;
then
    #Dans le cas où l'acquisition est faite en une seule bande, il est possible que l'orientation autour de l'axe de vol ne soit pas satisfaisante.
    #Avec l'option Forcevert, un point factice est ajouté à la verticela du chantier afin que tous les sommets de prise de vue ne soient pas alignés
    echo "CenterBascule"
    mm3d CenterBascule "OIS-Reech_.*tif" Rel Nav Abs L1=true ForceVert=1000000 | tee rapports/rapport_CenterBascule.txt >> logfile
else
    echo "CenterBascule"
    mm3d CenterBascule "OIS-Reech_.*tif" Rel Nav Abs L1=true | tee rapports/rapport_CenterBascule.txt >> logfile
fi

#Analyse de rapport_CenterBascule
python ${repertoire_scripts}/analyse_CenterBascule.py --input_rapport rapports/rapport_CenterBascule.txt


#Produit une première orthophoto qui donne un aperçu de cette première mise en place
echo "Tarama"
mm3d Tarama "OIS-Reech_.*tif" Abs Out=TA-Abs >> logfile