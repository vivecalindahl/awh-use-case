#! /usr/bin/env python2.7

# ======================================================
#
# IMPORTS
# ======================================================

import os
import argparse
import warnings

# Execute global startup script
startup = os.environ.get("PYTHONSTARTUP")
if startup and os.path.isfile(startup):
    execfile(startup)

# My own modules
import read_write as rw

# ======================================================
#
# FUNCTIONS
# ======================================================

# Normalize y(x)
#---------------------------------------------------------
def normalize(y, exp=False):
    if exp:
        sumexpy = np.exp(-y).sum(axis=0)
        y = y + np.log(sumexpy)
    else:
        y = y - np.mean(y)

    return y


# Return weighted average y(x) for a sequence {y(x)}
#---------------------------------------------------------
# To get the stdev of the average: dof = ny - 1
# More:
# ys.shape() = (nx, ny)
# See e.g. http://en.wikipedia.org/wiki/Weighted_arithmetic_mean#Correcting_for_over-_or_under-dispersion
# for expression for variance of weighted mean.

def avg_weighted_arrays(ys, expavg=False, sub=False, stdev=False, weights=None, dof=1):
    ny = ys.shape[1]
    stdy = 0
    if expavg:
        # normalize y s.t. sum_x exp(-y) = 1
        sumexpys = np.exp(-ys).sum(axis=0).reshape((1, ny))
        ys = ys + np.ma.log(sumexpys)
        expys = np.exp(-ys)
        avgexpys = np.ma.average(expys, axis=1, weights=weights)
        avgexpys = avgexpys.reshape((expys.shape[0], 1))
        avgy = -np.ma.log(avgexpys)
        if stdev:
            stdexpy = std_weighted_arrays(expys, avgexpys, axis=1, weights=weights)
            stdexpy = stdexpy.reshape(avgexpys.shape)
            stdy = stdexpy/avgexpys # Propagation of error
    else:
        # Align first by subtracting (row) average for each run
        if sub:
            ys =  ys - ys.mean(axis=0).reshape((1, ny));

        avgy = np.ma.average(ys, axis=1, weights=weights)
        avgy = avgy.reshape((ys.shape[0], 1))

        if stdev:
            stdy = std_weighted_arrays(ys, avgy, axis=1, weights=weights)

    # Standard deviation of mean
    stdavgy = None
    if stdev:
        if dof > 0:
            stdavgy = stdy/np.sqrt(dof)
        else:
            stdavgy = np.zeros(stdy.shape)

    return avgy, stdavgy

# Return standard deviation for a sequence {y(x)}
#---------------------------------------------------------
def std_weighted_arrays(ys, avgy, axis=0, weights=None):
    # Note 1: no degree of freedoms choice in np_average
    # Note 2: assumes avg_y has right shape (relative to y)

    var = np.average((ys - avgy )**2, axis=axis, weights=weights)
    return np.sqrt(var)



def var_jackknife(ys, wx=None, niter=10, weights=None):
# Return the variance estimate of the average of sequence {y(x)} using the jackknife method 
#---------------------------------------------------------
# Note 1: only supports selfconsistent averaging for now
# Note 2: yref could in principle be something else but is usually the jack knife mean 

    nx, ny = ys.shape[0], ys.shape[1]
    ys = np.ma.array(ys)

    if  weights is None:
        weights = np.ma.ones((1,ny))
    else:
        weights = weights.reshape((1,ny))

    if  wx is None:
        wx = np.ma.ones((nx,ny))
    else:
        wx = wx.reshape((nx,ny))

    # The averages of the subsets with 1 run deleted
    avg_ys_sub = np.ma.empty(ys.shape)

    for i in range(ny):

        # Subset with ith run deleted
        mask_sub = np.delete(ys.mask, i, 1) 
        ys_sub = np.ma.array(np.delete(ys, i, 1), mask=mask_sub)
        wx_sub = np.ma.array(np.delete(wx, i, 1), mask=mask_sub)        
        weights_sub = np.ma.array(np.delete(weights, i, 1))

        # Get the subset mean. The average returned by avg_exp_selfconsistently
        # is normalized st. the average of y(x) over x is zero.
        avg_ys_sub[:,i] = avg_exp_selfconsistent(ys=ys_sub, wy=weights_sub, wx=wx_sub).reshape((nx,))

    # For now we align by subtracting the minimum value.
    avg_ys_sub -= np.ma.min(avg_ys_sub, axis=0).reshape((1,ny))     

    # The full set average
    avg_y = avg_exp_selfconsistent(ys=ys, wy=weights, wx=wx).reshape((nx,1))
    avg_y = avg_y - np.ma.min(avg_y)

    # Note: if the subset averages are aligned by subtracting the mean the full set
    # average is equal to the linear average over the subset averages:
    # avg_y = np.ma.mean(avg_ys_sub, axis=1).reshape((nx, 1))

    # The final variance estimate is the sum (over runs) of square deviations.
    # Variance(x)
    var = 1.*(ny - 1)/ny*np.ma.sum((avg_ys_sub - avg_y)**2, 1)

    return var

def avg_exp_selfconsistent(ys, wy=None, wx=None, niter=10):
# Return self-consistent exponential average y(x) for a sequence {y_i(x)}
#---------------------------------------------------------
# More:
# exp(-y) = sum_i wy_i*(Z_i/z_i)*exp(-y_i) = sum_i wy_i*(sum_x exp(wx_i(x) - y(x)))/(sum_x exp(wx_i(x) - y_i(x)))*exp(-y_i)
# where:
# wy_i is a global normalization factor for y_i (corresponding to the total number of samples),
# wx_i is a local normalization factor,
# Z_i = sum_x exp(wx_i(x) - y(x)),
# z_i = sum_x exp(wx_i(x) - y_i(x)).
#
# The fact that Z_i is a function of unknown and sought for variable y is the reason for using a self-consistent approach.
#
# ys.shape() = (nx, ny)
#
# Note 1: if wx_i = constant for all x this will should be equivalent to simple exponential averaging
# exp(-y) = sum_i wy_i*Z*exp(-y_i)/z_i, where
# z_i = (sum_x exp(-y_i(x))), and
# Z = sum_x exp(-y(x)) here has become a constant for all i.
#
# Note 2: The normalization of wx_i gets divided away because wx_i only appears in the factor Z_i/z_i.

    nx, ny = ys.shape[0], ys.shape[1]

    # Use masked arrays
    ys = np.ma.array(ys)

    if wy != None:
        if wy.shape == (1, ny) or wy.shape == (ny,1):
            wy = wy.flatten()
        elif wy.shape != (ny,):
            print "ERROR: wy is of shape " + str(wy.shape) + "but should be of shape " + str((ny,))
            sys.exit(1)
    else:
        wy = np.ma.ones((ny,))

    if wx != None and wx.shape != ys.shape:
        print "ERROR: wx is of shape " + str(wx.shape) + "but should be of shape " + str(ys.shape)
        sys.exit(1)
    elif wx == None:
        wx = np.ma.zeros(ys.shape)

    wx = np.ma.array(wx)
    wx.mask = ys.mask

    # Align linearly to avoid numerical issues with the exponential
    ys = ys - np.ma.mean(ys,0).reshape((1,ny))
    wx = wx - np.ma.mean(wx,0).reshape((1,ny))

    # Normalize wx so that z_i = sum_x {exp(wx_i(x) - y_i(x))} = 1
    # This means we only need to care about Z_i from now on (as
    # long as we don't realign y_i.).
    wx = wx -np.ma.log( np.ma.sum(np.ma.exp(-ys + wx),0)) # (nx,ny) - (1,ny)

    # We could subtract an overall constant 
    # wx = wx -  np.ma.mean(wx)

    # Initial guess of average = linear average of the aligned ys
    avg_y,_ = avg_weighted_arrays(ys, weights=wy)
    #avg_y,_ = avg_weighted_arrays(ys, weights=wy, expavg=True)

    avg_y   = avg_y.reshape((nx,1))
    avg_y   = avg_y - np.ma.mean(avg_y)
    
    nx_nonmasked = np.ma.count(avg_y)

    # Self-consistent exponential average
    for k in range(niter):
        Z = np.ma.sum(np.ma.exp(wx - avg_y), 0).reshape((1, ny))
        nom = np.ma.sum(wy*Z*np.ma.exp(avg_y - ys), 1).reshape((nx, 1)) # sum_1 (1,ny)^2*((nx,1) - (nx,ny)) = sum_1 (nx,ny) = (nx)

        # This normalization just keeps the update around 0
        denom = np.ma.sum(nom) 
        nom = nx_nonmasked*nom

        # Update.
        # Note: the update is equivalent to:
        # avg_y = -np.ma.log(np.ma.sum(wy*Z*np.ma.exp(- ys), 1).reshape((nx, 1)))
        avg_y = avg_y - np.ma.log(nom/denom)

        # Keep same normalization of result
        avg_y = avg_y - np.ma.mean(avg_y)

    # Normalize with minimum y instead.
    avg_y = avg_y - np.ma.min(avg_y)

    return avg_y

# Calculate average y(x) for a sequence {y(x)}
#---------------------------------------------------------
# Description:
# Reads input y(x) datafiles and writes the average y(x)

def avg_data(filenames, outfile="out.dat", sub=True, col=1, expavg=False, stdev=True,
             weights=None, wcol=None, dymax=None, dim=1):
    # Get a matrix of all the y(t)
    ys = np.empty(0)

    if wcol:
        wxs = np.ma.empty(0)
    else:
        wxs = None
    ny = 0
    nx = 0
    for fname in filenames:
        #data = np.genfromtxt(fname, skip_header=nskip, invalid_raise=True)
        data, _ = rw.read_xvg(fname, usemask=True)
        y = data[:,col]
        y = y.reshape(len(y),1)
        if wcol:
            wx = data[:,wcol]
            wx = wx.reshape(y.shape)
        if ny > 0:
            if nx != data.shape[0]:
                sys.exit("avg_arrays.py: y(x) in files have different lengths")
            ys = np.hstack([ys, y])
            if wcol:
                wxs = np.hstack([wxs,wx])
        else:
            # First file
            x = data[:,:dim].reshape(len(y),dim)
            nx = len(x)
            ys = y
            if wcol:
                wxs = wx
        ny = ny + 1

    ys = np.ma.masked_invalid(ys)
    if wcol:
        wxs.mask = ys.mask

    if np.ma.count_masked(ys) > 0 :
        print "WARNING: data has invalid entries. Ignoring."

    # Mask values above the dymax cutoff
    if dymax:
        ymins = np.ma.min(ys,0)
        ys = np.ma.masked_where((ys - ymins) > dymax, ys)
        ys = np.ma.mask_rows(ys)
        print "Masking " + str(np.ma.count_masked(ys[:,0])) + " y values due to the y cutoff"

    # Get average and standard deviation along columns/trajectories
    if expavg:
        avgy = avg_exp_selfconsistent(ys, wx=wxs)
        if stdev:
            stdavgy = np.ma.sqrt(var_jackknife(ys=ys, wx=wxs, weights=weights))
    else:
        # Here, stdavgy is actually the rmsd and not the stdev of the average of y.
        avgy, stdavgy = avg_weighted_arrays(ys, expavg=expavg, sub=sub, stdev=stdev, weights=weights, dof=1)

    if expavg:
        avgy = avgy - np.ma.min(avgy)

    # Set fill value to something larger than the maximum to make it unique but not annoying
    # when visualizing the output.
    fillvalue=np.ma.max(avgy) + 1.0
    np.ma.set_fill_value(avgy, fillvalue)
    avgyfilled = np.ma.filled(avgy)

    # Masked values have zero error bars
    fillvalue = 0.
    np.ma.set_fill_value(stdavgy, fillvalue)
    stdavgyfilled = np.ma.filled(stdavgy)

    # Collect results and write to file
    if stdev:
        dataout = np.ma.hstack([x, avgyfilled.reshape(len(x),1), stdavgyfilled.reshape(len(x),1)])
    else:
        dataout = np.hstack([x, avgyfilled.reshape(len(x),1)])

    # Save to file
    np.savetxt(outfile, dataout)

#--------------------------------------------
# Main function
#--------------------------------------------

if __name__ == "__main__":

    # Parse arguments
    parser = argparse.ArgumentParser(description="calculate average of y(x) for a number of y's")

    # Positional args
    parser.add_argument('filenames', type=str, nargs='+',
                        help='files with different y(x)')
    # Optional args
    parser.add_argument("--ycol", type=int, help="column with y data, 0-indexed (1)")
    parser.add_argument("--dymax", type=float, help="maximum y - ymin. Mask y values larger than this.")
    parser.add_argument("--dim", type=int, help="dimension of x variable (1)")
    parser.add_argument("--out", type=str, help="output file name")
    parser.add_argument("--sub", action='store_true', help="align each y(x) before calculating the average/variance " \
                        "by subtracting the average over x")
    parser.add_argument("--exp", action='store_true', help="exponential average. If wcol is provided this is done selfconsistently.")
    parser.add_argument("--wcol", type=int, help="for self-consistent averaging: column with local weight data, 0-indexed")
    parser.add_argument("--stdev", action='store_true', help="output standard deviation of the mean for exp averaging "\
                        "and rmsd for linear averaging.")
    parser.add_argument("--weights", nargs='+', type=float, help="list of weights associated with each given file")

    args = parser.parse_args()
    filenames = args.filenames
    outfile = args.out
    if not outfile:
        outfile = 'avg_t.dat'
        print "NOTE: --out not specified. Assuming out='avg_t.dat'"
    sub = args.sub

    dim = args.dim
    if not args.dim:
        dim = 1

    col = args.ycol
    if not col:
        col = dim
        print "NOTE: --ycol not specified. Assuming ycol=" + str(col)
    expavg = args.exp
    stdev = args.stdev

    if expavg and sub:
        print "ERROR: options --exp and --sub are incompatible. "
        sys.exit(1)
    elif expavg:
        sub = False

    weights = args.weights

    if weights and (len(weights) != len(filenames)):
        print "ERROR: the number of weights (" + str(len(weights)) + ") " \
              "must equal the number of given files (" + str(len(filenames)) + ")."
        sys.exit(1)

    wcol = args.wcol
    if wcol and not expavg:
        print "ERROR: option --wcol is only compatible with --exp."
        sys.exit(1)

    avg_data(filenames, outfile, sub, col, expavg, stdev, weights, wcol, args.dymax, dim)
