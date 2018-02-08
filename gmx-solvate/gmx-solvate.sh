#!/bin/bash

gro_in=$1

# input
gmx=gmx

# Solvate in the more general sense of taking a solute molecul and putting it in a box of solvent (water)
# with ions of a given concentration.
boxtype="dodecahedron"
#boxtype="triclinic"
soluteboxdistance=1
tmp_gro="tmp.gro"

# box vectors a, b, c. 
# dna is (assumed to be) z aligned (TODO: add alignment step)
# so periodic chain ==> 
# c = z, and
# a = x by gmx convention.
# b
# ==> angle ac = 90 deg.
# box vector angles:
bc=90
ac=90
ab=60

# z box vector from diameter along z
# xy box vectors from  average/max diameter along x and  y. Add 1 nm * 2 to have 1 nm to box edge.
d=0; for i in 4 5; d=`awk -v col=$i 'BEGIN{zmin=100; zmax=-100;}{while(NR <= 2){getline}; z=$col; if (NF==3){exit}; if(z > zmax){zmax=z}; if(z < zmin){zmin=z;}}END{print zmax-zmin}' conf.gro`; done
# Make a box
$gmx editconf -f $gro_in -angles $bc $ac $ab -box  $((xylen+1)) $xylen  3.95500 -c -o $tmp_gro

# Put water in the box


