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
    if command.count('|') > 1:
        return run_in_shell_piped(command)

    proc = subprocess.Popen((command).split(), preexec_fn=os.setsid, close_fds = True,
                            stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    stdout, stderr = proc.communicate()
    stdout = stdout.strip()

    error = proc.returncode != 0
    if error:
        print stdout, stderr
        sys.exit("Failed to execute command: " + command + 
                 " (in: " + os.getcwd() + ")")

    return stdout

def run_in_shell_piped(command):
    commands = command.split('|') # this could fail

    # Chain piped commands together
    prev_proc = None;
    proc_piped=[]

    for c in commands:
        prev_stdout = None
        if prev_proc != None:
            prev_stdout = prev_proc.stdout

        proc = subprocess.Popen(c.split(), preexec_fn=os.setsid, close_fds = True,
                                           stdout = subprocess.PIPE, stderr= subprocess.PIPE,
                                           stdin = prev_stdout)
        proc_piped.append(proc)
        prev_proc = proc

    stdout, stderr = proc_piped[-1].communicate()
    stdout = stdout.strip()

    error = proc.returncode != 0
    if error:
        sys.exit("Failed to execute command: " + command)

    return stdout

def run_in_shell_allow_error(command):
    proc = subprocess.Popen((command).split(), preexec_fn=os.setsid, close_fds = True,
                            stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    stdout, stderr = proc.communicate()
    stdout = stdout.strip()

    error = proc.returncode != 0

    return stdout, stderr, error

# TODO: put into a separate script
def absolute_path(path):
    stdout = run_in_shell('readlink -f ' + path)
    return stdout

#--------------------------------------------
# Main function
#--------------------------------------------

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Sets up the MD simulations of periodically connected DNA chains. \
    Generates run directories for equilibration.")

    parser.add_argument(dest='pdbfiles', nargs = '+', type=str, help="list of pdb-files (.pdb) (the system name will be inferred from the filename)")

    # Optional args
    parser.add_argument('-f', dest='force', action='store_true', help="force overwriting of old output")
    parser.add_argument('-o', '--out', dest='outdir', type=str, default='build',
                        help='name of output directory to create')
    parser.add_argument('-ff', '--forcefield', dest='forcefield', type=str, choices=['amber99bsc1', 'charmm27'])
    parser.add_argument('--ffdir', dest='ffdir', type=str)
    ##parser.add_argument("--gmx", dest='gmx', type=str, help="gmx binary to use") # TODO

    # Defines a keyvalue argument type for the parser
    allowed_types={'name':'str', 'params':'.mdp', 'selections':'.txt'}
    def keyvalue(keyvalue):
        try:
            # value is a string
            key, value = keyvalue.split('=')
        except:
            raise argparse.ArgumentTypeError('use "key=value" format')
    
        if not key in allowed_types:
            raise argparse.ArgumentTypeError(key + " is not a recognized key")        

        # Check that value strings are consistent with their key and convert to
        # the right non-string type if needed.
        valuetype = allowed_types[key]
        if valuetype.startswith('.'):
            #  value is a file
            #  should should have the right filename extension
            if not value.endswith(valuetype):
                raise argparse.ArgumentTypeError("Value for " + key + " needs to be file of type '" + valuetype + "'")
        else:
            # value is number or string
            # try converting to the right type                            
            try:
                value=eval(valuetype)(value)
            except:
                raise argparse.ArgumentTypeError(value + ' is not of the right type (' + valuetype + ')')

        return [key,value]

    parser.add_argument('--run', '-r', dest='runs', action='append', 
                        help="defines a run using 'key=value' format. "
                        "Allowed keys: " +  ', '.join([k + '=<' + str(v) + '>' for k,v in allowed_types.items()]),
                        type=keyvalue, nargs='+')

    parsed_args = parser.parse_args()

    pdbs = parsed_args.pdbfiles
    outdir = parsed_args.outdir
    forceful = parsed_args.force
    forcefield=parsed_args.forcefield
    ffdir=parsed_args.ffdir

    runs = parsed_args.runs

    if runs:
        runs=[{k:v for k, v in run} for run in runs]
    else:
        runs=[]

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

    if ffdir:
        ffdir = absolute_path(ffdir)

    for run in runs:                        
        if 'params' in run:
            run['params'] = absolute_path(run['params'])
        if 'selections' in run:
            run['selections'] = absolute_path(run['selections'])

    if os.path.exists(outdir) and not forceful:
        sys.exit(outdir + ' already exists. Use -f to force overwrite.')
    else:
        run_in_shell('rm -rf ' + outdir)

    run_in_shell('mkdir -p ' + outdir)
    outdir = absolute_path(outdir)

    for pdb in pdbs:
        name  = pdb.split('/')[-1].split('.pdb')[-2]
        if len(name) == 0:
            sys.exit('Give ' + pdb + ' a non-empty descriptive name')

        setup='/'.join([outdir, name, 'setup'])    
        run_in_shell('mkdir -p ' + setup)

        if ffdir:
            run_in_shell('cp -r ' + ffdir + ' ' + setup)

        os.chdir(setup)

        print "Setting up system " + name + " in " + setup

        stdout=run_in_shell(scriptsdir + '/pdb-to-solvated-periodic-dna-for-gmx.sh ' + pdb + ' ' + forcefield)

        topology = setup + '/topol.top'
        config = setup + '/conf.gro'

        for run in runs:
            if 'name' in run:
                runid=run['name']
            else:
                sys.exit("give all runs names")

            print 'Adding ' + runid

            runpath='/'.join([outdir, name, runid])

            template='/'.join([runpath, 'template'])
            run_in_shell('mkdir -p ' + template)

            # copy the files needed
            params=run['params']
            for runfile, defaultname in zip([config, topology, params], ['conf.gro', 'topol.top', 'grompp.mdp']):
                shutil.copy(runfile, template + '/' + defaultname)
            if ffdir:
                run_in_shell('cp -r ' + ffdir + ' ' + template)

                # Generate an index file from the selections
            if 'selections' in run:
                selections = run['selections']
                tmp='/'.join([runpath, 'tmp'])
                run_in_shell('cp -r ' + template + ' ' + tmp)
                os.chdir(tmp)                                    
                stdout = run_in_shell(scriptsdir + '/selections-to-index-file.sh ' + selections)                                      
                run_in_shell("cp ./index.ndx " + template)
                run_in_shell('rm -r ' + tmp)

            # Test if we are now able to generate a run file with errors.
            tmp='/'.join([runpath, 'tmp'])
            run_in_shell('cp -r ' + template + ' ' + tmp)
            os.chdir(tmp)
            grompp = 'gmx grompp'
            if 'selections' in run:
                grompp += ' -n'
            stdout, stderr, error = run_in_shell_allow_error(grompp)
            if error:
                stdout = run_in_shell(grompp + ' -maxwarn 10')
                print("'" + grompp + "'" + " generated warnings")

            run_in_shell('rm -r ' + tmp)
                
