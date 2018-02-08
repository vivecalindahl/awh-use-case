#!/bin/bash

# Generate gromacs top and gro files for DNA pdb files.

args=( "$@" )

function print_usage_exit
{
    echo "Usage: $0 [<.pdb>...]"
    exit 0
}

[ ${#args[@]} -eq 0 ] && { echo "No input arguments given." && print_usage_exit; }

for i in ${args[@]}; do 
    [[ $i =~ \.pdb$ ]] || \
	{ echo "Input \"$i\" does not end with .pdb." && print_usage_exit; }
done

pdbs=()
for i in ${args[@]}; do
    pdbs+=( `readlink -e $i` )
done

connect_dna=`readlink -e ./connect_dna.sh` # TODO put in script library

outdir="`pwd -P`/build"
rm -rf $outdir;
mkdir -p $outdir
cd $outdir
for pdb in ${pdbs[@]}; do 
    filename=`basename $pdb`
    name="${filename%.*}"
    echo $name

    mkdir $name
    cd $name
    echo "in `pwd -P`" 
    $connect_dna $pdb || { echo "There was a problem." && exit 1; }

    cd $outdir
done



