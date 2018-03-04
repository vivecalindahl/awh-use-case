#/bin/bash

args=( "$@" )
function print_usage_exit
{
    echo "Usage: $0 <template> <nreplicas> [<nwalkers>] "
    exit 0
}

# Read the arguments and/or print usage
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

# Make the directory structure and generate the tprs using gmx grompp
echo "Making $nreplicas replicas for ${nwalkers[@]} number of walkers using template: $template"

# My own gmx build, has the same dependencies as the gromacs module.
module load gromacs/2018.1
gmx_login=/cfs/klemming/nobackup/v/vivecal/programs/gromacs-login/2018.1/bin/gmx
gmx_mpi=/cfs/klemming/nobackup/v/vivecal/programs/gromacs/2018.1/bin/gmx

start=`pwd -P`
# work in a copy of the template directory to generate tprs
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

# Launch the simulations. Split the job of each replica into many shorter jobs.
# Each replica gets its own name, then use the sbatch flag
# --dependency=singleton to link jobs with the same name together.

# Generate a slurm job script for the given number of walkers and with
# a unique job name given by the replica index.
generate_and_submit_job_script()
{
nw=$1 # number of walkers
i=$2  # replica index (warning for bad variable name...)   
job_out=$3 # Name of file to write to.

# sbatch arguments
time="00:15:00"
account="2017-11-25"
jobname="dna-x${nw}-${i}"
ntasks=$((32*nw))
nodes=$((1*nw))
ntaskspernode=32
cpuspertask=1
constraint="[group-0|group-1|group-2|group-3|group-4]"

# Settings for launching mdrun using sbatch

hours=$(echo "${time}" | awk -F ':' '{print $1 + $2/60 + $3/(60*60)}')
cont_opts="-cpi -maxh $hours"
npme=2; nstlist=40; dlb=no; ntomp=2;
std_opts="-pin on -quiet -v -stepout 10000 -nstlist ${nstlist} -dlb ${dlb} -npme ${npme} -ntomp ${ntomp}"
walker_indices=($(seq  0 $((nw-1))))

walker_dirs=()
prefix='walker-'
for j in ${walker_indices[@]}; do
    walker_dirs+=("${prefix}${j}")
done

mdrun="$gmx_mpi mdrun $std_opts $cont_opts -multidir ${walker_dirs[@]}"

aprun_opts="-cc none"
aprun_opts+=" -n $ntasks -N $ntaskspernode"
mdrun_cmd="aprun $aprun_opts $mdrun"

echo -e \
"#!/bin/bash -l

#SBATCH --account=${account}
#SBATCH --time=${time}
#SBATCH --job-name=${jobname}
#SBATCH --ntasks=${ntasks}
#SBATCH --nodes=${nodes}
#SBATCH --ntasks-per-node=${ntaskspernode}
#SBATCH --cpus-per-task=${cpuspertask}
#SBATCH --constraint=${constraint}

export MPICH_GNI_MAX_EAGER_MSG_SIZE=131072 # maybe useful anymore

module load gromacs/2018.1

echo '---> Running:' $mdrun_cmd

$mdrun_cmd

echo '---> Reached end of run script.'
" \
> $job    

# Here calculate the number of jobs to run based on the maximum total allocated run time.
totalhours=24
# no. of jobs = total time/time per job
njobs=$(awk -v hours=$hours -v totalhours=$totalhours 'BEGIN{print int(totalhours/hours)}')

# launch dependent (chained) jobs for this replica
for ((j=0; j<${njobs}; j++)); do 
    sbatch --dependency=singleton $job
done
}

for nw in ${nwalkers[@]}; do
    for ((i=0; i<${nreplicas}; i++)); do

	mdrundir=${start}/data/${n}-walkers/replica-${i}
	cd $mdrundir 
	job=x${nw}-${i}.job
	generate_and_submit_job_script $nw $i $job
    done
done
