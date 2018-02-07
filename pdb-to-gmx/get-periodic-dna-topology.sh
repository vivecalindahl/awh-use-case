#!/bin/bash

gmx="gmx"
pdb_in="GCGCTTTCGCG.pdb" # whichever dna pdb
# --

# Generate a two-residue topology and extract the necessary couplings from there
pdb_work="two-res.pdb"
awk '/ATOM/{pdb_resid_col=6; if(resid != $pdb_resid_col){nresid+=1}; if (nresid <= 2){resid=$pdb_resid_col; print}}/END/{print}' $pdb_in > $pdb_work

##pdb2gmx_args="-f $pdb_work   -merge all  -ter -o -p  -ff charmm27-mod -water tip3p"
pdb2gmx_args="-f $pdb_work   -merge all  -ter -o -p  -ff charmm27-mod -water tip3p"

# Dummy-run pdb2gmx (choosing termini indexed by 0 and 0) to figure out what the real indices of the termini we want to select are.
echo -e "0 \n 0" | $gmx pdb2gmx  $pdb2gmx_args  &> tmp.log

# The pdb2gmx interactive session will list indices in the format "<index>: <ter>".
## We want ter=5' and ter=3'. 
# We want ter=hack and ter=none. 

#tersel=`awk 'BEGIN{prime_char="\47"} /Select start/{sel="5"prime_char; getline; while(sel != $2){getline}; print $1};
#/Select end/{sel="3"prime_char; getline; while(sel != $2){getline}; print $1}' tmp.log  | awk -F ":" '{print $1}'`
tersel=`awk 'BEGIN{prime_char="\47"} /Select start/{sel="hack"; getline; while(sel != $2){getline}; print $1};
/Select end/{sel="None"; getline; while(sel != $2){getline}; print $1}' tmp.log  | awk -F ":" '{print $1}'`
tersel=($tersel)
[ ${#tersel[@]} -ne 2 ] && { echo "Should have got 2 ter indices. Have indices: ${tersel[@]}"; exit 1; }
echo -e "${tersel[0]} \n ${tersel[1]}" | $gmx pdb2gmx $pdb2gmx_args &> tmp-pdb2gmx.log

# first atom in 2nd residue
gro="conf.gro"
cut=`awk 'BEGIN{gro_header_size=2}; /^ *2/{if(NR > gro_header_size){print $3 ; exit;}}' $gro`

# TODO: remove some hardcoding in the below extraction

all_mixed="topol-mixed.dat"
# [ dihedrals ] mixed entries, i.e. atoms from both residues
awk '/\[ /{if ($2 == "dihedrals"){start=1; next}else{start=0}}{if (start && $1 != ";" && NF==5){print};}' \
topol.top  > topol-dih.dat
awk -v cut=$cut '{hasup=0; hasdown=0;for (i=1; i<= 4; i++){if($i < cut){hasup=1}else{hasdown=1}} if(hasup && hasdown){print}}' \
topol-dih.dat > topol-dih-mixed.dat
rm topol-dih.dat

# [ pairs ] mixed entries
awk '/\[ /{if ($2 == "pairs"){start=1; next}else{start=0}}{if (start && $1 != ";" && NF==3){print};}' \
topol.top  > topol-pairs.dat
awk -v cut=$cut '{hasup=0; hasdown=0;for (i=1; i<=2; i++){if($i < cut){hasup=1}else{hasdown=1}} if(hasup && hasdown){print}}' \
topol-pairs.dat > topol-pairs-mixed.dat
rm topol-pairs.dat

# [ bonds ] mixed entries
awk '/\[ /{if ($2 == "bonds"){start=1; next}else{start=0}}{if (start && $1 != ";" && NF==3){print};}' \
topol.top  > topol-bonds.dat
awk -v cut=$cut '{hasup=0; hasdown=0;for (i=1; i<=2; i++){if($i < cut){hasup=1}else{hasdown=1}} if(hasup && hasdown){print}}' \
topol-bonds.dat > topol-bonds-mixed.dat
rm topol-bonds.dat

# [ angles ] mixed entries
awk '/\[ /{if ($2 == "angles"){start=1; next}else{start=0}}{if (start && $1 != ";" && NF==4){print};}' \
topol.top  > topol-angles.dat
awk -v cut=$cut '{hasup=0; hasdown=0;for (i=1; i<=3; i++){if($i < cut){hasup=1}else{hasdown=1}} if(hasup && hasdown){print}}' \
topol-angles.dat > topol-angles-mixed.dat
rm topol-angles.dat

rm -rf $all_mixed
echo -e "[ bonds ]" >> $all_mixed
cat topol-bonds-mixed.dat >> $all_mixed
echo -e "[ angles ]" >> $all_mixed
cat topol-angles-mixed.dat >> $all_mixed
echo -e "[ dihedrals ]" >> $all_mixed
cat topol-dih-mixed.dat >> $all_mixed
echo -e "[ pairs ]" >> $all_mixed
cat topol-pairs-mixed.dat >> $all_mixed


gro_header_size=2; 
gro_footer_size=1; 
end=$((`wc -l conf.gro | awk '{print $1}'` - gro_footer_size)); 
awk -v start=$((gro_header_size+1)) -v end=$end '{if(NR >= start && NR <= end){print $3, substr($1, 0, 1), $2}}' conf.gro > index-to-res-and-name-table.dat
#... 
#pdb2gmx_args="-f $pdb_in -merge all  -ter -o -p  -ff charmm27 -water tip3p"
#echo -e "${tersel[0]} \n ${tersel[1]}" | $gmx pdb2gmx $pdb2gmx_args
