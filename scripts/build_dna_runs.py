#! /usr/bin/env python2.7

import os, sys
import numpy as np

import gmx_builder as gmxb
from gmx_builder import run_in_shell as xsh
from gmx_builder import make_tpr
from gmx_builder import remove_temporary_files
from gmx_builder import read_lines

# Global variables
gmx='/data/viveca/gromacs/build-release-2018-debug-mpi/bin/gmx_mpi_debug'

def read_gro_coordinates(gro):
    # gro-file format info
    gro_columns = {'residue':0, 'name':1, 'index':2,
                   'x':3, 'y':4, 'z':5,
                   'vx':6, 'vy':7, 'vz':8}
    gro_header_size = 2
    gro_footer_size = 1

    # Read gro-file as a list of strings
    lines = read_lines(gro);

    # Remove data headers
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
    stdout = xsh(' '.join([gmx, 'editconf', args]))

def pdb2gmx_periodic(pdb, watermodel, forcefield):

    # Assume a pdb2gmx wrapper script for periodic molecules is in the same directory as this file.
    periodic_pdb2gmx = os.path.dirname(os.path.realpath(__file__)) + '/gmx-pdb2gmx-wrapper-periodic-dna.sh'

    args=' '.join(['-water', watermodel, '-ff', forcefield, '-f', pdb])
    xsh(' '.join([periodic_pdb2gmx, args]))

def solvate_box(gro='conf.gro', top='topol.top', tpr='topol.tpr'):
    args = ' '.join(['-cp', gro, '-p', top, '-cs','-o', 'conf.gro'])
    stdout = xsh(' '.join([gmx, 'solvate', args]))


def neutralize_box(gro='conf.gro', top='topol.top', tpr='topol.tpr'):
    args = ' '.join(['-neutral', '-pname', 'NA', '-p', 'topol.top', '-o', 'conf.gro'])
    interactive_args = 'SOL'
    cmd = ' '.join(['echo -e', interactive_args, '|', gmx, 'genion', args])

    stdout = xsh(cmd)

def build_periodic_dna(pdb_path, watermodel='tip3p', forcefield='charmm27', make_clean=True):

    # Generate gmx topology and config file.
    pdb2gmx_periodic(pdb_path, watermodel, forcefield)

    # Test if a gmx run (tpr-) file can be generated.
    # Also, the gmx tools often require a tpr as input.
    make_tpr('.', nomdp=True)

    # Set the box size and shape.
    make_box_for_periodic_dna()

    # Add water to the box.
    make_tpr('.', nomdp=True)
    solvate_box()

    # Neutralize system by adding ions.
    make_tpr('.', nomdp=True)
    neutralize_box()

    # Make a final tpr.
    make_tpr('.', nomdp=True)

    # Clean up
    if make_clean:
        remove_temporary_files()

# Parameter file (mdp) settings
em_mdp = {
    'integrator': 'steep',
    'emtol': '1000.0',
    'emstep': '0.01',
    'nsteps': '50000',
    'coulombtype': 'pme',
    'vdwtype': 'cut-off',
    'cut-off-scheme': 'verlet',
}
        
npt_mdp = {
    'integrator': 'md',
    'dt': '0.002',
    'nsteps': '25000000',
    'nstlog': '5000000',
    'nstenergy': '50000',
    'nstxtcout': '500000',
    # pressure
    'pcoupl': 'parrinello-rahman',
    'tau_p': '5.0',
    'pcoupl-type': 'isotropic',
    'ref-p': '1.0',
    'compressibility': '4.5e-5',
    # temperature
    'tcoupl': 'v-rescale',
    'tau-t': '0.5',
    'ref-t': '300',
    'tc-groups': 'system',
    # electrostatics and vdw
    'coulombtype': 'pme',
    'vdwtype':'cut-off',
    'cut-off-scheme': 'verlet',
}

def electrostatics_vdw_mdp(ff_name):
    # These are just examples, but should at least be reasonable.
    if ff_name == 'charmm':
        mdp = {
            'rcoulomb':'1.2',
            'fourierspacing': '0.14',
            'vdw-modifier': 'force-switch',
            'rvdw-switch': '0.8',
            'rvdw': '1.2'
        }
    elif ff_name == 'amber':
         mdp = {
       'rcoulomb':'1.0',
        'fourierspacing': '0.121',
        'vdw-modifier': 'potential-shift',
        'rvdw': '1.0',
        'dispcorr': 'ener-pres'
         }
    else:
        valid = {'charmm', 'amber'}
        raise ValueError("results: status must be one of %r." % valid)

    return mdp

def mdp_periodic_dna(ff_name, run_type):

    if run_type == 'npt':
        base = npt_mdp
    elif run_type == 'em':
        base = em_mdp
    else:    
        valid = {'npt', 'em'}
        raise ValueError("results: status must be one of %r." % valid)

    # Force field specific settings
    electrostatics_vdw = electrostatics_vdw_mdp(ff_name)

    # Extra definitions to add because of the molecule being periodi
    periodic_mol = {
        'periodic-molecules': 'yes',
        'pcoupl-type': 'semiisotropic',
        'ref-p': '1.0 1.0',
        'compressibility': '4.5e-5 4.5e-5',
    }

    # The merge order matters. Later mdps have precedence.
    mdp =  gmxb.merge_mdps([base, electrostatics_vdw, periodic_mol])

    return mdp

# An example of how how one could build a simulation experiment for the periodic DNA system.
def example_build(make_clean=False):
    pdb_dir = '/data/viveca/awh-use-case/md-files/pdbs'
    pdbs = ['/'.join([pdb_dir,f]) for f in os.listdir(pdb_dir) if f.endswith('.pdb') ]

    # Build specifications (model parameters)
    build_list = [
        {'name':'charmm', 'ff': 'charmm27', 'water':'tip3p', 'ffdir':None},
        {'name':'amber', 'ff': 'amber99bsc1', 'water':'spce', 'ffdir':'/data/viveca/awh-use-case/md-files/forcefields/amber99bsc1.ff'}
    ]

    def sysname(pdb):
        return pdb.split('.pdb')[0].split('/')[-1]

    startdir=os.getcwd()

    # Here, each pdb is built with each model.
    for pdb, specs in zip(len(build_list)*pdbs, len(pdbs)*build_list,):

        # Define the directory hierarchy. Infer system name from pdb file.
        build_dir = '/'.join([startdir, specs['name'], sysname(pdb), 'build'])
        print '>>>>>>> Building pdb and specs ', pdb,  specs, 'into', build_dir
        if make_clean:
            xsh('rm -rf ' + build_dir)
        xsh('mkdir -p ' + build_dir)

        # Add external parameters if needed
        if specs['ffdir']:
            xsh('cp -r ' + specs['ffdir'] + ' ' + build_dir)

        # Build the gmx system
        os.chdir(build_dir)
        build_periodic_dna(pdb, forcefield=specs['ff'], watermodel=specs['water'])
        os.chdir(startdir)

        # Add runs.  Here, each run is added to each build.
        run_list = [
            {'name':'em', 'mdp': mdp_periodic_dna(specs['name'], 'em')},          
            {'name':'npt', 'mdp': mdp_periodic_dna(specs['name'], 'npt')},
            #{'name':'npt', 'mdp': mdp_periodic_dna(specs['name'], 'awh')},
        ]

        # Put the run directory on the same level as the build directory
        for run in run_list:
            run_dir = '/'.join([startdir, specs['name'], sysname(pdb), run['name']])

            print '>>>>>>> Adding run template for ' + run['name'] + ' in ' + run_dir
            if make_clean:
                xsh('rm -rf ' + run_dir)
            xsh('mkdir -p ' + run_dir)
            template_dir = run_dir + '/template'

            #            #mdp = mdp_periodic_dna(specs['name'], run['name'])
            gmxb.make_run_template(build_dir, mdp, template)

#            print run['mdp']
            sys.exit()



