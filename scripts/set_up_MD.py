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

def absolute_path(path):
    stdout = run_in_shell('readlink -f ' + path)
    return stdout


#--------------------------------------------
# Main function
#--------------------------------------------

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Sets up the MD simulations of periodically connected DNA chains. \
    Generates the gromacs input files generates run directories for equilibration.")

    #condreq_args = parser.add_argument_group(title='conditionally required')

    # Positional args
    parser.add_argument(dest='pdbfiles', nargs = '+', type=str, help="list of pdb-files (.pdb) (the system name will be inferred from the filename)")

    # Optional args
    parser.add_argument("--gmx", dest='gmx', type=str, help="gmx binary to use")
    parser.add_argument('-f', dest='force', action='store_true', help="force overwriting of old output")
    parser.add_argument('-o', '--out', dest='outdir', type=str, default='build',
                        help='name of output directory to create')

    #parser.add_argument(dest='pdbfiles', nargs = '+', type=str, help="list of pdb-files (.pdb) (the system name will be inferred from the filename)")

    #condreq_args.add_argument('-p', dest='mdps', type=str, nargs='+',
    #                          help='parameter files (.mdp)', required=True)

    parsed_args = parser.parse_args()
    pdbs = parsed_args.pdbfiles
    outdir = parsed_args.outdir
    forceful = parsed_args.force

    # This script has dependencies on shell scripts.
    # For now, assume all scripts are in the same directory as this script
    # and make use an environment variable. Not sure how this should be done most
    # elegantly...
    scriptsdir=absolute_path(run_in_shell('dirname ' + os.path.realpath(__file__)))
    os.putenv('SETUP_MD_SCRIPTS', scriptsdir)

    # Check existence of input files and types
    for pdb in pdbs:
        filetype=pdb.split('/')[-1].split('.')[-1]
        if not os.path.exists(pdb):
            sys.exit(pdb + ": pdb does not exist")
        if filetype != 'pdb':
            sys.exit(pdb + ' does not look like a .pdb file')

    pdbs=[ absolute_path(pdb) for pdb in pdbs]

    outdir = absolute_path(outdir)
    if os.path.exists(outdir) and not forceful:
        sys.exit(outdir + ' already exists. Use -f to force overwrite.')
    else:
        run_in_shell('rm -rf ' + outdir)

    for pdb in pdbs:
        name  = pdb.split('/')[-1].split('.pdb')[-2]
        if len(name) == 0:
            sys.exit('Give ' + pdb + ' an non-empty descriptive name')

        outpath='/'.join([outdir, name, 'setup'])    
        run_in_shell('mkdir -p ' + outpath)
        os.chdir(outpath)

        print "Setting up system " + name + " in " + outpath
        stdout=run_in_shell(scriptsdir + '/gmx-equil-setup.sh ' + pdb)
        print stdout
