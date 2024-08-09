#Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/
#
#File main authors:
#- Célestin Huet
#This file is part of Hiatus: https://github.com/IGNF/Hiatus
#
#Hiatus is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#Hiatus is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#You should have received a copy of the GNU General Public License along with Hiatus. If not, see <https://www.gnu.org/licenses/>.

scripts_dir=$1
ortho=$2
TA=$3


python ${scripts_dir}/build_bbox.py --TA ${TA} --metadata metadata

#Sur les petits chantiers, il n'y a qu'une seule dalle qui s'appelle Orthophotomosaic.tif. On la renomme Orthophotomosaic_Tile_0_0.tif pour ne pas faire de cas particuliers dans la suite
if test ! -f Ortho-MEC-Malt-Abs-Ratafia/Orthophotomosaic_Tile_0_0.tif; then
    cp  Ortho-MEC-Malt-Abs-Ratafia/Orthophotomosaic.tif Ortho-MEC-Malt-Abs-Ratafia/Orthophotomosaic_Tile_0_0.tif >/dev/null
    cp  Ortho-MEC-Malt-Abs-Ratafia/Orthophotomosaic.tfw Ortho-MEC-Malt-Abs-Ratafia/Orthophotomosaic_Tile_0_0.tfw >/dev/null
fi

EPSG=`cat metadata/EPSG.txt`
echo "Téléchargement de la BD Ortho"

if test ${ortho} = "dalles"; then
    #On télécharge le SRTM correspondant à la zone et on découpe les images en tuiles de 2000 pixels de côté
    mkdir metadata/mns_temp
    mkdir metadata/mns
    python ${scripts_dir}/download_SRTM.py --MNS_Histo MEC-Malt-Abs-Ratafia/MNS_Final_Num8_DeZoom2_STD-MALT.tif --metadata metadata --output metadata/mns_temp/MNS_temp.tif
    gdalwarp -t_srs EPSG:${EPSG}   -overwrite metadata/mns_temp/MNS_temp.tif metadata/mns_temp/MNS.tif
    rm metadata/mns_temp/MNS_temp.tif
    python ${scripts_dir}/cut_pleiade_images.py --input "metadata/ortho_temp" --output "metadata/ortho" --metadata "metadata"
elif test ${ortho} = "histo"; then
    #On télécharge les chantiers les plus anciens. Dans ce cas, on télécharge les dalles à la résolution du chantier
    python ${scripts_dir}/download_ortho_MNS_geoserver.py --metadata "metadata"
elif test ${ortho} = "storeref"; then
    #On télécharge la BD Ortho et le MNS via le store-ref. Les dalles sont à une résolution de 50cm pour la BD Ortho et de 20cm pour le MNS
    python ${scripts_dir}/download_ortho_MNS_store-ref.py --metadata "metadata" --scripts ${scripts_dir}
elif test ${ortho} = "wms"; then
    #On télécharge la BD Ortho et le MNS via un flux WMS. Les dalles sont rééchantillonnées à la résolution de l'ortho produite par le premier Malt/Tawny
    python ${scripts_dir}/download_ortho_MNS_wms.py --metadata "metadata"
fi

#On applique un gdal_translate sur les dalles de MNS et de BD Ortho afin que les dalles respectent bien les spécifications tif. 
#Sans cela, il arrive que les scripts de recherche de points d'appuis ne fonctionnent pas. 

cd metadata
find mns_temp -name "*.tif" -exec basename {} ';' | parallel -I% --max-args 1 gdal_translate mns_temp/% mns/%

#On construit un vrt qui sert uniquement à la visualisation afin de comparer plus facilement le résultat final à l'ortho de référence
cd mns
gdalbuildvrt MNS.vrt MNS*tif
cd ..
rm -rf mns_temp

if test ${ortho} != "dalles"; then
    find ortho_temp -name "*.jp2" -exec basename {} .jp2 ';' | parallel -I% --max-args 1 gdal_translate ortho_temp/%.jp2 ortho/%.tif

    find ortho_temp -name "*.tif" -exec basename {} ';' | parallel -I% --max-args 1 gdal_translate ortho_temp/% ortho/%
fi

rm -rf ortho_temp


cd ortho
gdalbuildvrt ORTHO.vrt ORTHO*tif
cd ../..