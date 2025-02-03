set -e

scripts_dir=$1

# Ce script permet de rechercher des points d'appuis sur les chantiers pour lesquels la BD Ortho et le MNS n'est pas disponible. 
# La recherche de points d'appuis se fait alors avec le MNS du SRTM

cd metadata
mkdir -p mns
mkdir -p mns_temp
cd ..
mkdir -p MEC_SRTM

#On télécharge le SRTM correspondant au terrain
python ${scripts_dir}/download_SRTM.py --metadata metadata --output metadata/mns_temp/mns.tif

#On reprojette le SRTM dans le bon EPSG
EPSG=`cat metadata/EPSG.txt`
gdalwarp -t_srs EPSG:${EPSG}   -overwrite metadata/mns_temp/mns.tif metadata/mns/mns.tif

#On convertit le SRTM découpé en Byte
gdal_translate -ot Byte -scale metadata/mns/mns.tif metadata/mns_temp/decoupe_byte.tif

#On ré-échantillonne le SRTM à 15 mètres
#python resample.py --input metadata/SRTM/N12E018.SRTMGL1.hgt/decoupe_byte.tif --output MEC_SRTM/DSM_SRTM.tif --res 2


# On applique  une égalisation sur le MNS calculé
mm3d TestLib DSM_Equalization MEC-Malt-Abs-Ratafia DSMFile=MMLastNuage.xml OutImg=DSM_histo-gray.tif

# On rééchantillonne le DSM_histo et le SRTM à 15 mètres
python ${scripts_dir}/resample.py --input_SRTM metadata/mns_temp/decoupe_byte.tif --output_SRTM MEC_SRTM/DSM_SRTM.tif --res 2 --input_histo MEC-Malt-Abs-Ratafia/DSM_histo-gray.tif --output_histo MEC-Malt-Abs-Ratafia/DSM_histo-gray.tif 

cp MEC_SRTM/DSM_SRTM.tif MEC_SRTM/DSM_SRTM-gray.tif_sfs.tif
cp MEC-Malt-Abs-Ratafia/DSM_histo-gray.tif MEC-Malt-Abs-Ratafia/DSM_histo-gray.tif_sfs.tif

# On crée les paires
mm3d TestLib GetPatchPair BruteForce MEC-Malt-Abs-Ratafia/DSM_histo-gray.tif_sfs.tif MEC_SRTM/DSM_SRTM-gray.tif_sfs.tif  OutDir=./Tmp_Patches-CoReg Rotate=0 PatchLSz=[640,480] PatchRSz=[640,480]

# On recherche les points de liaisons sur les paires
mm3d TestLib SuperGlue SuperGlueInput.txt  InDir=./Tmp_Patches-CoReg/ OutDir=./Tmp_Patches-CoReg/ SpGOutSH=-SuperGlue Viz=1

#On regroupe tous les points de liaisons trouvés
mm3d TestLib MergeTiePt ./Tmp_Patches-CoReg/  HomoXml=SubPatch.xml MergeInSH=-SuperGlue MergeOutSH=-SubPatch PatchSz=[640,480]

#On applique un Ransac pour conserver les points de liaisons les plus cohérents
mm3d TestLib RANSAC R2D MEC_SRTM.tif MEC-Malt-Abs-Ratafia.tif Dir=./Tmp_Patches-CoReg/  2DRANInSH=-SubPatch 2DRANOutSH=-SubPatch-2DRANSAC

#On visualise les points de liaisons


mkdir TraitementAPP
python ${scripts_dir}/get_Appuis_SRTM.py --input_points Tmp_Patches-CoReg/Homol-SubPatch-2DRANSAC/PastisMEC_SRTM.tif/MEC-Malt-Abs-Ratafia.tif.txt --output_points TraitementAPP/resultpi --input_image metadata/mns_temp/decoupe_byte.tif

#mm3d SEL Tmp_Patches-CoReg/ MEC_SRTM.tif MEC-Malt-Abs-Ratafia.tif KH=NT SzW=[600,600] SH=-SubPatch-2DRANSAC

#La suite est la même que pour les autres algorithmes
cd TraitementAPP
#scripts_dir=../${scripts_dir}
mv resultpi resultpt

#Sur les petits chantiers, il n'y a qu'une seule dalle qui s'appelle Orthophotomosaic.tif
if test -f ../Ortho-MEC-Malt-Abs-Ratafia/Orthophotomosaic_Tile_0_0.tif; then
    ${scripts_dir}/POMPEI.LINUX Reproj resultpt bidon bidon Orthophotomosaic_Tile_0_0.ori Orthophotomosaic_Tile_0_0.ori resultpi >> logfile
    ${scripts_dir}/RANSAC resultpi resultpif --taille_case 5000 > /dev/null >> logfile
    #On reprojette en terrain
    ${scripts_dir}/POMPEI.LINUX ReprojTerrain resultpif Orthophotomosaic_Tile_0_0.ori Orthophotomosaic_Tile_0_0.ori resultpifreproj >> logfile
else
    ${scripts_dir}/POMPEI.LINUX Reproj resultpt bidon bidon Orthophotomosaic_Tile.ori Orthophotomosaic_Tile.ori resultpi >> logfile
    ${scripts_dir}/RANSAC resultpi resultpif --taille_case 5000 > /dev/null >> logfile
    #On reprojette en terrain
    ${scripts_dir}/POMPEI.LINUX ReprojTerrain resultpif Orthophotomosaic_Tile.ori Orthophotomosaic_Tile.ori resultpifreproj >> logfile
fi