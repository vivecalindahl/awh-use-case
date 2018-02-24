#!/bin/bash

# input
selections=$1

gro="conf.gro"

# Make a dummy run input file (.tpr) that might be needed for generating an index file 
# from the selections (a dummy mdp-file has to be used because the real one may depend
# on the index file, which we haven't generated yet).
touch empty.mdp
tpr="topol.tpr"
gmx grompp -c $gro -f empty.mdp -maxwarn 10 -o $tpr


# Evaluate the selections. Output is an index file with the selected groups.
# gmx select requires tpr-file as input.

# If grompp gets a custom index file it will forget about the default groups, 
# so need to generate a default to add first.
ndx="index.ndx"
echo -e "q" | gmx make_ndx -f $gro  -o $ndx


# add selected groups last
selected="selected.ndx"
gmx select -s $tpr -on  $selected -sf $selections
cat $selected >> $ndx

# the output index is now ready.
