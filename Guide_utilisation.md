# Guide d'utilisation Pompei

Les procédures d'installation de Pompéi et Micmac sont détaillées dans la [documentation Pompéi](https://github.com/IGNF/Pompei/blob/ensg2/readme.md#Installation)

Une fois que Pompéi est correctement installé, plusieurs commandes doivent être exécutées avant de concrétement lancer Pompéi.

Le guide d'utilsation est disponible dans la documentation de Pompéi.

Les commandes sont rappelées ci-dessous avec quelques détails supplémentaires:

### Récupération des chantiers disponibles 
Pour récupérer les chantiers disponibles sur [Remonter le temps](https://remonterletemps.ign.fr/) :
```
python scripts/get_data.py --outdir footprints
```

outdir désigne le chemin du dossier où sera récupéré footprints. 
Il est fortement conseillé de créer un chemin sous le format "chantiers/test/testN/footprints.geojson" pour qu'il n'y ai pas de problèmes par la suite

Un fichier [outdir]/footprints.geojson est créé. Il contient :
* les emprises (footprints) au sol 
* la date de la mission (ne tenir compte que de l'année et pas du jour ni du mois)
* la résolution en mètres. Il s'agit d'une approximation calculée à partir de la hauteur de vol et de la focale définie dans les métadonnées de l'IGN
* la couleur. C : en RVB, P : panchromatique, IRC : infrarouge fausse couleur, IR : infrarouge
* le support. Nu : numérique, Ag : argentique
* prise de vue oblique. Pompei ne fonctionne pas avec les acquisitions en prise de vue oblique car il n'y a pas assez de recouvrement entre les images et les algorithmes de recherche de points d'appuis ne sont pas faits pour comparer images obliques et orthophoto acquises à la verticale. 
* la taille de la focale en mm. Il s'agit d'une approximation issue des métadonnées, mais qui sert de valeur initiale lorsque Pompei déterminera la vraie valeur de la focale.

Note : seul le répertoire chantiers dispose d'un volume Docker. Donc si vous avez utilisé Docker pour l'installation, il faut que footprints soit de la forme chantiers/[...] pour que vous puissiez le visualiser ensuite dans Qgis.



### Récupération du plan de vol

Pour récupérer les emprises au sol d'un chantier :
```
python scripts/get_flight_plan.py --footprints_file fichier_emprises --id id_chantier --outdir outdir
```

id_chantier 
Un fichier [outdir]/images.geojson est créé. Vous pouvez l'ouvrir dans Qgis. Ce fichier contient les emprises au sol de tous les clichés du chantier. Sélectionnez les clichés qui vous intéressent et sauvegardez-les dans un nouveau fichier shapefile.

Paramètres :
* fichier_emprises : chemin vers le fichier des chantiers disponibles, celui qui a été téléchargé avec le get_data.py
* id_chantier : l'identifiant du chantier souhaité : champ id du fichier footprints, sans le "dataset" (récupérable via QGIS)
* outdir : répertoire où mettre les données pour le chantier

En ouvrant images.geojson (dans QGIS), il y a souvent beaucoup d'images, il est fortement conseillé de sélectionner certaines images avec un bon recouvrement,
puis d'enregistrer la couche QGIS et la placer dans le repertoire où se situe images.geojson.


### Récupération des données pour un chantier spécifique

Pour récupérer les images et le TA d'un chantier :
```
python scripts/get_images.py --selection selection --id id_chantier --epsg epsg --outdir outdir
```
Avec :
* selection : chemin vers le fichier contenant les images sélectionnées
* id_chantier : l'identifiant du chantier souhaité : champ id du fichier footprints, sans le "dataset."
* epsg : epsg du chantier : il n'y a pas moyen de récupérer automatiquement l'EPSG du chantier, donc il faut le rentrer à la main ici
* outdir : répertoire où mettre les données pour le chantier


### Traitement d'un chantier

```
cd pompei
sh visualize_flight_plan.sh TA 0

sh pompei.sh TA nb_fiducial_marks targets Kugelhupf_image_filtree remove_artefacts ortho algo filter_GCP create_ortho_mns create_ortho_mnt cpu
```
Il faut bien indiquer le chemin vers TA (donc le même que pour images.geojson)

La signification des paramètres est détaillée dans [la documentation](documentation/Pompei.pdf).

# Guide d'utilisation du script select_points.py

La partie de Pompéi non automatisée est celle liée aux repères de fonds de chambre, prise en charges par select_points.py et SaisieMask de MicMac.

Ainsi, lorsque vous lancerez Pompei, il y a plusieurs actions à effectuées: 
1. une interface de saisie s'ouvre afin de saisir le nombre de repères que vous avez spécifié dans l'appel de Pompéi

    Il y a 8 boutons de zoom, aux coins et aux centres des arètes des images. 
    Il n'y a pas forcément un repère à cliquer dans chaque zoom.
    Un clic gauche permet de sélectionner un repère, un clic droit permet de le désélectionner. 
    Si le repère n'apparait que partiellement dans la fenêtre, vous pouvez soit utiliser les curseurs en bas et à droite de la fenêtre soit passer en grand écran.
    Une fois que tous les repères ont été saisis, il suffit de fermer la fenètre avec la croix en haut à droite.

2. Ensuite, il faudra saisir des masques de recherche. 
    Pour zoomer => molette vers le bas (inversement pour dézoomer)
    Pour dessiner un masque => ctrl puis clic gauche pour les côté du polygone, et maj+clic gauche pour fermer le polygone.
    Pour fermer => clic droit, puis glissez la souris sur exc (en bas à droite).

3. Une corrélation va se lancer. Si elle échoue, il faudra saisir les repères sur toutes les autres images problématiques.
    Le premier outil select_points s'ouvrira de nouveau avec cette fois le nombre de zoom correspond au nombre de points à saisir.
    Tous les zooms sont donc utiles ici!

4. Il ya ensuite un rééchantillonage des images.
    S'il y a des résidus trop importants, il faudra saisir un masque via le deuxième outil présenté SaisieMask.

Après, c'est fini, tout est automatisé. 


