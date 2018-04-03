#! /usr/bin/env python2.7

import os, sys
import numpy as np

import build_runs as build_runs

# Globals variables
scriptsdir='/data/viveca/awh-use-case/scripts'
gmx='/data/viveca/gromacs/build-release-2018-debug-mpi/bin/gmx_mpi_debug'

def read_lines_in_file(inputfile):
    # first two lines: name string, number of atoms
    # last line the box vectors
    with open(inputfile) as f:
        lines=f.read().splitlines()

    return lines

# gro-file format info
gro_columns = {'residue':0, 'name':1, 'index':2,
               'x':3, 'y':4, 'z':5,
               'vx':6, 'vy':7, 'vz':8}
gro_header_size = 2
gro_footer_size = 1

def read_gro_coordinates(gro):
    lines = read_lines_in_file(gro);

    # Remove data headers.
    lines = lines[gro_header_size:-gro_footer_size]

    # Split strings with white space delimiter
    lines = [line.split() for line in lines]

    # Extract coordinates as numpy array
    cols = [gro_columns[coord] for coord  in ['x', 'y', 'z']]
    coords=[]
    for row in lines:
        xyz = []
        for col in cols:
            xyz.append(float(row[col]))
        coords.append(xyz)

    coords = np.array(coords)

    return coords

def make_box_for_periodic_dna(gro='conf.gro'):
    # Make a box for a DNA molecule that is periodically connected in the z-direction.

    # The box angles (naming as in gmx manual).
    # Here vectors a and b lie in the xy-plane, and are 60 deg apart. 
    # vector c is parallel to the z axis
    bc, ac, ab = 90, 90, 60

    # Very simple measure of the diameter along each dimension:
    coords = read_gro_coordinates(gro)
    diameter = coords.max(0) - coords.min(0)

    # Dna is roughly circular in x and y. Use the x diameter and add 2 nm
    # to ensure that periodic images are ~ 2 nm apart.

    a = diameter[0] + 2.0
    b = a

    # The z box length should equal the molecule length since we are making a
    # periodic molecule.
    c = diameter[-1]

    # Make the box with editconf
    angles = ' '.join([str(bc), str(ac), str(ab)])
    lengths =  ' '.join([str(a), str(b), str(c)])
    out='conf.gro'
    args = ' '.join(['-angles', angles, '-box', lengths, '-o', out])
    stdout = build_runs.run_in_shell(' '.join([gmx, 'editconf', args]))

def pdb2gmx_periodic(pdb, watermodel, forcefield):
    periodic_pdb2gmx=scriptsdir + '/gmx-pdb2gmx-wrapper-periodic-dna.sh'
    args=' '.join(['-water', watermodel, '-ff', forcefield, '-f', pdb])
    build_runs.run_in_shell(' '.join([periodic_pdb2gmx, args]))


def solvate_box(gro='conf.gro', top='topol.top', tpr='topol.tpr'):

    # Keep same file names, input files will be modified.
    args = ' '.join(['-cp', gro, '-p', top, '-cs','-o', 'conf.gro'])
    stdout = build_runs.run_in_shell(' '.join([gmx, 'solvate', args]))


def neutralize_box(gro='conf.gro', top='topol.top', tpr='topol.tpr'):
    args = ' '.join(['-neutral', '-pname', 'NA', '-p', 'topol.top', '-o', 'conf.gro'])
    interactive_args = 'SOL'
    cmd = ' '.join(['echo -e', interactive_args, '|', gmx, 'genion', args])

    stdout = build_runs.run_in_shell(cmd)

def remove_temporary_files():
    files = ' '.join([ f for f in os.listdir(os.getcwd())  if f.startswith('#') or f.endswith('~') ])
    build_runs.run_in_shell('rm ' + files)

def build_periodic_dna(pdb_path, watermodel='tip3p', forcefield='charmm27', make_clean=True):

    pdb2gmx_periodic(pdb_path, watermodel, forcefield)
    build_runs.make_tpr('.', nomdp=True)

    # Edit the box size and shape
    make_box_for_periodic_dna()

    # Add water to the box, requires a tpr file.
    build_runs.make_tpr('.', nomdp=True)
    solvate_box()

    # Neutralize system by adding ions
    build_runs.make_tpr('.', nomdp=True)
    neutralize_box()

    # Make a final tpr
    build_runs.make_tpr('.', nomdp=True)

    # Clean up
    if make_clean:
        remove_temporary_files()

# An example of how how one can set up a simulation experiment for the DNA system.
def build_dna_example(make_clean=False):
    pdb_dir = '/data/viveca/awh-use-case/md-files/pdbs'
    pdbs = ['/'.join([pdb_dir,f]) for f in os.listdir(pdb_dir) if f.endswith('.pdb') ]

    build_list=[
        {'name':'charmm', 'ff': 'charmm27', 'water':'tip3p', 'ffdir':None},
        {'name':'amber', 'ff': 'amber99bsc1', 'water':'spce', 'ffdir':'/data/viveca/awh-use-case/md-files/forcefields/amber99bsc1.ff'}
    ]

    startdir=os.getcwd()
    for pdb, specs in zip(len(build_list)*pdbs, len(pdbs)*build_list,):

        sysname = pdb.split('.pdb')[0].split('/')[-1]

        # Define the directory hierarchy
        build_dir = '/'.join([startdir, specs['name'], sysname, 'build'])

        print '>>>>>>> Building pdb and specs ', pdb,  specs, 'into', build_dir

        if make_clean:
            build_runs.run_in_shell('rm -rf ' + build_dir)

        build_runs.run_in_shell('mkdir -p ' + build_dir)

        # Add external parameters if needed
        if specs['ffdir']:
            build_runs.run_in_shell('cp -r ' + specs['ffdir'] + ' ' + build_dir)

        # Build the gmx system
        os.chdir(build_dir)
        build_periodic_dna(pdb, forcefield=specs['ff'], watermodel=specs['water'])
        os.chdir(startdir)
