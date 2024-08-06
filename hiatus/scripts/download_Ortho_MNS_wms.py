import os
import argparse
import requests
from tools import load_bbox, getEPSG


def download_data(bbox, type, metadata, EPSG):

    if type=="ORTHO":
        layer='ORTHOIMAGERY.ORTHOPHOTOS.BDORTHO'
        path_tuile = os.path.join(metadata, "ortho_temp")
        path_meta = os.path.join(metadata, "ortho")
        resolution = 0.5

    if type=="MNS":
        layer='ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES.MNS'
        path_tuile = os.path.join(metadata, "mns_temp")
        path_meta = os.path.join(metadata, "mns")
        resolution = 0.2

    if type=="MNT":
        layer="ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES"
        path_tuile = os.path.join(metadata, "mnt_temp")
        path_meta = os.path.join(metadata, "mnt")
        resolution = 0.5
        
    if not os.path.exists(path_tuile):
        os.makedirs(path_tuile)

    if not os.path.exists(path_meta):
        os.makedirs(path_meta)
    
    format='image/geotiff'

    #Le service WMS de l'IGN ne fournit pas d'images avec plus de 10000 pixels de côté, donc il est nécessaire de diviser la surface en dalles de 5 km au maximum (pour une ortho à 50 cm)
    emin, nmin, emax, nmax = bbox

    #Les positions des sommets de prises de vue sont approximatives, donc il faut ajouter une marge. On ajoute une marge de 500 mètres
    emin -= 500
    nmin -= 500
    emax += 500
    nmax += 500

    liste_e = [e for e in range(int(emin), int(emax), 1000)]
    liste_e.append(emax)

    liste_n = [n for n in range(int(nmin), int(nmax), 1000)]
    liste_n.append(nmax)

    for i in range(len(liste_e) - 1):
        e_min_dalle = liste_e[i]
        e_max_dalle = liste_e[i+1]
        for j in range(len(liste_n) - 1):
            n_min_dalle = liste_n[j]
            n_max_dalle = liste_n[j+1]

            bbox_string = "{},{},{},{}".format(e_min_dalle, n_min_dalle, e_max_dalle, n_max_dalle).strip()
            width=str(int((e_max_dalle - e_min_dalle)/resolution))
            height=str(int((n_max_dalle - n_min_dalle)/resolution))
            url = "https://data.geopf.fr/wms-r?LAYERS="+layer+"&FORMAT="+format+"&SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&STYLES=&CRS=EPSG:"+str(EPSG)+'&BBOX='+bbox_string+'&WIDTH='+width+'&HEIGHT='+height
            r = requests.get(url)
            if r.status_code==200:
                try:
                    with open(os.path.join(path_tuile, '{}_dalle_{}_{}.tif'.format(type, i, j)), 'wb') as out:
                        out.write(bytes(r.content))
                except:
                    print(url)
                    print('File failed to download.')
            else:
                print(url)
                print('File failed to download.')

            if type=="ORTHO":
                with open(os.path.join(path_meta, '{}_dalle_{}_{}.tfw'.format(type, i, j)), 'w') as out:
                    out.write("0.50\n")
                    out.write("0.00\n")
                    out.write("0.00\n")
                    out.write("-0.50\n")
                    out.write("{}\n".format(e_min_dalle+0.25))
                    out.write("{}\n".format(n_max_dalle-0.25))
            
            elif type=="MNS":
                with open(os.path.join(path_meta, '{}_dalle_{}_{}.ori'.format(type, i, j)), 'w') as out:
                    out.write("CARTO\n")
                    out.write("{} {}\n".format(e_min_dalle*1000, n_max_dalle*1000))
                    out.write("0\n")
                    out.write("{} {}\n".format(width, height))
                    out.write("200.000000 200.000000\n")


                with open(os.path.join(path_meta, '{}_dalle_{}_{}.hdr'.format(type, i, j)), 'w') as out:
                    out.write(" // Convention de georeferencement : angle noeud (Geoview)\n")
                    out.write("!+\n!+--------------------------\n!+ HDR/A : Image Information\n!+--------------------------\n!+\n")
                    out.write("ULXMAP  {}\n".format(e_min_dalle))
                    out.write("ULYMAP  {}\n".format(n_max_dalle))
                    out.write("XDIM    0.20\n")
                    out.write("YDIM    0.20\n")
                    out.write("NROWS  {}\n".format(height))
                    out.write("NCOLS  {}\n".format(width))
                    out.write("NBANDS   1\n")
                    out.write("!+\n!+--------------------------\n!+ HDR/B : Frame Corner Support\n!+--------------------------\n!+\n")
                    out.write("!+\n!+--------------------------\n!+ HDR/C : File Encoding\n!+--------------------------\n!+\n")
                    out.write("!+\n!+--------------------------\n!+ HDR/E : More Parameters\n!+--------------------------\n!+\n")
                    out.write("COSINUS 1.00\n")
                    out.write("SINUS 0.00\n")
                    out.write("SIGNE	1\n")
                    out.write("BAND_NAMES	Z\n")
                    out.write("PROJECTION    LAMBERT93\n")


if __name__=="__main__":

    parser = argparse.ArgumentParser(description="Téléchargement des dalles de la BD Ortho et du MNS du chantier")
    parser.add_argument('--metadata', help='Chemin où enregistrer la BD Ortho et le MNS')
    args = parser.parse_args()

    #Charge l'emprise du chantier
    bbox = load_bbox(args.metadata)

    #On récupère l'EPSG du chantier
    EPSG = getEPSG(args.metadata)

    #Télécharge la BD Ortho sous forme de dalles
    download_data(bbox, "ORTHO", args.metadata, EPSG)

    #Télécharge le MNS sous forme de dalles
    download_data(bbox, "MNS", args.metadata, EPSG)