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

# ======================================================
#
# FUNCTIONS
# ======================================================

# read data from an .xvg-file, i.e. ignore
# lines starting with # or @.
def read_xvg(fname, skip=1, usemask=False):
    # if file does not exist, exit
    # if exists, check number of commentlines to skip
    # extract data and return

    if (not os.path.exists(fname)):
        print "WARNING: file " + fname + " not found."
        return [],[]

    # Since xvg files can have both @ and # as a head we check
    # the size of the header here.
    # genfromtxt ignores lines starting with #.
    # Also extract comments starting with # here.
    nskip = 0
    comments =[]
    founddata=False
    with open(fname) as f:
        for line in f:

            if line.startswith(("#")):
                comments.append(line.rstrip('\n').lstrip('#').rstrip().lstrip())

            if line.startswith(("@","#")):
                if not founddata:
                    nskip += 1
            else:
                founddata = True
    try:
        data = np.genfromtxt(fname, skip_header=nskip, invalid_raise=True, usemask=usemask)
    except ValueError as e:
        print "Raised ValueError! Incorrect data format in " + fname + "?"
    except MemoryError as e:
        print "Raised MemoryError while reading " + fname + "! Try decreasing your file size."
        raise

    return data[::skip], comments


#--------------------------------------------
# Main function
#--------------------------------------------

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Plot y(x).")

    parser.add_argument(dest='datafiles', nargs ='+', type=str, help="File with data. x, y in first, second column.")

    # Optional args
    parser.add_argument('--out', dest='out', type=str, default='plot.pdf',
                        help='name of output figure')

    parser.add_argument("--xmin", type=float, help="max x")
    parser.add_argument("--xmax", type=float, help="min x")
    parser.add_argument("--ymin", type=float, help="max x")
    parser.add_argument("--ymax", type=float, help="min x")
    parser.add_argument("--xlabel", type=str, help='x-axis label')
    parser.add_argument("--ylabel", type=str, help='y-axis label')
    parser.add_argument("--title", type=str, help='y-axis label')


    args = parser.parse_args()

    print "Plotting data from " + ' '.join(args.datafiles) + ' to ' + args.out

    # global configurations
    fontsize=16
    plt.rcParams.update({'font.size': fontsize})
    linewidth = 2

    scale = 6
    nrows, ncols = 1, 1
    width=scale*ncols
    height=scale*nrows
    fig, ax = plt.subplots(nrows, ncols, figsize = (width, height))
    plt.axes(ax)

    xcol, ycol = 0, 1
    for datafile in args.datafiles:
        data, metadata = read_xvg(datafile)

        x, y  = data[:, xcol], data[:, ycol]
        addedlines = plt.plot(x, y, lw=linewidth)

    if args.xlabel:
        ax.set_xlabel(args.xlabel)
    if args.ylabel:
        ax.set_ylabel(args.ylabel)
    if args.title:
        ax.set_title(args.title)


    print "Saving to file " + args.out
    plt.savefig(args.out)

