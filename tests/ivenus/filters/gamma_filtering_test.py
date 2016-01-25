#!/usr/bin/env python

import numpy as np, os
from ivenus import filters, io

def test(interactive=False):
    # test data
    dir = os.path.dirname(__file__)
    path = os.path.join(dir, "..", "..", "iVenus_data_set", "20120618_TURBINECT_0180_46_750_0055.fits")
    img = io.ImageFile(path).getData()

    # filter
    orig_max = np.max(img)
    img = filters.gamma_filtering.filter(img)
    new_max = np.max(img)
    assert new_max < orig_max
    
    if interactive:
        # display
        import pylab
        pylab.imshow(img)
        pylab.colorbar()
        pylab.show()

if __name__ == '__main__': test(interactive=True)