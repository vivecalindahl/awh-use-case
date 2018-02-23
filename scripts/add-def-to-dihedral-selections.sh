#!/bin/bash

# Add required variable definitions to beginning of template file for dihedral selections.

nargsmin=3
if [ $# -lt $nargsmin ] || [ "$1" == "-h" ]; then
    echo "Usage: $0  <base resid> <partner resid> <template>" 
    echo "Example:"
    echo "$0 2 10 dihedral-selection-template.txt > dihedral-selections-bp2-10.txt"
    exit 0
fi

base=$1
shift
partner=$1
shift
template=$1
shift

base_up=$((base + 1)); base_down=$((base - 1)); partner_up=$((partner - 1)); partner_down=$((partner + 1));
def="base=$base; partner=$partner; base_up=$base_up; base_down=$base_down; partner_up=$partner_up; partner_down=$partner_down;";
out=selection_bp${base}-${partner}.txt;
echo $def #> $out ;
cat $template  #>> selections-dihedral-template.txt  >> $out
