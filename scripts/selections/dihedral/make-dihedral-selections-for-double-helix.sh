#!/bin/bash

# Generate all the dihedral selections for a double helix, 
# i.e. two paired DNA chains of equal lengths N.
# given the minimum and the maximum residue and a template file with the dihedral definition.
# Assumes that the residues of the two chains are indexed and paired as:
#
# 1    --   2N
# 2    --   2N-1
#     [..]  
# n    --   2N+1-n     
#     [..] 	 
# N-1  --   N+2
# N    --   N+1
#
# Chain end residues are ignored.

nargsmin=1
if [ $# -lt $nargsmin ] || [ "$1" == "-h" ]; then
    echo "Usage: $0  <chain length>" 
    echo "Example:"
    echo "$0 11"
    exit 0
fi

N=$1
shift
template=$1
shift

# Now assume helper script should be in the same directory as the called script
scriptsdir=$(dirname $(readlink -f $0))
make_selection="${scriptsdir}/make-dihedral-selection.sh"
template="${scriptsdir}/dihedral-selection-template.txt"

[ ! -x "$make_selection" ] && { echo "Not found $make_selection"; exit 1; }
[ ! -e "$template" ] && { echo "Not found $template"; exit 1; }

# Generate the non-termini pairs
for ((n=2; n<$N; n++)); do
    prefix="dihedral-selections"

    n1=$n; 
    n2=$((2*N+1-n))
    out=./${prefix}-${n1}-${n2}.txt
    $make_selection $n1 $n2 $template > $out
    echo $out    

    n1=$n2
    n2=$n
    out=./${prefix}-${n1}-${n2}.txt
    $make_selection $n1 $n2 $template > $out
    echo $out
done

