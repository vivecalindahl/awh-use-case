#! /usr/bin/env python2.7

#--------------------------------------------
# Description
#--------------------------------------------
# My python function help functions
#-------------------------------------------
import os
import time

# Execute global startup script (os needs to already be imported)
startup = os.environ.get("PYTHONSTARTUP")
if startup and os.path.isfile(startup):
    execfile(startup)

import inspect

DEBUG=False

#--------------------------------------------
# Function definitions
#--------------------------------------------
def get_default_args(func):
    args, varargs, keywords, defaults = inspect.getargspec(func)
    return dict(zip(reversed(args), reversed(defaults)))

# Check if directory exists and give error message if not
def exit_if_not_dir(path):
    if not os.path.isdir(path):
        sys.exit(path + ": not a directory")

# Check if file exists and give error message if not
def exit_if_not_file(path):
    if not os.path.isfile(path):
        sys.exit(path + ": not a file")

# Check if path exists and give error message if not
def exit_if_not_exists(path):
    if not os.path.exists(path):
        sys.exit(path + ": path does not exist")

# Return the path to a program
def which(program):
    # Is the path executable?
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    # Get the full program path and test it.
    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None
