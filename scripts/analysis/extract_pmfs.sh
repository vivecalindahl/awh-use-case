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
echo "Extracting PMFs for $nreplicas replicas for ${nwalkers[@]} number of walkers from data in $datadir"

gmx=gmx # for now assume is there

start=`pwd -P`

reloutdir="./analysis/pmfs"
echo "Writing into directory $reloutdir"
outdir=${start}/$reloutdir

for n in ${nwalkers[@]}; do	

    for ((i=0; i<$nreplicas; i++)); do
	echo "replica $i, walker $j"

	replica=${datadir}/${n}-walkers/replica-${i}	
	tpr=${replica}/walker-0/topol.tpr
	edr=${replica}/walker-0/ener.edr

	out=${outdir}/${n}-walkers/replica-${i}
	mkdir -p $out
	cd $out
	awh_args="-f $edr -s $tpr -more -kt"
	$gmx awh $awh_args  &> awh.log || { echo "gmx awh $awh_args failed in $(pwd -P) "; exit 1; }

    done;
done

