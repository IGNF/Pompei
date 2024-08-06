metadonnees_xml=$1


if test "$#" = 0; then
    echo "visualisation_plan_vol.sh :"
    echo "metadonnees_xml : path"
else
    repertoire_chantier=$(dirname ${metadonnees_xml})
    python scripts/visualisation.py --input_xml ${metadonnees_xml} --chantier ${repertoire_chantier}
fi