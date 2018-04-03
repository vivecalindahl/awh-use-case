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
from random import randint

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
    if command.count('|') >= 1:
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
    ##print stderr.strip()

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

def absolute_path(path):
    stdout = run_in_shell('readlink -f ' + path)
    return stdout

def clone_directory(srcdir, outdir):
    contents=' '.join(['/'.join([srcdir,item]) for item in os.listdir(srcdir)])
    run_in_shell('mkdir -p ' + outdir)
    run_in_shell(' '.join(['cp -r', contents, outdir]))


def make_tpr(templatedir, nomdp=False, indexfile=False, out='topol.tpr'):

    # Work in a temporary directory.
    startdir=absolute_path(os.getcwd())
    templatedir=absolute_path(templatedir)
    workdir='./_tmpdir' + str(randint(1,1e4))
    clone_directory(templatedir, workdir)
    os.chdir(workdir)

    if nomdp:
        run_in_shell('touch grompp.mdp')

    extra_args=''   
    if indexfile:
        extra_args += ' -n'

    # Allow warnings but print if there were some.
    grompp = ' '.join(['gmx grompp', extra_args])
    stdout, stderr, error = run_in_shell_allow_error(grompp)
    if error:
        extra_args += ' -maxwarn 10'
        grompp = ' '.join(['gmx grompp', extra_args])
        stdout = run_in_shell(grompp)
        print("'gmx grompp' generated warnings for " + templatedir)

    # Only keep the tpr-file
    run_in_shell('mv topol.tpr ' + startdir + '/' + out)
    os.chdir(startdir)
    run_in_shell('rm -r ' + workdir)
    
def concatenate_files(filenames, outfilename):
    with open(outfilename, 'w') as outfile:
        for fname in filenames:
            with open(fname) as infile:
                for line in infile:
                    outfile.write(line)

def make_index_file_from_selections(tpr, selections):
    # If grompp gets a custom index file it will be unaware about the 
    # otherwise generated default groups, e.g. "system", which are
    # generally needed e.g. to specify the  temperature coupling groups.
    # So, generate a default index file first, then add the actual selections.

    defaults='defaults.ndx'
    run_in_shell_piped('echo -e "q" | gmx make_ndx -n ' + defaults + ' -f ' +  tpr)

    selected='selected.ndx'
    run_in_shell(' '.join(['gmx select','-s', tpr, '-sf', selections, '-on', selected]))

    concatenate_files([defaults, selected], 'index.ndx')

    run_in_shell(' '.join(['rm', defaults, selected]))

def make_run_template(setup, runspecs, template):
    clone_directory(setup, template)
    run_in_shell(' '.join(['cp', runspecs['params'], template + '/grompp.mdp']))
    tpr = template + '/topol.tpr'

    # Generate an index file from the selections, if given. 
    if 'selections' in runspecs:
        selections = runspecs['selections']
        make_index_file_from_selections(setup + '/' + tpr, selections)

    # The ultimate test: is it possible to make a tpr from this?
    make_tpr(template, indexfile = ('selections' in runspecs))

def build_system_shell(cmd_list):
    for cmd in cmd_list:
        run_in_shell(cmd)

    # System should now be ready. Bundle into a tpr-file
    make_tpr(setup, nomdp=True) 

def check_path_is_clean(path, forceful=False):
    if os.path.exists(path) and not forceful:
        sys.exit(path + ' already exists. Use -f to force overwrite.')
    else:
        run_in_shell('rm -rf ' + path)        

#--------------------------------------------
# Main function
#--------------------------------------------

if __name__ == "__main__":

    # -----------------------------------------------------------------------------------------------------------------------------
    # Define input arguments and parse them

    parser = argparse.ArgumentParser(description="")

    parser.add_argument('--build', dest='build_cmds', type=str, nargs='+', help='List of shell commands that should output a .gro and .tpr file.')
    parser.add_argument('--setup', type=str, default='./setup', help="Template directory containing system setup (conf.gro, topol.top).\
    Either exists or generate with '--build'.")

    parser.add_argument('--ffdir', dest='ffdir', type=str, help='external force field directory if needed')
    parser.add_argument('-f', dest='force', action='store_true', help="force overwriting of old output if needed")

    # Defines a keyvalue argument type for the parser
    # This should probably be an input file instead.
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

    # Parse and fetch arguments.
    parsed_args = parser.parse_args()

    forceful = parsed_args.force
    ffdir=parsed_args.ffdir
    runspecs_list = parsed_args.runs
    build_cmds = parsed_args.build_cmds
    setup = parsed_args.setup

    # Turn the run key-value arguments into a dictionary.
    if runspecs_list:
        runspecs_list=[{k:v for k, v in runspecs} for runspecs in runspecs_list]
    else:
        runspecs_list=[]

    # -----------------------------------------------------------------------------------------------------------------------------
    # Check existence of input files and types
    # Turn any relative paths into absolute ones.

    if ffdir:
        ffdir = absolute_path(ffdir)

    # Check the given run parameters
    for runspecs in runspecs_list:                        
        if 'params' not in runspecs:
            sys.exit("give all runs a parameter (.mdp) file")
        runspecs['params'] = absolute_path(runspecs['params'])

        if 'selections' in runspecs:
            runspecs['selections'] = absolute_path(runspecs['selections'])
        if 'name' not in runspecs:
            sys.exit("give all runs names")

    build_system = build_cmds and len(build_cmds) > 0
    if build_system and not os.path.exists(setup):
        sys.exit("Instructions for building the system (see '--build') not given and the system setup path (see '--setup') does not exist." )
    setup = absolute_path('./setup')

    # -----------------------------------------------------------------------------------------------------------------------------
    # Here actually do something

    if build_system:
        check_path_is_clean(setup, forceful=forceful)
        run_in_shell('mkdir -p ' + setup)

        if ffdir:
            run_in_shell('cp -r ' + ffdir + ' ' + setup)

        startdir=os.getcwd()
        os.chdir(setup)
        print "Building system in directory " + setup
        build_system_shell(build_cmds)
        os.chdir(startdir)

    # Generate the run directories
    for runspecs in runspecs_list:                    
        runpath=runspecs['name']
        check_path_is_clean(runpath, forceful=forceful)
        
        # Prepare a template run directory with the files needed for making a .tpr file.
        template='/'.join([runpath, 'template'])
        make_run_template(setup, runspecs, template)
                
# TODOs:
# dump info/log files with command line for generating the build
