# color ids
set gray 2
set silver 6

set irep 0
set imol 0


# for the periodic chain, some of the end atoms are
# not classified as "nucleic" by default.
set dna "not ions and not water"

# Nucleic acid backbone              
mol modselect $irep $imol $dna
mol modstyle $irep $imol NewRibbons 0.300000 10.000000 3.000000 0
mol modcolor $irep $imol Name
mol showrep $imol  $irep 0
set irep [expr {$irep + 1}]

mol addrep $imol
mol modselect $irep $imol $dna
mol modstyle $irep $imol Licorice 0.300000 10.000000 10.000000
mol modcolor $irep $imol Name
mol showrep $imol  $irep 1
set irep [expr {$irep + 1}]
