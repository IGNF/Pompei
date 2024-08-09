"""
Copyright (c) Institut national de l'information géographique et forestière https://www.ign.fr/

File main authors:
- Célestin Huet

This file is part of Hiatus: https://github.com/IGNF/Hiatus

Hiatus is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Hiatus is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Hiatus. If not, see <https://www.gnu.org/licenses/>.
"""

import psycopg2
import json
import argparse


parser = argparse.ArgumentParser(description="Scripts pour interroger la base de données MisPhot")
parser.add_argument('--user', help="Nom de l'utilisateur")
parser.add_argument('--password', help='Mot de passe')
parser.add_argument('--host', help='Machine hôte')
parser.add_argument('--port', help='Port')
parser.add_argument('--database', help='Database')
args = parser.parse_args()


def test_camera(cursor):
    cursor.execute("SELECT c.id_missta, s.name, s.focal_x, s.focal_y, s.focal_z, s.usefull_frame, c.name, EXTRACT(YEAR FROM c.t0) FROM misphot.chantiers as c JOIN misphot.sensors as s ON c.id = s.chantier")
    records = cursor.fetchall()
    for data in records:
        #if data[1] == None:
        #    print("La caméra du chantier {} n'a pas de nom ou chantier {}, {}".format(data[0], data[6], data[7]))
        #    taille = data[5].replace(")", "(").replace(",", "(").split("(")
        #    print("{} {} {} {} {} {} {},{}".format(data[0], data[6], data[1], data[2], data[3], data[4], taille[0].strip(), taille[1]))
        if data[2] == None:
            print("La caméra du chantier {} n'a pas de focal_x {}, {}".format(data[0], data[6], data[7]))
        if data[3] == None:
            print("La caméra du chantier {} n'a pas de focal_y {}, {}".format(data[0], data[6], data[7]))
        if data[4] == None:
            print("La caméra du chantier {} n'a pas de focal_z {}, {}".format(data[0], data[6], data[7]))
        if data[5] == None:
            print("La caméra du chantier {} n'a pas de usefull_frame {}, {}".format(data[0], data[6], data[7]))


def test_position_cliche(cursor):
    cursor.execute("SELECT c.id_missta, cl.image, ST_X(cl.point), ST_Y(cl.point), ST_Z(cl.point), ST_X(cl.quaternion), ST_Y(cl.quaternion), ST_Z(cl.quaternion), ST_AsGeoJSON(cl.footprint), c.name, EXTRACT(YEAR FROM c.t0) FROM misphot.chantiers as c JOIN misphot.cliches as cl ON c.id = cl.chantier")
    
    records = cursor.fetchall()
    min_x = 1e20
    max_x = 0
    min_y = 1e20
    max_y = 0
    min_z = 1e20
    max_z = 0
    
    for data in records:

        if data[1] == None:
            print("L'image {} du chantier {} n'a pas de nom".format(data[1], data[0]))
        if data[2] == None or data[3]==None or data[4]==None:
            print("L'image {} du chantier {} n'a pas de sommets de prise de vue {}, {}".format(data[1], data[0], data[9], data[10]))
        else:
            coord = int(data[2])
            min_x = min(min_x, coord)
            max_x = max(max_x, coord)
            coord = int(data[3])
            min_y = min(min_y, coord)
            max_y = max(max_y, coord)
            coord = int(data[4])
            min_z = min(min_z, coord)
            max_z = max(max_z, coord)

        if data[5] == None or data[6] == None or data[7] == None:
            print("L'image {} du chantier {} n'a pas de quaternion".format(data[1], data[0]))

        #if data[8] == None:
        #    print("L'image {} du chantier {} n'a pas d'footprintau sol {}, {}".format(data[1], data[0], data[9], data[10]))
        else:
            footprint = json.loads(data[8])
            if len(footprint["coordinates"][0]) != 9:
                print("L'image {} du chantier {} n'a pas 8 points pour l'footprintau sol {}, {}".format(data[1], data[0], data[9], data[10]))
        
    print("min_x, max_x : ", min_x, max_x)
    print("min_y, max_y : ", min_y, max_y)
    print("min_z, max_z : ", min_z, max_z)


def test_sommet_prise_vue(cursor):
    cursor.execute("SELECT c.id_missta, c.name, EXTRACT(YEAR FROM c.t0) FROM misphot.chantiers as c JOIN misphot.cliches as cl ON c.id = cl.chantier WHERE cl.point IS NULL GROUP BY c.id")
    records = cursor.fetchall()

    compte = 0
    for data in records:
        print(data)
        compte += 1
    print("Dans {} chantiers, au moins une image n'a pas de sommets de prise de vue renseignée".format(compte))

def test_quaternion(cursor):
    cursor.execute("SELECT c.id_missta, c.name, EXTRACT(YEAR FROM c.t0) FROM misphot.chantiers as c JOIN misphot.cliches as cl ON c.id = cl.chantier WHERE cl.quaternion IS NULL GROUP BY c.id")
    records = cursor.fetchall()

    compte = 0
    for data in records:
        print(data)
        compte += 1
    print("Dans {} chantiers, au moins une image n'a pas de quaternion renseignée".format(compte))


def test_footprint_au_sol(cursor):
    cursor.execute("SELECT c.id_missta, cl.image, ST_AsGeoJSON(cl.footprint), c.name, EXTRACT(YEAR FROM c.t0) FROM misphot.chantiers as c JOIN misphot.cliches as cl ON c.id = cl.chantier")
    records = cursor.fetchall()

    for data in records:
        if data[2] != None:
            footprint = json.loads(data[2])
            if len(footprint["coordinates"][0]) != 9 and len(footprint["coordinates"][0]) != 10:
                print("L'image {} du chantier {} {} n'a pas 8 points pour l'footprintau sol mais {}".format(data[1], data[3], data[4], len(footprint["coordinates"][0])-1))
        



def test_footprint_au_sol_None(cursor):
    cursor.execute("SELECT c.id_missta, c.name, EXTRACT(YEAR FROM c.t0) FROM misphot.chantiers as c JOIN misphot.cliches as cl ON c.id = cl.chantier WHERE ST_AsGeoJSON(cl.footprint) IS NULL GROUP BY c.id")
    records = cursor.fetchall()

    compte = 0
    for data in records:
        print(data)
        compte += 1
    print("Dans {} chantiers, au moins une image n'a pas d'footprintau sol renseignée".format(compte))


def get_projection(cursor):
    cursor.execute("SELECT projection, count(*) FROM misphot.chantiers GROUP BY projection")
    records = cursor.fetchall()

    for data in records:
        print(data)


def chantiers_problemes(cursor):
    cursor.execute("SELECT c.id_missta, c.name, EXTRACT(YEAR FROM c.t0) FROM misphot.chantiers as c JOIN misphot.cliches as cl ON c.id = cl.chantier WHERE cl.point IS NULL OR ST_AsGeoJSON(cl.footprint) IS NULL OR cl.quaternion IS NULL GROUP BY c.id")
    records = cursor.fetchall()

    dictionnaire = {}
    for i in range(1919, 2023):
        dictionnaire[str(i)] = 0

    compte = 0
    for data in records:
        print(data)
        compte += 1
        dictionnaire[str(data[2])] += 1
    print(dictionnaire)
    print("Dans {} chantiers, au moins une image a un problème".format(compte))
    for i in range(1919, 2023):
        if dictionnaire[str(i)] != 0:
            print("{} : {} chantiers problématiques".format(i, dictionnaire[str(i)]))

def chantier_une_deux_images(cursor):
    cursor.execute("SELECT count(*) FROM (SELECT count(*) AS compte FROM misphot.cliches AS c GROUP BY c.chantier HAVING count(*) >= 3) AS d")
    records = cursor.fetchall()
    for data in records:
        print("Il y a {} chantiers avec au moins 3 images".format(data[0]))

    cursor.execute("SELECT count(*) FROM (SELECT count(*) AS compte FROM misphot.cliches AS c GROUP BY c.chantier HAVING count(*) <=4) AS d")
    records = cursor.fetchall()
    for data in records:
        print("Il y a {} chantiers avec une ou deux images".format(data[0]))


def chantiers_obliques(cursor):
    cursor.execute("SELECT count(*) FROM misphot.chantiers AS c WHERE c.note ILIKE '%OBLIQUE%' OR c.note ILIKE '%oblique%'")
    records = cursor.fetchall()
    for data in records:
        print(data)

def chantiers_a_faire(cursor):
    """
    Chantiers sans obliques, avec au moins 3 images, et où toutes les images ont des sommets de prise de vue et des footprints au sol et antérieurs à 2003
    """
    
    cursor.execute("SELECT count(*), AVG(compte) FROM (SELECT count(*) AS compte FROM misphot.cliches AS c JOIN misphot.chantiers AS ch ON ch.id = c.chantier WHERE ((ch.note NOT LIKE '%OBLIQUE%' AND  ch.note NOT LIKE '%oblique%') OR ch.note IS NULL) AND EXTRACT(YEAR FROM ch.t0) <= 2003 AND ch.id NOT IN (SELECT c.id FROM misphot.chantiers as c JOIN misphot.cliches as cl ON c.id = cl.chantier WHERE cl.point IS NULL OR ST_AsGeoJSON(cl.footprint) IS NULL OR cl.quaternion IS NULL GROUP BY c.id)  GROUP BY c.chantier HAVING count(*) >= 3) AS d")

    records = cursor.fetchall()
    compte = 0
    for data in records:
        compte += 1
        print(data)
    print(compte)



def chantiers_couleurs(cursor):
    """
    Nombre de chantiers en couleur, en infrarouge et en IRC
    """

    cursor.execute("SELECT count(*), c.emulsion FROM misphot.chantiers AS c GROUP BY c.emulsion")
    records = cursor.fetchall()
    for data in records:
        print("{} : {}".format(data[1], data[0]))



    cursor.execute("SELECT count(*) FROM misphot.chantiers AS c WHERE c.emulsion ILIKE 'Panchromatique' AND c.note ILIKE '%infra-rouge couleur%'")
    records = cursor.fetchall()
    for data in records:
        print("Il y a {} chantiers qui existent en panchromatique et en infrarouge couleur".format(data[0]))

    cursor.execute("SELECT count(*) FROM misphot.chantiers AS c WHERE c.emulsion ILIKE 'Infra-Rouge Couleur' AND c.note ILIKE '%Panchromatique%'")
    records = cursor.fetchall()
    for data in records:
        print("Il y a {} chantiers qui existent en panchromatique et en infrarouge couleur".format(data[0]))

    print("")
    
    cursor.execute("SELECT count(*) FROM misphot.chantiers AS c WHERE c.emulsion ILIKE 'Panchromatique' AND c.note ILIKE '%infra-rouge%' AND NOT c.note ILIKE '%couleur%'")
    records = cursor.fetchall()
    for data in records:
        print("Il y a {} chantiers qui existent en panchromatique et en infrarouge".format(data[0]))

    cursor.execute("SELECT count(*) FROM misphot.chantiers AS c WHERE c.emulsion ILIKE 'Infra-Rouge' AND c.note ILIKE '%Panchromatique%'")
    records = cursor.fetchall()
    for data in records:
        print("Il y a {} chantiers qui existent en panchromatique et en infrarouge".format(data[0]))

    print("")


    cursor.execute("SELECT count(*) FROM misphot.chantiers AS c WHERE c.emulsion ILIKE 'Panchromatique' AND c.note ILIKE '%couleur%' AND NOT c.note ILIKE '%infra-rouge%'")
    records = cursor.fetchall()
    for data in records:
        print("Il y a {} chantiers qui existent en panchromatique et en couleur".format(data[0]))

    cursor.execute("SELECT count(*) FROM misphot.chantiers AS c WHERE c.emulsion ILIKE 'Couleur' AND c.note ILIKE '%Panchromatique%'")
    records = cursor.fetchall()
    for data in records:
        print("Il y a {} chantiers qui existent en panchromatique et en couleur".format(data[0]))

    print("")



    cursor.execute("SELECT count(*) FROM misphot.chantiers AS c WHERE c.emulsion ILIKE 'Couleur' AND c.note ILIKE '%infra-rouge couleur%'")
    records = cursor.fetchall()
    for data in records:
        print("Il y a {} chantiers qui existent en couleur et en infrarouge couleur".format(data[0]))

    cursor.execute("SELECT count(*) FROM misphot.chantiers AS c WHERE c.emulsion ILIKE 'Infra-Rouge Couleur' AND c.note ILIKE '%couleur%'")
    records = cursor.fetchall()
    for data in records:
        print("Il y a {} chantiers qui existent en couleur et en infrarouge couleur".format(data[0]))

    print("")

    cursor.execute("SELECT count(*) FROM misphot.chantiers AS c WHERE c.emulsion ILIKE 'Couleur' AND c.note ILIKE '%infra-rouge%' AND NOT c.note ILIKE '%couleur%'")
    records = cursor.fetchall()
    for data in records:
        print("Il y a {} chantiers qui existent en couleur et en infrarouge".format(data[0]))

    cursor.execute("SELECT count(*) FROM misphot.chantiers AS c WHERE c.emulsion ILIKE 'Infra-Rouge' AND NOT c.note ILIKE '%infra-rouge%' AND  c.note ILIKE '%couleur%'")
    records = cursor.fetchall()
    for data in records:
        print("Il y a {} chantiers qui existent en couleur et en infrarouge".format(data[0]))
        
    print("")
    cursor.execute("SELECT count(*) FROM misphot.chantiers AS c WHERE c.emulsion ILIKE 'Infra-Rouge' AND c.note ILIKE '%infra-rouge couleur%'")
    records = cursor.fetchall()
    for data in records:
        print("Il y a {} chantiers qui existent en infrarouge et en infrarouge couleur".format(data[0]))

    cursor.execute("SELECT count(*) FROM misphot.chantiers AS c WHERE c.emulsion ILIKE 'Infra-Rouge Couleur' AND c.note ILIKE '%infra-rouge%'")
    records = cursor.fetchall()
    for data in records:
        print("Il y a {} chantiers qui existent en infrarouge et en infrarouge couleur".format(data[0]))







user = args.user
password = args.password
host = args.host
port = args.port
database = args.database


connection = psycopg2.connect(
		user = user,
		password = password,
		host = host,
		port = port,
        database = database
	)
cursor = connection.cursor()

#cursor.execute("select relname from pg_class where relkind='r' and relname !~ '^(pg_|sql_)';")

#cursor.execute("select vol from misphot.bandes")

# Retrieve query results
#records = cursor.fetchall()
#print(records)

#test_camera(cursor)
#test_position_cliche(cursor)

#Vérifie que toutes les images ont un sommet de prise de vue renseigné 
#test_sommet_prise_vue(cursor)

#Vérifie que toutes les images ont un quaternion de renseigné
#test_quaternion(cursor)

#Liste les projections existantes 
#get_projection(cursor)




#Vérifie qu'il existe une footprintau sol pour toutes les images
#test_footprint_au_sol_None(cursor)

#test_footprint_au_sol(cursor)

#chantiers_problemes(cursor)

#Compte le nombre de chantiers avec une ou deux images
#chantier_une_deux_images(cursor)

#Compte le nombre de chantiers obliques
#chantiers_obliques(cursor)

#chantiers_a_faire(cursor)


chantiers_couleurs(cursor)