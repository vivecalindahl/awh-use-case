#!/bin/bash

# Add required variable definitions to beginning of template file for distance selections.

nargsmin=3
if [ $# -lt $nargsmin ] || [ "$1" == "-h" ]; then
    echo "Usage: $0  <base resid> <partner resid> <template>" 
    echo "Example:"
    echo "$0 2 10 distance-selection-template.txt > distance-selections-bp2-10.txt"
    exit 0
fi

base=$1
partner=$2
template=$3

# The resids
base_up=$((base + 1)); base_down=$((base - 1)); partner_up=$((partner - 1)); partner_down=$((partner + 1));
# string with the selections needed to be added
def="base=resid $base;
partner=resid $partner;";

# spit it out
echo -e "# Definitions added by $(basename $0)"
echo -e $def "\n"
cat $template
