import os
from PIL import Image
from lxml import etree


#à partir d'une liste d'éléments, renvoie une sous-liste de tous les éléments qui contiennent une liste de pattern  
def filter_list_pattern_in(list_to_filter, list_pattern_in): 
    return [str for str in list_to_filter if
             all(subin in str for subin in list_pattern_in)] 

if __name__ == "__main__":

	input_calib_folder = "Ori-CalibNum"

	list_xml = []
	list_OIS = []	
	#On récupère les fichiers xml dans Ori-CalibNum
	list_xml = filter_list_pattern_in(os.listdir(input_calib_folder), ['.xml'])

	#On récupère les clichés argentiques rééchantillonnés
	list_OIS = filter_list_pattern_in(os.listdir(),['OIS-Reech_', '.tif'])
	
	#On augmente la taille maximale des images acceptées par PIL
	Image.MAX_IMAGE_PIXELS = 1e15

	#taille image des clichés argentiques rééchantillonnés
	im = Image.open(list_OIS[0])
	w, h = im.size
	half_w = int(float(w)/2)
	half_h = int(float(h)/2)
	
	str_width=str(w)
	str_height=str(h)

	
	#lecture fichier Ori-CalibNum
	for xml in list_xml:
		tree = etree.parse(os.path.join(input_calib_folder, xml))
		root = tree.getroot()

		root.find(".//PP").text = "{} {}".format(half_w, half_h)
		root.find(".//SzIm").text = "{} {}".format(w, h)
		root.find(".//CDist").text = "{} {}".format(half_w, half_h)

		AutoCal_Foc_path = os.path.join(input_calib_folder, xml)
		with open(AutoCal_Foc_path, "w") as f:
			f.write("<?xml version=\"1.0\" ?>\n")
			f.write(str(etree.tostring(root, encoding='unicode')))
		


	with open("find_tie_points.sh", "r") as f:
		text = f.readlines()
	
	with open("find_tie_points.sh", "w") as f:
		for line in text:
			if "mm3d Tapioca File CouplesTA.xml" in line:
				if len(list_OIS) >= 4:
					line = "mm3d Tapioca File CouplesTA.xml " + str(max(half_w, half_h)) + " | tee reports/rapport_Tapioca.txt >> logfile \n"
				else:
					line = "mm3d Tapioca All OIS-Reech.*.tif " + str(max(half_w, half_h)) + " | tee reports/rapport_Tapioca.txt >> logfile \n"
			if "mm3d OriConvert OriTxtInFile" in line:
				if len(list_OIS) >= 4:
					line = "mm3d OriConvert OriTxtInFile SommetsNav.csv Nav NameCple=CouplesTA.xml >> logfile \n"
				else:
					line = "mm3d OriConvert OriTxtInFile SommetsNav.csv Nav >> logfile \n"
			f.write(line)
