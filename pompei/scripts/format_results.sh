#Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/
#
#File main authors:
#- Célestin Huet
#- Arnaud Le Bris
#This file is part of Pompei: https://github.com/IGNF/Pompei
#
#Pompei is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#Pompei is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#You should have received a copy of the GNU General Public License along with Pompei. If not, see <https://www.gnu.org/licenses/>.

mkdir -p resultat/tiff/Ortho
mkdir -p resultat/tiff/MNS
mkdir -p resultat/tiff/MNS_difference
mkdir -p resultat/COG/Ortho
mkdir -p resultat/COG/MNS
mkdir -p resultat/COG/MNS_difference
mkdir -p resultat/carte_correlation

EPSG=`cat metadata/EPSG.txt`

cd Ortho-MEC-Malt-Final-Corr
ls Orthophotomosaic_Tile*.tif > liste_tile.txt
cd ..
for f in `cat Ortho-MEC-Malt-Final-Corr/liste_tile.txt`; do 
    gdal_translate "Ortho-MEC-Malt-Final-Corr/$f" "resultat/tiff/Ortho/${f%.*}.tif" -a_srs EPSG:${EPSG}; 
done
gdalbuildvrt resultat/tiff/Ortho/Ortho.vrt resultat/tiff/Ortho/*.tif

cd MEC-Malt-Final
ls MNS_Final*.tif > liste_tile.txt
cd ..
for f in `cat MEC-Malt-Final/liste_tile.txt`; do 
    gdal_translate "MEC-Malt-Final/$f" "resultat/tiff/MNS/${f%.*}.tif" -a_srs EPSG:${EPSG}; 
done
gdalbuildvrt resultat/tiff/MNS/MNS.vrt resultat/tiff/MNS/*.tif

mv resultat/tiff/MNS/*difference.tif resultat/tiff/MNS_difference/

cd resultat/tiff/Ortho/
ls *.tif > liste_images.txt
cd ../..
for f in `cat tiff/Ortho/liste_images.txt`; do 
    gdal_translate "tiff/Ortho/$f" "COG/Ortho/${f%.*}.tif" -of COG -co COMPRESS=LZW ; 
done
gdalbuildvrt COG/Ortho/ortho.vrt COG/Ortho/*.tif

cd tiff/MNS/
ls *.tif > liste_images.txt
cd ../..
for f in `cat tiff/MNS/liste_images.txt`; do 
    gdal_translate "tiff/MNS/$f" "COG/MNS/${f%.*}.tif" -of COG -co COMPRESS=LZW ; 
done
gdalbuildvrt COG/MNS/MNS.vrt COG/MNS/*.tif

cd tiff/MNS_difference/
ls *.tif > liste_images.txt
cd ../..
for f in `cat tiff/MNS_difference/liste_images.txt`; do 
    gdal_translate "tiff/MNS_difference/$f" "COG/MNS_difference/${f%.*}.tif" -of COG -co COMPRESS=LZW ; 
done
gdalbuildvrt COG/MNS_difference/MNS_difference.vrt COG/MNS_difference/*.tif

cd ..
cp MEC-Malt-Final/correlation*tif resultat/carte_correlation/
cp MEC-Malt-Final/indicateur*tif resultat/carte_correlation/