

echo "Conversion des images jp2 en tif"

find . -maxdepth 1 -name "*jp2" -exec basename {} .jp2 ';' | parallel -I% --max-args 1 gdal_translate %.jp2 %.tif

mkdir jp2
mv *.jp2 jp2

