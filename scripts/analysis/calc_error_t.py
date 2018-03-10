#! /usr/bin/env python2.7

# ======================================================
#
# IMPORTS
# ======================================================

import os
import argparse
from scipy.interpolate import interp1d

# Execute global startup script (os needs to already be imported)
startup = os.environ.get("PYTHONSTARTUP")
if startup and os.path.isfile(startup):
    execfile(startup)

# My modules
import avg_arrays
import read_write as rw
import function_utils as fu

# ======================================================
#
# FUNCTIONS
# ======================================================

# Calculate error as a function of time.
#---------------------------------------------------------
# Description:
# Reads awh files from given run directories and writes resulting error(t).
#

def error(dt, tstart=0, tmax=1e20,
          dim = 1, runs = '.', dymax = None, xmin = None, xmax = None,
          fmt = 'awh_t{:g}.xvg', reffile = None, refout="ref.dat",
          col = None, wcol = None, refcol = 1, out = 'error_t.dat',
          avgtype='selfconsistent', errortype='rmsd'):

    # Check input and set up parameters
    # ......................................................
    if not col:
        col = dim

    xweights = None
    if avgtype == 'selfconsistent' and not wcol:
        wcol = col + 1
    if avgtype != 'selfconsistent' and wcol:
        print "--wcol is only an option for --avgtype selfconsistent"
        sys.exit(0)

    # Get list of input files to read. Assume all run directories have the same runs
    nruns = len(runs)
    t = tstart
    ts = []
    filenames = [];
    filenametemplate = runs[0] + '/' + fmt

    # Find the times to analyze less than or equal to tmax
    if dt <= 0:
        dt = 1

    while (os.path.isfile(filenametemplate.format(t)) and t <= tmax):
        filenames.append(fmt.format(t))
        ts.append(t)
        t += dt

        # Make sure all directories have all required files
        nt = 0
        for fname in filenames:
            nr = 0
            for run in runs:
                if not os.path.isfile(run + '/' + fname):
                    break
                else:
                    nr = nr + 1
            if nr == nruns:
                nt = nt + 1
            else:
                break;

    if nt < len(filenames):
        del filenames[nt:]
        del ts[nt:]

    ts = np.array(ts);
    nt = len(filenames)
    if nt < 1:
        print "No matching files of format '" + fmt + "' found! Exiting."
        sys.exit();

    printfreq = 10**(np.floor(np.log10(nt))-1)

    # Assume all data files have the same format. Get format from the first one.
    # First cols are x. y is at column col.
    refformatfile = runs[0] + '/' + filenames[0]
    data = []

    data, _ = rw.read_xvg(refformatfile, usemask=True)

    xs = data[:,:dim]
    nx = xs.shape[0]

    if not xmin:
        xmin = np.min(xs)
    if not xmax:
        xmax = np.max(xs)

    xmin = max(np.min(xs), xmin)
    xmax = min(np.max(xs), xmax)

    xs = np.ma.masked_outside(xs, xmin,xmax)

    # Get reference profile
    # ......................................................

    # Either ref is given or calculate reference profile from last time
    get_errorbars = (errortype == "jackknife") and (avgtype == "selfconsistent")
    errorbars = np.ma.empty(nx)

    yref = np.ma.empty(nx)
    if reffile:
        dof = nruns
        data, _ = rw.read_xvg(reffile, usemask=True)

        if dim == 1:
            # 1D: Interpolate to get yref at same x values as runs
            xsref, yrefdata = data[:,0], data[:,refcol]
            xminref, xmaxref = np.min(xsref), np.max(xsref)
            xs = np.ma.masked_outside(xs, xminref,xmaxref) # This adds to the x mask already set
            yreffcn = interp1d(xsref, yrefdata, kind='cubic', bounds_error=False)
            yref = np.ma.masked_invalid(yreffcn(xs)).flatten()
            if (np.ma.count_masked(xs) > 0):
                yref = np.ma.masked_where(xs.mask.reshape(yref.shape), yref)
        else:
            # dim > 1: only if ref has same points as data
            xref = data[:,:dim]
            if (xref != xs).any():
                print "Reference and data points do not match. Exiting."
                sys.exit();
            else:
                yref = data[:,refcol]
    else:
        if nruns > 0:
            dof = nruns - 1
        else:
            dof = 1 # Avoid divide by zero below

        fname = filenames[-1]
        ys = np.ma.empty((nx, nruns))

        if wcol:
            xweights = np.ma.empty((nx, nruns))
        else:
            xweights = None

        ymins = np.ma.empty((nx, nruns))
        r = 0
        for run in runs:
            data, _ = rw.read_xvg(run + '/' + fname, usemask=True)
            y = data[:,col]
            if wcol:
                xweights[:,r] = data[:,wcol]
            ymin = np.min(y);
            ys[:,r] = y
            ymins[:,r] = ymin
            r = r + 1

        # Apply mask for all x outside of cutoff
        if dymax:
            ys = np.ma.masked_where((ys - ymins) > dymax, ys)
            ys = np.ma.mask_rows(ys)

        ys.mask = np.ma.mask_or(ys.mask, xs.mask)
        if avgtype == "selfconsistent":
            yref = avg_arrays.avg_exp_selfconsistent(ys, wx=xweights)
            if get_errorbars:
                errorbars = np.ma.sqrt(avg_arrays.var_jackknife(ys, xweights))
        elif avgtype == "linear":
            yref,_ = avg_arrays.avg_weighted_arrays(ys, expavg=False, sub=True)
        else:
            yref,_ = avg_arrays.avg_weighted_arrays(ys, expavg=True)

    yref = np.ma.array(yref)

    # Subtract min of for looks of output
    yrefout = yref - np.min(yref)
    yrefout = yrefout.filled(yrefout.max())
    dataout = np.hstack([xs, yrefout.reshape(nx,1)])

    if get_errorbars:
        dataout = np.hstack([dataout, errorbars.reshape((nx,1))])

    np.savetxt(refout, dataout, fmt='%g')
    print "Writing error reference to " + refout

    #  Read data for each time and calculate average error(t)
    # ........................................................
    ys = np.ma.empty((nx, nruns))

    if wcol:
        xweights = np.ma.empty((nx, nruns))
    else:
        xweights = None

    dys = np.ma.empty((nx, nruns))
    ymins = np.ma.empty((nx, nruns))

    # The mean square deviation (as a function of time), i.e. an estimate of the squared error.
    meansqrdevs = np.ma.empty(nt)

    # The variance of the square deviation, i.e. an estimate of the variance of the squared error.
    getErrorVariance = (errortype == "rmsd")
    varsqrdevs = np.ma.empty(nt)

    # We align the reference to the runs by subtracting the average over x.
    # Note: this could be done differently
    # (e.g. by exponential average or by minimizing the error somehow) or
    # one could avoid alignment by estimating the deviation as 
    # dy(x1, x2) - dy_ref(x1, x2)  and average over all pairs (x1, x2).
    yref = yref - np.ma.mean(yref)
    yref = yref.reshape((nx,1))

    for f in range(nt):
        fname = filenames[f]

        # Read a file with y data for this time, for each run.
        for r in range(nruns):
            run = runs[r]
            data, _ = rw.read_xvg(run + '/' + fname, usemask=True)
            y = np.ma.array(data[:,col], mask = yref.mask)
            if wcol:
                xweights[:,r] = np.ma.array(data[:,wcol], mask = yref.mask)
            
            # Align and store y for each run
            ys[:,r] = y - np.ma.mean(y)

        # With jackknife we estimate the error of the average of all runs
        if errortype == 'jackknife':
            if avgtype == 'selfconsistent':
                # Average over all x
                meansqrdevs[f] = np.ma.mean(avg_arrays.var_jackknife(ys, xweights))
            else:
                print "ERROR: jackknife error is only supported together with selfconsistent averaging"
                sys.exit()
        # With rmsd we estimate the error of a single run
        else:
            # The y deviation as a function of x for each run.
            dys = ys - yref

            # The square deviation, averaged over x.
            sqrdev = np.mean(dys**2, 0)

            # The mean square deviation (second moment of the deviation)
            meansqrdevs[f] = np.sum(sqrdev)/dof

            if getErrorVariance:

                # Fourth moment of the deviation
                varsqrdevs[f] = np.sum((sqrdev)**2)/dof

                # The variance of the square deviation in two formulations.
                #varsqrdevs[f] = np.sum((sqrdev - meansqrdevs[f])**2)/dof 
                #varsqrdevs[f] = np.sum((sqrdev)**2)/dof - meansqrdevs[f]**2
                
        if f%printfreq == 0 or fname == filenames[-1]:
            print fname

    # The output is in units of deviation, i.e. we take the square root of the mean square deviation (RMSD).
    dataout = np.hstack([ts.reshape(nt,1), (np.sqrt(meansqrdevs)).reshape(nt,1)])

    if getErrorVariance:
        # "Error bars" for the error. To get units of deviation, we need to take fourth root.
        #dataout = np.hstack([dataout, (np.power(varsqrdevs, 0.25)).reshape(nt,1)])

        # Fourth moment of the deviation normalized by the second moment, kurtosis or "tailedness".
        dataout = np.hstack([dataout, (varsqrdevs/meansqrdevs**2).reshape(nt,1)])


    print "Writing error to " + out
    np.savetxt(out, dataout, fmt='%g')

#--------------------------------------------
# Main function
#--------------------------------------------

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="calculate error(t) for a number of runs")

    # Positional args
    parser.add_argument("tstart", type=float, help="time of first file")
    parser.add_argument("dt", type=float, help="time step in between files")
    parser.add_argument("tmax", type=float, help="max time of last file")

    # Optional args
    parser.add_argument("--dim", type=int, help="dimension of x variable (1)")
    parser.add_argument("--runs", type=str, nargs='+', help="run directories ('.')")
    parser.add_argument("--col", type=int, help="column with y data, 0-indexed (dim)")
    parser.add_argument("--out", type=str, help="out file name")

    # cutoffs in x or y
    parser.add_argument("--dymax", type=float, help="maximum y-ymin")
    parser.add_argument("--xmin", type=float, help="mininmum x")
    parser.add_argument("--xmax", type=float, help="maximum x")
    parser.add_argument("--fmt", type=str, help="name format for data files")

    # reference profile
    parser.add_argument("--reffile", type=str, help="path to reference profile")
    parser.add_argument("--refout", type=str, help="out reference file name")
    parser.add_argument("--refcol", type=int, help="column with reference y data, 0-indexed (dim)")

    # error and average types
    parser.add_argument("--errortype", type=str, help="type of error estimate: 'jackknife', 'rmsd'" )
    parser.add_argument("--avgtype", type=str, help="type of averaging: 'selfconsistent', 'exp' or 'linear'" )
    parser.add_argument("--wcol", type=int, help="for self-consistent averaging: column with local weight data, 0-indexed (dim+1)")

    parsed_args = parser.parse_args()
    defaults = fu.get_default_args(error)
    argdict = {}

    for arg in vars(parsed_args):
        attr = getattr(parsed_args, arg)
        if not attr and defaults.has_key(arg):
            argdict[arg] = defaults[arg]
        else:
            argdict[arg] = attr

    error(tstart=argdict['tstart'],dt=argdict['dt'], tmax=argdict['tmax'],
          dim=argdict['dim'], runs=argdict['runs'],
          dymax=argdict['dymax'], xmin=argdict['xmin'], xmax=argdict['xmax'],
          fmt=argdict['fmt'], reffile=argdict['reffile'], refout=argdict['refout'],
          col=argdict['col'], wcol=argdict['wcol'], refcol=argdict['refcol'], out=argdict['out'],
          errortype=argdict['errortype'], avgtype=argdict['avgtype'])
