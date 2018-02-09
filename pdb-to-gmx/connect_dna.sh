#!/bin/bash

# Given a pdb with sequence XYZ, add an extra residue X' yielding XYZX' such that pdb2gmx
# gives us the topology terms needed for later periodically connecting Z to X  (...-XYZ-XYZ-...).

# The given sequence should have all atoms needed for periodic connection,
# i.e. an end residue should have the same atoms as if it were a central residue.
pdb_in=$1;
[ -z "$pdb_in" ] && echo "No pdb given" && exit

[ ! -e "$pdb_in" ] && echo "$pdb_in does not exist" && exit 1

# gmx binary to use
gmx="gmx"

pdb_work="work.pdb"

# Contents of columns in pdb file format
chain_col=5;
resid_col=6;

# Copy the first residue of each chain to the end of each n-residue long chain,
# making a temporary new n+1 long chain.
awk -v chain_col=$chain_col -v resid_col=6 \
'{chain=$chain_col;  resid=$resid_col;
if (chain != prev_chain){if (str != ""){print str; str=""}; first_res=resid;};
if ($1 ~ /^ATOM/ && resid==first_res){if(str != ""){str=str"\n"$0}else{str=$0};};
prev_chain=chain; print}' \
$pdb_in  > $pdb_work

#---------- Generate topology and config gro-file for the n+1 chain.

# Need to add a hack to the terminal data base file for pdb2gmx to accept the ends
# without modification.
#forcefield="charmm27"
gmx_loc=`echo \`which $gmx\` | awk -F 'bin' '{print $1}'`
forcefield="charmm27"
forcefield_dir=`find $gmx_loc -name "${forcefield}.ff"`
[ ! -d "$forcefield_dir" ] && { echo "Force field ${forcefield} not found in gmx installation directory $gmx_loc"; exit 1; }
local_ff="./${forcefield}.ff"
rm -rf "./${forcefield}.ff"
cp -r $forcefield_dir .

# tdb-file for the 5' end
tdb="./${forcefield}.ff/dna.n.tdb" 
# Overwrite with a hack
echo -e "[ hack ]\n[ replace ]\nC5' C5' CN8B 12.011 -0.08" > $tdb

# Dummy-run pdb2gmx (choosing termini indexed by 0 and 0) to figure out what the real indices of the termini we want to select are.
# Use the local hacked force field.
tmp_log="tmp.log"

nchains=`awk -v chaincol=$chain_col '/^ATOM/{chain=$chaincol; print chain}' $pdb_in  | sort -u  | wc -l`
nter=$((nchains*2))
sel_str=""; for ((i=0; i < ${nter}; i++)); do sel_str=$sel_str"0\\n"; done; 
echo -e "$sel_str" | $gmx pdb2gmx -v -f $pdb_work -ff ${forcefield} -water tip3p -ter -o "tmp" -p "tmp" &> $tmp_log

ter_selection=`awk '/Select start/{sel="hack"; getline; while(sel != $2){getline}; print $1};
/Select end/{sel="None"; getline; while(sel != $2){getline}; print $1}' ${tmp_log} \
 | awk -F ":" '{print $1}'`

ter_selection=($ter_selection)
[ ${#ter_selection[@]} -ne 2 ] && { echo "Should have got 2 ter indices. Have indices: ${ter_selection[@]}"; exit 1; }

sel_str="";
for ((i=0; i < ${nter}; i++)); do
    sel=${ter_selection[$((i%2))]}
    sel_str=$sel_str"${sel}\\n";
done;

# Top and gro from unmodified config
nonperiodic="non-periodic"
echo -e "$sel_str" | $gmx pdb2gmx -v -f $pdb_in -ff ${forcefield} -water tip3p -ter -o "${nonperiodic}.gro" -p "${nonperiodic}.top"  &> $tmp_log

chain_itps=(`grep  "chain.*itp" ${nonperiodic}.top | awk '{print $NF}' | awk -F  \" '{print $2}'`)

# Extract the last atom index of the uncapped topology, for each chain
imaxs=()
for itp in ${chain_itps[@]}; do
    name='atoms'
    imax=`awk -v  name=$name 'BEGIN{found=0;};/^ *\[ /{ if ($2 == name){found=1; getline;} else { found=0 }};{if (found && $1 != ";"  && $1 !~ /^ *#/ && NF>0){imax=$1};}END{print imax}' $itp`
    imaxs+=($imax)
done

# Top and gro from "capped" config
echo -e "$sel_str" | $gmx pdb2gmx -v -f $pdb_work -ff ${forcefield} -water tip3p -ter -o "extra.gro" -p "extra.top"  &> $tmp_log
extra_itps=(`grep  "chain.*itp" "extra.top" | awk '{print $NF}' | awk -F  \" '{print $2}'`)

#-------------  Modify the topology

for chain in ${!extra_itps[@]}; do
    top_in=${extra_itps[chain]}
    imax=${imaxs[chain]}
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
    #    i --> i + imax, if i > imax,  where imax = max index of the chain.
    top_work="tmp.top"

    cp $top_in $top_work
    for name in ${!natoms[@]}; do
	natoms=${natoms[$name]}
	# 1) Don't print interactions where the all involved atoms are in residue  n+1.
	# 2) Modify (remap) interactions where some involved atoms are in residue  n+1.
	# 3) Otherwise, print as is.
	awk -v imax=$imax -v name=$name -v natoms=$natoms 'BEGIN{found=0};
/^ *\[ /{ if ($2 == name){found=1; print; getline;} else { found=0 }};
{ if (found && $1 != ";"  && $1 !~ /^ *#/ && NF>0){ count=0; for (j=1; j<=natoms; j++){if ($j >imax){$j=($j-imax); count++}}; if (count<natoms){print}}
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
chain_itps=(`grep  "chain.*itp" $top_out | awk '{print $NF}' | awk -F  \" '{print $2}'`)
for itp in ${chain_itps[@]}; do
    # sed r command appends the itp file after the matching include statement
    sed -i "/^ *\#include *\"$itp/r  $itp" ${top_out};

    # delete the include statement
    sed  -i "s/^ *\#include *\"$itp.*//g"  ${top_out};
done

# Modify the forcefield entry to not expect a force field in the current directory
sed -i "s/.\/${forcefield}/${forcefield}/" ${nonperiodic}.top

gro_out="conf.gro"
mv ${nonperiodic}.gro $gro_out

# Clean up
ls  | grep -v "$gro_out" | grep -v "$top_out" | xargs -n 1 rm -rf
#rm -rf \#* $tmp_log $top_work posre*itp tmp.* $pdb_work ./${forcefield}.ff extra*.* ${nonperiodic}*.* periodic*chain*.itp
