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


TA=$1


if test "$#" = 0; then
    echo "visualize_flight_plan.sh :"
    echo "TA : path"
else
    workspace=$(dirname ${TA})
    rm workspace.txt
    echo $workspace >> workspace.txt
    python scripts/visualize_flight_plan.py --TA ${TA} --chantier ${workspace}
fi