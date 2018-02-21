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

# TODO: put into a separate script
def absolute_path(path):
    stdout = run_in_shell('readlink -f ' + path)
    return stdout

def mdfiles(keyvalue):
    try:
        key, value = keyvalue.split('=')
    except:
        raise argparse.ArgumentTypeError('use "key=value" format')

    allowed_keys={'params', 'paramgrps', 'nreplicas', 'nmultisim', 'name'}
    if not key in allowed_keys:
        raise argparse.ArgumentTypeError(key + " is not a recognized key")

    filetypes={'params':'mdp', 'paramgrps':'.txt'}        
    othertypes={'nreplicas':int, 'nmultisim':int}

    if key in filetypes:
        if not key.endswith(keyfiletypes[key]):
            raise argparse.ArgumentTypeError("Value for " + key + " needs to be file of type " + keyfiletypes[key])

    # mdp, groupdefs, 
    return value
#--------------------------------------------
# Main function
#--------------------------------------------

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Sets up the MD simulations of periodically connected DNA chains. \
    Generates run directories for equilibration.")


    required_args = parser.add_argument_group(title='Required')
    required_args.add_argument('-p', '--params', dest='mdp', type=str, required=False, help="MD parameter file (.mdp)", nargs='+')
    required_args.add_argument('-c', '--config', dest='gro', type=str, required=False, help="configuration (.gro) files", nargs='+')
    required_args.add_argument('-t', '--top', dest='top', type=str, required=False, help="topology (.top) files", nargs='+')

    # Positional args

    #    parser.add_argument(dest='mdpfile', nargs = '+', type=str, help="list of pdb-files (.pdb) (the system name will be inferred from the filename)")
    #parser.add_argument(dest='pdbfiles', nargs = '+', type=str, help="list of pdb-files (.pdb) (the system name will be inferred from the filename)")

    # Optional args
    parser.add_argument('-f', dest='force', action='store_true', help="force overwriting of old output")
    parser.add_argument('-o', '--out', dest='outdir', type=str, default='build',
                        help='name of output directory to create')
    parser.add_argument("--gmx", dest='gmx', type=str, help="gmx binary to use")
    #parser.add_argument('-f', dest='force', action='store_true', help="force overwriting of old output")
    #parser.add_argument('-o', '--out', dest='outdir', type=str, default='build',
    #                        help='name of output directory to create')

    #parser.add_argument(dest='pdbfiles', nargs = '+', type=str, help="list of pdb-files (.pdb) (the system name will be inferred from the filename)")

    #condreq_args.add_argument('-p', dest='mdps', type=str, nargs='+',
    #                          help='parameter files (.mdp)', required=True)



    allowed_keys={'params', 'paramgrps', 'nreplicas', 'nmultisim', 'name'}

    keytypes={'params':'.mdp', 'paramgrps':'.txt', 'nreplicas':'int', 'nmultisim':'int', 'name':'str'}

    def keyvalue(keyvalue):
        try:
            key, value = keyvalue.split('=')
        except:
            raise argparse.ArgumentTypeError('use "key=value" format')
    
        #allowed_keys={'params', 'paramgrps', 'nreplicas', 'nmultisim', 'name'}
        if not key in allowed_keys:
            raise argparse.ArgumentTypeError(key + " is not a recognized key")
    
    
        if key in keytypes:
            if not key.endswith(keytypes[key]):
                raise argparse.ArgumentTypeError("Value for " + key + " needs to be file of type " + keytypes[key])
    
        # mdp, groupdefs, 
        return value
    
    parser.add_argument('--run', dest='run', action='append', 
                        help="defines a run using 'key=value' format. "
                        "Allowed keys: " +  ', '.join([k + '=<' + str(v) + '>' for k,v in keytypes.items()]),
                        type=keyvalue, nargs='+')

    parsed_args = parser.parse_args()

    run=parsed_args.run
    print run

    top = parsed_args.top
    gro= parsed_args.gro
    mdp = parsed_args.mdp
    outdir = parsed_args.outdir
    forceful = parsed_args.force


    sys.exit()
    # Each run requires a (top, gro) pair.
    # If there is only one mdp file given, it is used for all runs.
    if len(gro) != len(top):
        sys.exit("The number of given configuration (.gro) and topology (.top) files need to be equal.")
    if len(mdp) > 1 and len(mdp) != len(gro): 
        sys.exit("The number of given parameter (.mdp) files need to be either one or one for each topology/configuration file (.top/.gro).")
    if len(mdp) == 1:
        mdp = mdp*len(gro)

    outdir = absolute_path(outdir)
    if os.path.exists(outdir) and not forceful:
        sys.exit(outdir + ' already exists. Use -f to force overwrite.')

    for mdp, top, gro in zip(mdp, top, gro):
        print i
        outpath='/'.join([outdir, name, 'setup'])    

    # This script has dependencies on shell scripts.
    # For now, assume all scripts are in the same directory as this script
    # and make use an environment variable. Not sure how this should be done most
    # elegantly...
    scriptsdir=absolute_path(run_in_shell('dirname ' + os.path.realpath(__file__)))
    os.putenv('SETUP_MD_SCRIPTS', scriptsdir)
