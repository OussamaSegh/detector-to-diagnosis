# Exercise 26.2: notes on the solution

**The two mistakes.**

- *The highest pixels are not the peaks.* A blob of 400 events blurred over a few pixels has
  several pixels higher than the top of a dimmer blob. The starter's 256 highest pixels sat on
  209 crystals. A peak is a local maximum of the smoothed flood: no pixel within two pixels is
  higher. Smoothing first keeps the noise of single pixels from making maxima of their own.
- *A regular grid is not the block.* The light sharing compresses the edges: in the
  acceptance block the rows are 16 pixels apart at the centre and 6.8 at the edges, and they
  sag. The starter's cell `int(r * 16 / 256)` put several edge peaks in one cell and left
  others empty. The order survives every distortion: the 16 highest peaks are the first row,
  the next 16 the second, each row sorted by column. That holds while a row's sag is smaller
  than the gap to the next row; a block whose rows cross needs a fit of the grid instead.

Two half-pixel details: a peak's position is refined by the centroid of its 3 by 3 pixels, and
pixel k covers positions k to k + 1, so its centre is k + 0.5 (the same mistake as the bin
positions of Exercise 26.1).

**The edges** (Then, by hand, 1). Of the events misidentified in the acceptance block (0.08%),
almost all are in the outer rows and columns, where neighbours are 6.8 pixels apart instead of
16 with the same blur. In a real block the edge crystals also see less light, so their blobs
are wider as well as closer: they are the first to merge, and a site's flood is read edge first.

**Boundaries** (2). The nearest peak puts every boundary halfway between two peaks, whatever
their brightness. The valley between two blobs of different brightness is closer to the dimmer
one, so the halfway boundary gives some of the brighter crystal's tail to the dimmer one, and a
watershed along the valleys would not. With equal blobs the two are the same; with a weak edge
crystal next to a bright inner one the difference is a few percent of the weak crystal's events.

**Recalibrating a board** (3). Automatic: exactly 256 peaks; rows and columns in order with no
crossing; spacing that changes smoothly from the centre to the edges; more than a set fraction of
the flood's events identified with each crystal getting a plausible share; and the peaks compared
with the previous table's, flagging any that moved more than a pixel or two. A person still looks
at the flood with the boundaries drawn on it, because a merged pair of edge crystals can pass every
count and order check (two peaks found where one should be, one missing elsewhere) and looks
wrong at once.
