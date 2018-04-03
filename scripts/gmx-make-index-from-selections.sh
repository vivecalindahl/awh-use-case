#!/bin/bash

# input
selections=$1
tpr=$2

# Run directory (files need to generate a tpr)
# Default gmx file names assumed.
templatedir=$2

# Output
ndx="index.ndx"

# Work in temporary folder
start=$(pwd -P)
#workdir="_tmp-${RANDOM}"
#cd $workdir

# Make a dummy run input file (.tpr) that might be needed for generating an index file 
# from the selections (a dummy mdp-file has to be used because the real one may depend
# on the index file, which we haven't generated yet).
#touch grompp.mdp
#gmx grompp -maxwarn 10


# Evaluate the selections. Output is an index file with the selected groups.
# gmx select requires tpr-file as input.

# If grompp gets a custom index file it will be unaware about the 
# otherwise generated default groups, e.g. "system", which are
# generally needed e.g. to specify the  temperature coupling groups.
# So, generate a default index file first, then add the actual selections.
echo -e "q" | gmx make_ndx -f $tpr -o $ndx

# add selected groups last
selected="selected.ndx"
gmx select -s $tpr -on  $selected -sf $selections
cat $selected >> $ndx

#mv $ndx ${start} 

# the output index is now ready.
