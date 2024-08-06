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