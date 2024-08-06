from geoserver.catalog import Catalog
import os
import shutil
from geo.Geoserver import Geoserver
import argparse



parser = argparse.ArgumentParser(description="Script pour uploader des données sur le geoserver")
parser.add_argument('--adresse', help='Adresse du geoserver. Elle doit commencer en http et se finir en /geoserver')
parser.add_argument('--username', help="Nom de l'utilisateur du geoserver")
parser.add_argument('--password', help="Mot de passe du geoserver")
parser.add_argument('--path', help="Chemin vers le répertoire contenant toutes les données à uploader")
parser.add_argument('--workspace', help="Nom du workspace dans le geoserver")
args = parser.parse_args()

"""
Le répertoire indiqué par path doit contenir un dossier par chantier.
Dans chaque dossier de chantier, on doit retrouver un dossier pour chaque produit (Ortho, MNS, différence de MNS)
A l'intérieur de ces dossiers de produit, on doit retrouver les images correspondantes.

Ce script crée un fichier zip pour chaque produit et crée une ImageMosaïque sur Geoserver. Le nom de chaque couche est : [nomChantier]_[nom_produit]
"""


def setTitle(layer_name):
    url = "{0}/rest/workspaces/{1}/coveragestores/{2}/coverages/{2}".format(
        geo.service_url, workspace_name, layer_name
    )

    headers = {"content-type": "text/xml", "Accept" : "application/json"}
    r = None

    data_gs = {}
    data_gs["title"] = layer_name
    data_gs = f"<coverage><title>{layer_name}</title></coverage>"

    r = geo._requests(method="put", url=url, data=data_gs, headers=headers)

    if r.status_code == 201 or r.status_code == 200:

        print(r.content)
    else:
        print("Erreur : ", url, r.status_code, r.content)



cat = Catalog(args.adresse + "/rest/", args.username, args.password)
geo = Geoserver(args.adresse, username=args.username, password=args.password)

path_data = args.path

workspace_name = args.workspace
try:
    workspace = cat.create_workspace(workspace_name, "http://"+workspace_name)
except:
    
    print("Le workspace a déjà été créé")

for chantier in os.listdir(path_data):
    for dataType in os.listdir(os.path.join(path_data, chantier)):
        if not ".zip" in dataType:
            layer_name = "{}_{}".format(chantier, dataType)
            if cat.get_store(layer_name, workspace=workspace_name):
                print("La couche existe déjà : ", chantier, dataType)
            else:
                chemin_zip = os.path.join(path_data, chantier, dataType)
                shutil.make_archive(os.path.join(path_data, chantier, dataType), "zip", chemin_zip)
                
                try:
                    cat.create_imagemosaic(layer_name, os.path.join(path_data, chantier, dataType+".zip"), workspace=workspace_name, coverageName=layer_name)
                    setTitle(layer_name)
                except:
                    print("La couche existe déjà : ", chantier, dataType)


