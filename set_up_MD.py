#! /usr/bin/env python2.7

# ======================================================
#
# IMPORTS
# ======================================================


# Execute global startup script
import os

startup = os.environ.get("PYTHONSTARTUP")
if startup and os.path.isfile(startup):
    execfile(startup)

import argparse

# ======================================================
#
# FUNCTIONS
# ======================================================

# Plot 2d function data
#---------------------------------------------------------
# Description:
#
#

def test_do():
    print "doing stuff"

#--------------------------------------------
# Main function
#--------------------------------------------

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Sets up the MD simulations of periodically connected DNA chains. \
    Generates the gromacs input files generates run directories for equilibration.")

    # Positional args
    #parser.add_argument('filename', type=str, nargs='+', help='data file to plot')

    # Optional args
    parser.add_argument("--pdbs", nargs = '+', type=str, help="list of pdb-files")

    parsed_args = parser.parse_args()

    pdbs = parsed_args.pdbs

    for pdb in pdbs: 
        print "got " + pdb
    test_do()
