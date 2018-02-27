#/bin/bash

args=( "$@" )
function print_usage_exit
{
    echo "Usage: $0 <template>"
    exit 0
}

# gromacs binary
module load gromacs/2018.1
gmx=gmx_seq

nargs=1
[ "${#args[@]}" -ne $nargs ] && { echo "No input arguments given." && print_usage_exit; }
template=$1
[ ! -d $template ] && { echo "directory $template not found"; exit 1; } 
template=`readlink -f $template`

nreplicas=4;
nwalkers=( 1 2 4 8 16 32 64 );
start=`pwd -P`

# work from the template, to generate tprs
cp -r template template_work
cd template_work
for n in ${nwalkers[@]}; do	
    echo "Creating ${n}-walker runs"
    echo "replicating by $nreplicas"
    for ((i=0; i<$nreplicas; i++)); do
	for  ((j=0; j<$n; j++)); do 
	    echo "replica $i, walker $j"
	    out=${start}/data/${n}-walkers/replica-${i}/walker-${j}

	    mkdir -p $out

	    ndxflag=""
	    gromppflags="-maxwarn 1"
	    [ -e "index.ndx" ] && ndxflag='-n'
	    $gmx grompp $gromppflags $ndxflag &> ${out}/grompp.log || exit 1

	    mv topol.tpr $out
	    rm mdout.mdp
	done;
    done;
done
cd $start
rm -r template_work