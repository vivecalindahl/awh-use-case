#!/bin/bash

# ==========================================================================
# Read input
# ==========================================================================
function print_usage
{
  echo "Usage: $0 -f <.pdb> -water <enum> -ff <string> [-h]"
}

old_gmx_is_ok=false;
while [ $# -gt 0 ]; do 
  case "$1" in    
    -h)       print_usage; exit 0;;
    -f)       pdb_in="$2"; shift;;
    -ff)      forcefield="$2"; shift;;
    -water)   water="$2"; shift;;
    -try)   old_gmx_is_ok=true; shift;;
    *)    echo "invalid option: $1" && exit 1;;
  esac 
  shift 
done

# Sanity and existence checks
[ -z "$pdb_in" ] && print_usage && exit
[ ! "${pdb_in##*.}" == "pdb" ] && echo "$pdb_in is not a pdb-file" && print_usage && exit 1 
[ ! -e "$pdb_in" ] && echo "$pdb_in does not exist" && exit 1 

[ -z "$forcefield" ] && print_usage && exit 
[ -z "$water" ] && print_usage && exit 


# 'gmx' command is assumed to be available but can be changed to any binary here.
gmx="gmx"
[ -z "$(which $gmx)" ]  && { $gmx; exit 1; }

# This script is intended for gmx version >= 2018.1  but it's not always strictly necessary.
gmx_major=$($gmx --version | sed  -n 's/GROMACS version: *\([0-9]*\)\.*\([0-9]*\).*/\1/p')
gmx_minor=$($gmx --version | sed  -n 's/GROMACS version: *\([0-9]*\)\.*\([0-9]*\).*/\2/p')

[ -z ${gmx_major} ] && { "Failed to read gmx version"; exit 1; }
min_major=2018
min_minor=1

old_gmx=false
if  [ ${gmx_major} -eq ${min_major} ]; then
    if   [ -z ${gmx_minor} ] || [ ${gmx_minor} -lt ${min_minor} ]; then
	old_gmx=true
    fi
elif [ ${gmx_major} -lt ${min_major} ]; then
    old_gmx=true
fi

if $old_gmx && ! $old_gmx_is_ok; then
    echo "gmx version ${gmx_major}.${gmx_minor} is less than the minimum recommended gmx version ${min_major}.${min_minor}."
    echo "Use '-try' flag to try anyway."
    exit 1
elif $old_gmx; then
    echo "Warning: gmx version ${gmx_major}.${gmx_minor} is less than the minimum recommended gmx version ${min_major}.${min_minor}."\
         "Proceeding anyway."
fi

# ==========================================================================
# The actual work:
# create a periodically connected molecule topology for DNA
# ==========================================================================
# Notes:
# 1) Likely this is easy to generalize to e.g. RNA.
# 2) Tested for charmm27 and parmbsc1 (amber99bsc1.ff)
# 3) It's assumed there is nothing but the DNA molecule in the pdb.

# The strategy: copy the first residue of each chain to the end of each n-residue long chain,
# making a temporary new n+1 long chain. This way we can "trick" gmx pd2gmx to
# generate all the interaction terms we need, and then we delete what is not needed.

# A pdb to work with
pdb_work="./work.pdb"

# and a file for temporary output
tmp_log="./tmp.log"

# Contents of columns in pdb file format
chain_col=5;
resid_col=6;

# Add residue to the work pdb, for each chain.
awk -v chain_col=$chain_col -v resid_col=6 \
'{chain=$chain_col;  resid=$resid_col;
if (chain != prev_chain){if (str != ""){print str; str=""}; first_res=resid;};
if ($1 ~ /^ATOM/ && resid==first_res){if(str != ""){str=str"\n"$0}else{str=$0};};
prev_chain=chain; print}' \
$pdb_in  > $pdb_work

# Generate topology and config gro-file for the n+1 chain.

# We need a local copy of the forcefield that we can modify.
$gmx pdb2gmx -f ${pdb_in} -ff ${forcefield} -water ${water} &> ${tmp_log}
forcefield_dir=$(awk '/Opening force field file/{gsub(/.ff.*/,".ff", $5);print $5; exit}' ${tmp_log})
[ -z "$forcefield_dir" ] && echo "Could not extract force field location from pdb2gmx. See ${tmp_log}." && exit 1

ff_work="${forcefield}_work"
ff_work_dir="./${ff_work}.ff"
cp -r $forcefield_dir $ff_work_dir

# Remove special treatment of the end termini in the .r2b file if there is one.
r2b="${ff_work_dir}/dna.r2b"
if [ -e "$r2b" ]; then
    mv $r2b ${r2b}"_tmp"
    awk '/;/{print; next}; {if (NF==5){print $1, $2, $2, $2, $2} else{print}}' ${r2b}"_tmp" > $r2b
    rm ${r2b}"_tmp"
fi

# Need to add a hack to the terminal data base file for pdb2gmx to accept the ends
# without modification. To avoid having to parse the interactive session of pdb2gmx,
# remove all .tdb entries other than those we define, so there is only one choice
# for each end (here we assume there is only the periodic molecule in the pdb)

# Make a custom tdb-file for the 5' end to force gmx pdb2gmx to allow end residue
# that have (temporarily) missing bonds.
# This hack (loophole?) will avoid ax gmx pdb2gmx fatal error. 
rm -f ${ff_work_dir}/*.n.tdb  # 5' end
rm -f ${ff_work_dir}/*.c.tdb  # 3' end

# For a gmx version < 2018.1 the pdb2gmx '-missing' flag was more strict requiring
# this hack to avoid a fatal error.
tdb5="${ff_work_dir}/dna.n.tdb" 
if $old_gmx; then 
    if [ "${forcefield}" == 'amber99bsc1' ]; then
	echo -e "[ hack ]\n[ replace ]\nC5' C5' CI 12.01 -0.0069" > $tdb5
    elif [ "${forcefield}" == 'charmm27' ]; then
	echo -e "[ hack ]\n[ replace ]\nC5' C5' CN8B 12.011 -0.08" > $tdb5
    else
	echo "Forcefield $forcefield not supported."; exit 1
    fi
else
    echo -e "[ none ]" > $tdb5
fi

# Put a dummy entry "none" on the 3' side.
tdb3="${ff_work_dir}/dna.c.tdb" 
echo -e "[ none ]" > $tdb3

# Generate .top and .gro files rom the unmodified configuration.
# The .gro file will be compatible with the periodic .top file.
# The .top file will be used a reference when modifying the n+1 
# topology to keep track of the start and end (atoms) of each
# molecule chain.
nonperiodic="non-periodic"
$gmx pdb2gmx -v -missing -f $pdb_in -ff ${ff_work} -water ${water} -ter -o "${nonperiodic}.gro" -p "${nonperiodic}.top"  &> $tmp_log || \
    { echo "gmx pdb2gmx exited with an error. See ${tmp_log}."; exit 1; }

# List with the non-periodic topology (.itp) files of each chain
itp_list=(`grep  "chain.*itp" ${nonperiodic}.top | awk '{print $NF}' | awk -F  \" '{print $2}'`)

# Extract the last atom index of the unmodified topology, for each chain.
max_atom_index_list=()
for itp in ${itp_list[@]}; do
    name='atoms'
    max_atom_index=`awk -v  name=$name 'BEGIN{found=0;};/^ *\[ /{ if ($2 == name){found=1; getline;} else { found=0 }};{if (found && $1 != ";"  && $1 !~ /^ *#/ && NF>0){max_atom_index=$1};}END{print max_atom_index}' $itp`
    max_atom_index_list+=($max_atom_index)
done

# Generate .top and .gro files of n+1 config
$gmx pdb2gmx -v -missing -f $pdb_work -ff ${ff_work} -water ${water} -ter -o "extra.gro" -p "extra.top"  &> $tmp_log || \
    { echo "gmx pdb2gmx exited with an error. See ${tmp_log}."; exit 1; }
extra_itps=(`grep  "chain.*itp" "extra.top" | awk '{print $NF}' | awk -F  \" '{print $2}'`)

# Modify the n+1 topology into the periodic topology.
for chain in ${!extra_itps[@]}; do
    top_in=${extra_itps[chain]}
    max_atom_index=${max_atom_index_list[chain]}
    top_out=`echo ${top_in} | awk -F "extra_" '{print "periodic_"$2}'`
    
    # array with the number of atoms listed for each type of interaction
    declare -A natoms
    natoms['bonds']=2
    natoms['angles']=3
    natoms['dihedrals']=4
    natoms['pairs']=2
    natoms['atoms']=1

    # Modify the topology.
    # For each gmx itp-directive (interaction type), 
    # 1) remove entries with atom indices only containing the added residue n+1
    # 2) in "mixed" entries containing the connections between residues n and n+1,
    #    remap atom indices of residue n+1 to the first residue, i.e:
    #    i --> i + max_atom_index, if i > max_atom_index,  where max_atom_index = max index of the chain.
    top_work="tmp.top"

    cp $top_in $top_work
    for name in ${!natoms[@]}; do
	natoms=${natoms[$name]}
	# 1) Don't print interactions where the all involved atoms are in residue  n+1.
	# 2) Modify (remap) interactions where some involved atoms are in residue  n+1.
	# 3) Otherwise, print as is.
	awk -v max_atom_index=$max_atom_index -v name=$name -v natoms=$natoms 'BEGIN{found=0};
/^ *\[ /{ if ($2 == name){found=1; print; getline;} else { found=0 }};
{ if (found && $1 != ";"  && $1 !~ /^ *#/ && NF>0){ count=0; for (j=1; j<=natoms; j++){if ($j >max_atom_index){$j=($j-max_atom_index); count++}}; if (count<natoms){print}}
else{print} }' $top_work > $top_out

	cp $top_out $top_work
    done; 
done

# Tweak entries of final topology, rename to the default topol.top
top_out="topol.top"
sed -i 's/extra/periodic/' extra.top;
mv extra.top $top_out

# Merge top and itps, just to get a single topology file.

# Replace include of chain itp with the contents
# (would like to use something like
#  sed  '/^ *\#include \"\(.*\)\"/r  \1' topol.top 
# but did not work.)
itp_list=(`grep  "chain.*itp" $top_out | awk '{print $NF}' | awk -F  \" '{print $2}'`)
for itp in ${itp_list[@]}; do
    # sed r command appends the itp file after the matching include statement
    sed -i "/^ *\#include *\"$itp/r  $itp" ${top_out};

    # delete the include statement
    sed  -i "s/^ *\#include *\"$itp.*//g"  ${top_out};
done

# Remap the forcefield entry to the unmodified one.
sed -i "s/${ff_work}/${forcefield}/" ${top_out}

# Did we find the force field locally, in this directory?
nonlocal_ff=true
[[  "$forcefield_dir" =~ ^\..* ]] && nonlocal_ff=false
if $nonlocal_ff; then
    sed -i "s/.\/${forcefield}/${forcefield}/" ${top_out}
fi

# Add comment about how this file at the top of the topology file.
script=$(basename $0)
args="$@"

# Here 1s refers to the first position in the file and '~' is used as the sed delimiter
# since the variables may contain '/'.
sed -i "1s~^~; This file was automatically generated using \"$0 $args\"~" topol.top

gro_out="conf.gro"
mv ${nonperiodic}.gro $gro_out

# Clean up
#ls  | grep -v "$gro_out" | grep -v "$top_out" | xargs -n 1 rm -rf
rm -rf *extra_DNA*.itp* *extra*.gro* \
    *periodic_DNA*.itp* \
    *non-periodic_DNA*.itp*  *non-periodic*.top* \
    *posre_DNA*.itp* \
    $pdb_work $top_work $tmp_log \
    $ff_work_dir
