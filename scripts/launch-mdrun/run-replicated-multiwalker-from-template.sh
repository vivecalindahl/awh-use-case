#/bin/bash

args=( "$@" )
function print_usage_exit
{
    echo "Usage: $0 <template> <nreplicas> [<nwalkers>] "
    exit 0
}

nargsmin=3
[ "${#args[@]}" -lt $nargsmin ] && { echo "Too few arguments given." && print_usage_exit; }
template=${args[0]}
[ ! -d $template ] && { echo "directory $template not found"; exit 1; } 
template=`readlink -f $template`
nreplicas=${args[1]}

nwalkers=()
for ((i=2; i<${#args[@]}; i++)); do
    nwalkers+=(${args[$i]})
done

echo "Making $nreplicas replicas for each number of walkers ${nwalkers[@]} from $template"

start=`pwd -P`

# gromacs binary
module load gromacs/2018.1
#gmx=gmx_seq

# My own gmx build                                                                                                                                                                                                                                                                                                           
gmx_login=/cfs/klemming/nobackup/v/vivecal/programs/gromacs-login/2018.1/bin/gmx


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
	    $gmx_login grompp $gromppflags $ndxflag &> ${out}/grompp.log || exit 1

	    mv topol.tpr $out
	    rm mdout.mdp
	done;
    done;
done
cd $start
rm -r template_work