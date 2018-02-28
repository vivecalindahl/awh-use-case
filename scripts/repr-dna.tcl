# color ids
set gray 2
set silver 6

set irep 0
set imol 0

# Nucleic acid backbone              
mol modselect $irep $imol nucleic and backbone
mol modstyle $irep $imol NewRibbons 0.300000 10.000000 3.000000 0
mol modcolor $irep $imol ColorID $silver
set irep [expr {$irep + 1}]

mol addrep $imol
mol modselect $irep $imol resid 11 28
#mol modselect $irep $imol resid 10 29
mol modstyle $irep $imol Licorice 0.300000 10.000000 10.000000
mol modcolor $irep $imol Name
set irep [expr {$irep + 1}]

mol addrep $imol
mol modselect $irep $imol resid 11 28
#mol modselect $irep $imol resid 10 29
mol modstyle $irep $imol VDW
mol modcolor $irep $imol ColorID $gray
mol modmaterial $irep $imol Transparent
mol drawframes $imol $irep {0}
mol showrep $imol $irep 0

set irep [expr {$irep + 1}]

# dna with basepairs colored
mol addrep $imol
mol modselect $irep $imol nucleic and not backbone
mol modstyle $irep $imol NewRibbons 0.300000 10.000000 3.000000 0
mol modcolor $irep $imol Name
mol showrep $imol $irep 0
set irep [expr {$irep + 1}]

                                                                                                                                               
