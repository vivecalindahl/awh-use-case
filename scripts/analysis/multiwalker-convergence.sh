#!/bin/bash

args=( "$@" )
function print_usage_exit
{
    echo "Usage: $0 <tstart> <dt> <tend> <pmfdir> [<nwalkers>] "
    exit 0
}

# Read the arguments and/or print usage
nargsmin=4
[ "${#args[@]}" -lt $nargsmin ] && { echo "Too few arguments given." && print_usage_exit; }
tstart=${args[0]}
dt=${args[1]}
tend=${args[2]}
pmfdir=${args[3]}
[ ! -d "$pmfdir" ] && { echo "$pmfdir not found"; exit 1; }
nwalkers=()
for ((i=4; i<${#args[@]}; i++)); do
    nwalkers+=(${args[$i]})
done

# Now assume helper script should be in the same directory as the called script
scriptsdir=$(dirname $(readlink -f $0))

#maxn=$(IFS=$'\n';  echo "${nwalkers[*]}" | sort -nr | head -n 1 ; unset IFS)
#n=$maxn
outdir="./analysis/convergence"
echo "Writing into directory $reloutdir"
mkdir -p $outdir


common_ref=${outdir}/ref_any-walkers.dat
${scriptsdir}/calc_error_t.py  --out ${outdir}/convergence_any-walkers.dat $tstart $dt $tend --runs  ${pmfdir}/*-walkers/replica-*/ \
    --refout $common_ref --col 2 ; 

[ ! -e "$common_ref" ] && { echo "$common_ref not generated"; exit 1; }


for n in ${nwalkers[@]}; do
    # col 2 has coord bias (for now use that)

    ${scriptsdir}/calc_error_t.py  --out ${outdir}/convergence_self-ref_${n}-walkers.dat $tstart $dt $tend --runs  ${pmfdir}/${n}-walkers/replica-*/ \
	--refout ${outdir}/ref_${n}-walkers.dat --col 2 ; 

    ${scriptsdir}/calc_error_t.py  --out ${outdir}/convergence_common-ref_${n}-walkers.dat $tstart $dt $tend --runs  ${pmfdir}/${n}-walkers/replica-*/ \
	--refout ref.tmp --reffile $common_ref --col 2 ; 
    rm ref.tmp
done


# Write out the average time to get below the given cutoff error as a function of the number of walkers
cutoff=2; ## TODO change
out=${outdir}/time-to-error-${cutoff}kT-walker-scaling.dat
rm -f $out
for n in ${nwalkers[@]}; do
    errordata=${outdir}/convergence_common-ref_${n}-walkers.dat;
    tfirst=$(awk -v cutoff=$cutoff '{t=$1; err=$2; if (err < cutoff){print t; exit};}' $errordata )
    echo $n  $tfirst >> $out
done
