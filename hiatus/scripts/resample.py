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

import argparse
import cv2

parser = argparse.ArgumentParser(description='Rééchantillonne le SRTM et le MNS calculé par MicMac à la même résolution')
parser.add_argument('--input_SRTM', default='', help='Image du SRTM')
parser.add_argument('--output_SRTM', default='', help='Image SRTM rééchantillonnée')
parser.add_argument('--res', default='2', help="résolution sur l'image du SRTM")
parser.add_argument('--input_histo', default='', help='Image histo')
parser.add_argument('--output_histo', default='', help='Image histo rééchantillonnée')
args = parser.parse_args()



img = cv2.imread(args.input_SRTM, cv2.IMREAD_UNCHANGED)
dim = (int(img.shape[0] * float(args.res)), int(img.shape[1] * float(args.res)))
img_resized = cv2.resize(img, dim, interpolation=cv2.INTER_CUBIC)
cv2.imwrite(args.output_SRTM, img_resized)


img_histo = cv2.imread(args.input_histo, cv2.IMREAD_UNCHANGED)
img_histo_resized = cv2.resize(img_histo, dim, interpolation=cv2.INTER_CUBIC)
cv2.imwrite(args.output_histo, img_histo_resized)