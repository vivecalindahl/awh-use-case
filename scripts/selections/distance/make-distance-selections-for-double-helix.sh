#!/bin/bash

# Generate all the distance selections for a double helix, 
# i.e. two paired DNA chains of equal lengths N.
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
make_selection="${scriptsdir}/make-distance-selection.sh"
template="${scriptsdir}/distance-selection-template.txt"

[ ! -x "$make_selection" ] && { echo "Not found $make_selection"; exit 1; }
[ ! -e "$template" ] && { echo "Not found $template"; exit 1; }

# Generate all  pairs
for ((n=1; n<=$N; n++)); do
    prefix="distance-selections"

    n1=$n; 
    n2=$((2*N+1-n))
    out=./${prefix}-length-${N}-resids-${n1}-${n2}.txt
    $make_selection $n1 $n2 $template > $out
    echo $out    
done

