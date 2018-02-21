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
import subprocess

# ======================================================
#
# FUNCTIONS
# ======================================================

# XXXXXXX
#---------------------------------------------------------
# Description:
# YYYYYYYYY
#
def run_in_shell(command):
    ##
    #    print command.split()
    proc = subprocess.Popen((command).split(), preexec_fn=os.setsid, close_fds = True,
                            stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    stdout, stderr = proc.communicate()

    if proc.returncode != 0:
        sys.exit("Failed to execute command: " + command)

    return stdout.strip()


#--------------------------------------------
# Main function
#--------------------------------------------

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Sets up the MD simulations of periodically connected DNA chains. \
    Generates the gromacs input files generates run directories for equilibration.")

    # Positional args
    #parser.add_argument('filename', type=str, nargs='+', help='data file to plot')
    parser.add_argument(dest='pdbfiles', nargs = '+', type=str, help="list of pdb-files")

    # Optional args
    parser.add_argument("--gmx", dest='gmx', type=str, help="gmx binary to use")
    parser.add_argument('-f', dest='force', action='store_true', help="force overwriting of old output")

    parsed_args = parser.parse_args()

    pdbs = parsed_args.pdbfiles
    forceful = parsed_args.force

    # This script has dependencies e.g. on shell scripts.
    # Assume all scripts are in the same directory as this script.
    scriptsdir=run_in_shell('dirname ' + os.path.realpath(__file__))
    scriptsdir=run_in_shell('readlink -f ' + scriptsdir)
    os.putenv('SETUP_MD_SCRIPTS', scriptsdir)

    # Check existence of input files and types
    for pdb in pdbs:
        filetype=pdb.split('/')[-1].split('.')[-1]
        if not os.path.exists(pdb):
            sys.exit(pdb + ": pdb does not exist")
        if filetype != 'pdb':
            sys.exit(pdb + ' does not look like a .pdb file')

    pdbs=[ run_in_shell('readlink -f ' + pdb) for pdb in pdbs]

    outdir ='./build'
    outdir=run_in_shell('readlink -f ' + outdir)
    if os.path.exists(outdir) and not forceful:
        sys.exit(outdir + ' already exists. Use -f to force overwrite.')
    else:
        run_in_shell('rm -rf ' + outdir)

    for pdb in pdbs:
        name  = pdb.split('/')[-1].split('.pdb')[-2]
        if len(name) == 0:
            sys.exit('Give ' + pdb + ' an non-empty descriptive name')

        pdbpath = run_in_shell('readlink -f ' + pdb)
        outpath='/'.join([outdir, name, 'equil'])    
        run_in_shell('mkdir -p ' + outpath)
        os.chdir(outpath)
        script='/'.join([scriptsdir, "gmx-equil-setup.sh"])
        command=' '.join([script, pdb])
        stdout=run_in_shell(command)
