TA=$1


if test "$#" = 0; then
    echo "visualize_flight_plan.sh :"
    echo "TA : path"
else
    workspace=$(dirname ${TA})
    python scripts/visualize_flight_plan.py --TA ${TA} --chantier ${workspace}
fi