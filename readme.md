# Hiatus


Hiatus est une chaîne de traitement presque entièrement automatisée pour reconstruire des orthophotos à partir des images argentiques acquises tout au long du XXème siècle et qui ont été scannées dernièrement. Jusqu’à présent, une première couverture de la France entière a été produite
à partir d’images de 1950-1960, sous le nom de BD Ortho historique. Cependant, cette production a nécessité de nombreuses opérations manuelles, principalement pour saisir les points d’appuis. Hiatus permet de produire ces orthophotos avec un nombre d’opérations manuelles particulièrement réduit et pour des résultats tout aussi bons. L’enjeu est de taille car l’IGN possède plus de 3,5 millions d’images argentiques scannées, acquises au cours de plus de 26000 chantiers, que ce soit en France métropolitaine, dans les DOM-TOM ou dans les anciennes colonies.

Hiatus permet notamment de répondre à plusieurs défis techniques : recherche de repères de fond de chambre, construction d’orthophotos, recherche de points d’appuis et égalisation radiométrique. Hiatus traite indifféremment les images en couleur (RVB ou IRC) ou bien les images à un seul canal
(panchromatique ou infrarouge).
Hiatus utilise le logiciel de photogrammétrie MicMac, ainsi que des scripts Python, bash et C++. Il est destiné à tourner uniquement sur des machines Linux.


# Documentation

La documentation détaillée de Hiatus se trouve dans [hiatus.pdf](documentation/Hiatus.pdf)



## Installation


### Avec Docker sur Linux

Construction de l'image Docker :

```
docker build -t hiatus --build-arg HTTP_PROXY=$HTTP_PROXY --build-arg HTTPS_PROXY=$HTTPS_PROXY --build-arg USER_ID=$(id --user) .
```


Pour lancer le conteneur Docker (renseigner le répertoire de montage dans la machine hôte) :
```
docker run --name hiatus -it -e DISPLAY -v [point de montage sur la machine hôte]:/home/hiatus/hiatus/hiatus/chantiers -v /tmp/.X11-unix:/tmp/.X11-unix --user="$(id --user)" hiatus /bin/bash
```

Ou bien (interne à l'IGN) : pour lancer le conteneur Docker après avoir monté store-ref en local (renseigner le répertoire de montage de store-ref) :
```
docker run --name hiatus -it -e DISPLAY --mount type=bind,src=[chemin vers store-ref],dst=/media/store-ref,readonly -v [point de montage sur la machine hôte]:/home/hiatus/hiatus/hiatus/chantiers -v /tmp/.X11-unix:/tmp/.X11-unix --user="$(id --user)" hiatus /bin/bash
```

Activer l'environnement conda :
```
mamba activate hiatus
```

### Avec Docker sur Mac

Construction de l'image Docker :

```
docker build -t hiatus --build-arg HTTP_PROXY=$HTTP_PROXY --build-arg HTTPS_PROXY=$HTTPS_PROXY --build-arg USER_ID=$(id -u) .
```

Lancer le serveur X11 (installer XQuartz si nécessaire):
```
open -a XQuartz
```

Autorisez les connexions locales:
```
xhost +localhost
```

Lancer le conteneur Docker (renseigner le répertoire de montage dans la machine hôte):
```
docker run --name hiatus -it --env="DISPLAY=host.docker.internal:0" -v [point de montage sur la machine hôte]:/home/hiatus/hiatus/hiatus/chantiers -v /tmp/.X11-unix:/tmp/.X11-unix --user="$(id -u)" hiatus /bin/bash
```

Ou bien (interne à l'IGN) : pour lancer le conteneur Docker après avoir monté store-ref en local (renseigner le répertoire de montage de store-ref) :
```
docker run --name hiatus -it --env="DISPLAY=host.docker.internal:0" --mount type=bind,src=[chemin vers store-ref],dst=/media/store-ref,readonly -v [point de montage sur la machine hôte]:/home/hiatus/hiatus/hiatus/chantiers -v /tmp/.X11-unix:/tmp/.X11-unix --user="$(id -u)" hiatus /bin/bash
```

Activer l'environnement conda :
```
mamba activate hiatus
```


### Sans Docker

* Installer Micmac en suivant les consignes d'installation sur la page [GitHub](https://github.com/micmacIGN/micmac).

* Installer l'environnement conda :
```
mamba env create -f environment.yml
```

* Activer l'environnement conda :
```
mamba activate hiatus
```


## Utilisation


### Récupération des chantiers disponibles 
Pour récupérer les chantiers disponibles sur la Géoplateforme :
```
python scripts/get_data.py --outdir footprints
```

Un fichier [outdir]/footprints.geojson est créé. Il contient :
* les footprints au sol 
* la date de la mission (ne tenir compte que de l'année et pas du jour ni du mois)
* la résolution en mètres. Il s'agit d'une approximation calculée à partir de la hauteur de vol et de la focale définie dans les métadonnées de l'IGN
* la couleur. C : en RVB, P : panchromatique, IRC : infrarouge fausse couleur, IR : infrarouge
* le support. Nu : numérique, Ag : argentique
* prise de vue oblique. Hiatus ne fonctionne pas avec les acquisitions en prise de vue oblique car il n'y a pas assez de recouvrement entre les images et les algorithmes de recherche de points d'appuis ne sont pas faits pour comparer images obliques et orthophoto acquises à la verticale. 
* la taille de la focale en mm. Il s'agit d'une approximation issue des métadonnées, mais qui sert de valeur initiale lorsque Hiatus déterminera la vraie valeur de la focale.



### Récupération des données pour un chantier spécifique

Pour récupérer les images et le TA d'un chantier :
```
python scripts/get_images.py --footprints_file fichier_footprints --id id_chantier --epsg epsg --outdir outdir
```
Avec :
* fichier_footprints : chemin vers le fichier des chantiers disponibles, celui qui a été téléchargé avec le get_data.py
* id_chantier : l'identifiant du chantier souhaité : champ id du fichier footprints, sans le "dataset."
* epsg : epsg du chantier : il n'y a pas moyen de récupérer automatiquement l'EPSG du chantier, donc il faut le rentrer à la main ici
* outdir : répertoire où mettre les données pour le chantier


### Traitement d'un chantier

```
cd hiatus
sh visualize_flight_plan.sh TA

sh hiatus.sh TA nb_fiducial_marks targets Kugelhupf_image_filtree remove_artefacts force_vertical ortho algo filter_GCP create_ortho_mns create_ortho_mnt
```
  


### Variante

Le script hiatus.sh ne fonctionne pas si les images ne se recouvrent pas suffisamment. En effet, il est alors impossible de reconstruire une orthophoto vraie et de la comparer avec l'ortho de référence. La variante se veut être plus robuste à ce cas de figure et plus rapide, mais moins précise. De plus, elle ne permet que la création d'une ortho sur MNT (donc pas de production de MNS). Il n'est pas possible de filtrer les points d'appuis. La variante ne fonctionne pas non plus pour le moment sur des images en couleur. Le principe est le suivant :
* Même processus de prétraitement des images et de recherche de repères de fond de chambre
* Recherche de points de liaisons
* Récupération de l'ortho de référence
* Pour chaque image, recherche de points d'appuis sur l'ortho de référence 
* Aérotriangulation à partir des points de liaisons et des points d'appuis. Si une image est isolée du reste du chantier, elle devrait cependant être géoréférencée si elle a suffisamment de points d'appuis
* Construction d'une ortho sur le MNT actuel et égalisation radiométrique

```
cd hiatus
sh visualize_flight_plan.sh TA

sh hiatus_rapide.sh TA nb_fiducial_marks targets Kugelhupf_image_filtree remove_artefacts ortho nb_cpus
```


# Contributeurs

Contributeurs IGN : Célestin Huet, Arnaud Le Bris


# Citations

* Aubry et al, Painting-to-3D Model Alignment Via Discriminative Visual Elements, 2014
* Giordano et al, Toward automatic georeferencing of archival aerial photogrammetric surveys, 2018
* Zhang et al, Feature matching for multi-epoch historical aerial images, 2021


# How to Cite

Please cite Hiatus and IGN if you use this software in your research or project.
Proper citations help others find and reference this work and support its continued development.

To cite this software, please use the following reference:

```bibtex
@software{Hiatus,
  author = {IGN},
  title = {Hiatus},
  version = {1},
  year = {2024},
  url = {https://github.com/IGNF/Hiatus}
}
```