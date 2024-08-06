import os
import argparse
from lxml import etree




parser = argparse.ArgumentParser(description='Generation des metadonnees d un site HIATUS')


# GENERAL PARAMETER
parser.add_argument('--input_micmac_folder', default='/home/adminlocal/Partage/HIATUS-1/sites/sablesdolonne/data/1982_IPLI13_test6_File/', help='Dossier racine')
args = parser.parse_args()

#à partir d'une liste d'éléments, renvoie une sous-liste de tous les éléments qui contiennent une liste de pattern  
def filter_list_pattern_in(list_to_filter, list_pattern_in): 
    return [str for str in list_to_filter if
             all(subin in str for subin in list_pattern_in)] 

#-----------------------------------------------------
if __name__ == "__main__":

    xml_files = os.listdir("Ori-InterneScan")

    for xml_file in xml_files:
        if "Masq" in xml_file:
            os.remove(os.path.join("Ori-InterneScan", xml_file))
        elif not "MeasuresCamera.xml" in xml_file:
            nom_image = xml_file.replace("MeasuresIm-filtre_FFTKugelHupf_", "")
            nom_image = nom_image.replace(".xml", "")

            tree = etree.parse(os.path.join("Ori-InterneScan", xml_file))
            root = tree.getroot()

            for NameIm in root.find(".//NameIm"):
                NameIm.text = nom_image
            
            with open(os.path.join("Ori-InterneScan", "MeasuresIm-"+nom_image)+".xml", "w") as f:
                f.write("<?xml version=\"1.0\" ?>\n")
                f.write(str(etree.tostring(tree, encoding='unicode')))