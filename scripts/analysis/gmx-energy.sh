#!/bin/bash

args=( "$@" )
function print_usage_exit
{
    echo "Usage: $0 <data-dir> <nreplicas> [<nwalkers>] "
    exit 0
}

# Read the arguments and/or print usage
nargsmin=3
[ "${#args[@]}" -lt $nargsmin ] && { echo "Too few arguments given." && print_usage_exit; }
datadir=${args[0]}
[ ! -d $datadir ] && { echo "directory $datadir not found"; exit 1; } 
datadir=`readlink -f $datadir`
nreplicas=${args[1]}

nwalkers=()
for ((i=2; i<${#args[@]}; i++)); do
    nwalkers+=(${args[$i]})
done

# Make the directory structure and generate the tprs using gmx grompp
echo "Extracting variables from energy file"

gmx=gmx # for now assume is there

start=`pwd -P`

reloutdir="./analysis/gmx-energy"
echo "Writing into directory $reloutdir"
outdir=${start}/$reloutdir

for n in ${nwalkers[@]}; do	

    for ((i=0; i<$nreplicas; i++)); do
	    replica=${datadir}/${n}-walkers/replica-${i}
	for ((j=0; j<$n;j++)); do
	    echo "replica $i, walker $j"
	    tpr=${replica}/walker-${j}/topol.tpr
	    edr=${replica}/walker-${j}/ener.edr
	    out=${outdir}/${n}-walkers/replica-${i}/walker-${j}
	    mkdir -p $out

	    cd $out
	    energy_args="-f $edr -s $tpr"	   
	    #echo -e 'box-x \n box-y \n box-z' |  $gmx energy $energy_args  &> energy.log || { echo "$gmx energy $energy_args failed in $(pwd -P) "; exit 1; }       
	    echo -e 'box-z' |  $gmx energy $energy_args  &> energy.log || { echo "$gmx energy $energy_args failed in $(pwd -P) "; exit 1; }       
	done
    done;
done

