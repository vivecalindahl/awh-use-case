#!/bin/bash

# COMMANDLINE ARGS
# ======================================================================

nargsmin=3
if [ $# -lt $nargsmin ] || [ "$1" == "-h" ]; then
    echo "Usage: $0 <gmx binary>  <base resid> <partner resid>" 
    #echo "$0  `which gmx` 11 28"
    exit 0
fi

gmx=$1
shift
base=$1
shift
partner=$1
shift

# INPUT
# ======================================================================
tpr='topol.tpr'
dihedraldef='dihedral-def.txt'

# OUTPUT
# ======================================================================
ndxout="dihedral.ndx"

# ======================================================================

# Id increase from 5' to 3' along strand.
base_up=$((base + 1))
base_down=$((base - 1))

# Ids on opposite strands increases in opposite direction
partner_up=$((partner - 1))
partner_down=$((partner + 1))

selection="\
base = resid $base; \
partner = resid $partner;\
base_up = resid $base_up;\
base_down = resid $base_down;\
partner_up = resid $partner_up;\
partner_down = resid $partner_down;" 

# Save the input
echo "${selection}" > dihedral-selection.dat
gmx  select  -select "${selection}" -sf ${dihedraldef} -s $tpr -on $ndxout
