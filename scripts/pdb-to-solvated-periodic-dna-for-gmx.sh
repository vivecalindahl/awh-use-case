#!/bin/bash

# input
gmx=gmx # asumme available for now

gro_in="./conf.gro"
top_in="./topol.top"
gro_in=`readlink -e $gro_in`
top_in=`readlink -e $top_in`

# Solvate in the more general sense of taking a solute molecule and putting it in a box of solvent (water)
# with ions of a given concentration.

# Use periodic boundary conditions with 
# unit cell defined by the box vectors a, b, c. 
# For DNA periodically connected along z use
# one box vector parallel to z (c) and the
# put the other two (a,b) in the xy-plane with
# with a relative angle 60 deg.
# ==> box vector angles:
bc=90
ac=90
ab=60
boxangles=($bc $ac $ab)
# z box vector from diameter along z
# xy box vectors from  average/max diameter along x (~circle in the xy plane) . Add 1 nm * 2 to have 1 nm to box edge.

# Molecule dimaeter along each dimension: d = (max - min)
# gro file has xyz values in  cols 4, 5, 6
dxyz=( `for i in 4 5 6 ;  
do awk -v col=$i 'BEGIN{zmin=100; zmax=-100;}{while(NR <= 2){getline}; z=$col; if (NF==3){exit}; if(z > zmax){zmax=z}; if(z < zmin){zmin=z;}}END{print zmax-zmin}' $gro_in ;done`
)

# Dna is roughly circular in x, y. Use dx as diameter and add 2 nm
# to ensure that periodic images are ~ 2 nm apart.
boxx=`awk -v dx=${dxyz[0]} 'BEGIN{print dx+2.0}'`
boxy=$boxx
boxz=${dxyz[2]}
boxvectors=($boxx $boxy $boxz)

# Make a box
box_gro="boxed.gro"

echo "Solvating the DNA and adding ions."
$gmx editconf -f $gro_in -angles ${boxangles[@]} -box ${boxvectors[@]} -c -o $box_gro &> "boxed.log"

# Put water in the box with the solute
cp $top_in solvated.top
gmx solvate -cp "boxed.gro"  -cs -o "solvated.gro"  -p "solvated.top" &> "solvated.log"


dummy="tmp"
touch "${dummy}.mdp";
gmx grompp -f "${dummy}.mdp" -c "solvated.gro" -p "solvated.top"  -o "${dummy}.tpr" &> "${dummy}.log"

cp "solvated.top" "ionated.top";

echo -e "SOL\n" | gmx genion -s "${dummy}.tpr" -neutral -pname  NA -o "ionated.gro"  -p "ionated.top" &> "ionated.log"

conf_out="conf.gro"
top_out="topol.top"
mv ionated.gro conf.gro
mv ionated.top topol.top
rm boxed.* mdout.mdp solvated.* ionated.log
rm "${dummy}".*
rm \#* 

echo "Final configuration and topology files saved as: ${conf_out} and ${top_out}."
