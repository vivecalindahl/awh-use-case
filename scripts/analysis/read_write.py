#! /usr/bin/env python2.7

#--------------------------------------------
# Description
#--------------------------------------------
# My IO python functions
#-------------------------------------------
import os
#from progressbar import ProgressBar
#from progressbar import *

# Execute global startup script (os needs to already be imported)
startup = os.environ.get("PYTHONSTARTUP")
if startup and os.path.isfile(startup):
    execfile(startup)


DEBUG=False

#--------------------------------------------
# Function definitions
#--------------------------------------------

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



# AWH data: files of format awh..._t<t>.xvg
def read_awh_xvgs(directory, dim, rskip=1):
    names = [d for d in os.listdir(directory)
                  if d.startswith('awh') and d.endswith('.xvg')]
    t = np.array([float(d.split('_t')[1].split('.xvg')[0]) for d in names])
    tsorted = np.sort(t)
    names_sorted = [d for (t,d) in sorted(zip(t,names))]

    # Peak at first file first
    i = 0
    data, comments = read_xvg(directory + '/' + names_sorted[i], skip=rskip)
    if data.shape[1] <= 2:
        print "FATAL ERROR: not enough columns in data file."
        print "Perhaps you forgot to add -more to gmx energy?"
        sys.exit()

    r = data[:,:dim] # First dim cols
    nr = len(r)
    pmf = data[:,dim].reshape((nr,dim))
    bias = data[:,dim+1].reshape((nr,1))
    target_distr = data[:,dim+2].reshape((nr,1))
    r_conv_distr = data[:,dim+3].reshape((nr,1))
    r_distr = data[:,dim+4].reshape((nr,1))

    t_sampling = np.ones(tsorted.shape) # Oh yeah
    t_sampling[i] = float(([l.split('=')[-1].strip().strip('kJ/mol') for l in comments
                            if ("AWH metadata" in l) & ("target error" in l)])[0])

    # The rest
    #widgets = [Percentage(), Bar()]
    #pbar = ProgressBar(widgets=widgets, maxval=len(names_sorted)).start()
    print 'Loading AWH data...'

    for name in names_sorted: # TODO: first file actually included twice
        data,comments = read_xvg(directory + '/' + name, skip=rskip)

        # Done with r, strip away first dim cols.
        data = data[:,dim:]

        p, b, xd, xcd, td = np.hsplit(data, data.shape[1])
        pmf = np.hstack((pmf, p))
        bias = np.hstack((bias, b))
        r_distr = np.hstack((r_distr, xd))
        r_conv_distr = np.hstack((r_conv_distr, xcd))
        target_distr = np.hstack((target_distr, td))
        t_sampling[i] = float(([l.split('=')[-1].strip().strip('kJ/mol') for l in comments
                            if ("AWH metadata" in l) & ("target error" in l)])[0])

        i = i + 1
        #pbar.update(i)

        if DEBUG and i > 100:
            break

    #pbar.finish()
    print "... done"
    print 'ouph!'

    if DEBUG:
        return (tsorted[:i], names_sorted[:i], r,
                pmf[:,:i], bias[:,:i], target_distr[:,:i],
                r_conv_distr[:,:i], r_distr[:,:i], t_sampling)

    return (tsorted, names_sorted, r,
            pmf, bias, target_distr, r_conv_distr, r_distr,
            t_sampling)
