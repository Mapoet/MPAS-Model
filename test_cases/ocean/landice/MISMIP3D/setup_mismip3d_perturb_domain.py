#!/usr/bin/env python
# This script sets up MISMIP3D P experiments.
# see http://homepages.ulb.ac.be/~fpattyn/mismip3d/Mismip3Dv12.pdf


GLbit = 256



import sys
from netCDF4 import Dataset
import numpy as np


# Parse options
from optparse import OptionParser
parser = OptionParser()
parser.add_option("-f", "--file", dest="filename", type='string', help="file in which to setup MISMIP3D Perturbation experiment.  This should be a full width domain in which the Stnd experiment initial condition has already been applied..", metavar="FILE")
parser.add_option("-s", "--stnd", dest="stndfilename", type='string', help="file containing output from the Stnd experiment from which to copy model state. This can be a minimal or full width domain.", metavar="FILE")
parser.add_option("-p", "--perturb", dest="perturb", type='float', help="perturbation amount, presumably 75 or 10", metavar="P")
options, args = parser.parse_args()
if not options.filename:
   print  'Filename to set up required.  Specify with -f'
if not options.stndfilename:
   print  'Stnd results filename required.  Specify with -s'
if not options.perturb:
   print  'Perturbation amount required.  Specify with -p'

# Open the Stnd output and get the needed info
fstnd = Dataset(options.stndfilename, 'r')
thicknessStnd = fstnd.variables['thickness'][-1,:]
edgeMaskStnd = fstnd.variables['edgeMask'][-1,:]
nCellsStnd = len(fstnd.dimensions['nCells'])
dcEdgeStnd = fstnd.variables['dcEdge'][:]
xCellStnd = fstnd.variables['xCell'][:]
yCellStnd = fstnd.variables['yCell'][:]
unique_ysStnd = np.array(sorted(list(set(yCellStnd[:]))))
unique_xsStnd = np.array(sorted(list(set(xCellStnd[:]))))
xEdgeStnd = fstnd.variables['xEdge'][:]
yEdgeStnd = fstnd.variables['yEdge'][:]
unique_ysEdgeStnd = np.array(sorted(list(set(yEdgeStnd[:]))))

# Open the file to be set up, get needed dimensions
gridfile = Dataset(options.filename,'r+')
nCells = len(gridfile.dimensions['nCells'])
dcEdge = gridfile.variables['dcEdge'][:]
xCell = gridfile.variables['xCell'][:]
yCell = gridfile.variables['yCell'][:]
unique_ys = np.array(sorted(list(set(yCell[:]))))
unique_xs = np.array(sorted(list(set(xCell[:]))))

if dcEdge.max() != dcEdgeStnd.max() or dcEdge.min() != dcEdgeStnd.min():
   sys.exit('ERROR: The two files are not the same resolution')

if nCellsStnd == nCells:
   if xCell[:] != xCellStnd[:] or yCell[:] != yCellStnd[:]:
      sys.exit('ERROR: The two files have the same number of cells but different x and/or y cell coordinates.')
   eqSize = True
else:
   if len(unique_ysStnd) != 3:
      print "unique yCell:", unique_ysStnd
      sys.exit('ERROR: This Stnd file appears to be a minimal width domain but it does not have 3 unique y values.')
   eqSize = False  # Assume we have a 3 cell wide minimal width domain

print "DOMAIN INFORMATION"
print "Stnd file y-range:", yCellStnd.max() - yCellStnd.min()
print "Perturb file y-range:", yCell.max() - yCell.min()
print "Stnd nCells:", nCellsStnd
print "Perturb file nCells:", nCells
print "Stnd file unique y-values on cells:", unique_ysStnd
print "Perturbfile unique y-values on cells:", unique_ys


print "Defining thickness."
thickness = np.zeros((nCells,))
if eqSize:
   thickness = thicknessStnd
else:
   # Need to map the minimal domain to the full domain
   thkStndProfile = np.zeros((len(unique_xsStnd),))
   for i in range(len(unique_xsStnd)):
      ind = np.where(xCellStnd == unique_xsStnd[i])[0]  # this should return either 1 or2 values
      thkStndProfile[i] = thicknessStnd[ind].mean()  # mean takes care of the places where there are two values - though they should be nearly identical

   # Now assign the correct thickness to each cell of the new file
   for i in range(nCells):
      ind = np.where(unique_xsStnd == xCell[i])[0]
      thickness[i] = thkStndProfile[ind]
# write it out      
gridfile.variables['thickness'][0,:] = thickness[:]      
gridfile.sync()

print "Determining grounding line position."
# Calculate GL position in Stnd output file
if eqSize:
   GLindEast = np.nonzero(
              np.logical_and( (
                 (edgeMaskStnd[:] & GLbit) / GLbit == 1),
                 (xEdgeStnd > 0.0)
              ) )[0]
   GLindWest = np.nonzero(
              np.logical_and( (
                 (edgeMaskStnd[:] & GLbit) / GLbit == 1),
                 (xEdgeStnd < 0.0)
              ) )[0]
else:
   if len(unique_ysEdgeStnd) != 7:
      sys.exit("ERROR: There are not 7 unique yEdge values in the Stnd file but this appears to be a minimal width domain.")
   print "Stnd file unique y-values on edges:", unique_ysEdgeStnd

   # First do east side
   GLindEast = np.nonzero(
           np.logical_and( 
              (edgeMaskStnd[:] & GLbit) / GLbit == 1,
              xEdgeStnd > 0.0) ) [0]
   if len(GLindEast) != 5:
       sys.exit("ERROR: East: There are not 5 unique yEdge GL values in the Stnd file but this appears to be a minimal width domain.")
   # Note that the topmost and bottommost edge positions are effectively outside the domain,
   # and not part of the GL, so are no included by the logic above.
   # In the zigzag GL there are 4 edge position/orientations that make up a whole cycle of 2 cells.
   # Note that "positions" 0 and 4 are both returned and should be identical, but only one of them should be used.
   # However we shouldn't assume that the indices are ordered by increasing yEdge (though in periodic_hex they are).
   # For now we are assuming these are periodic_hex meshes!
   print "East: All GL indices, their yEdge values:", GLindEast, yEdgeStnd[ GLindEast ]
   GLindEast = GLindEast[ [0,1,2,3] ]
   print "East: Using yEdge values from Stnd:", yEdgeStnd[GLindEast]
   print "East: All possible yEdge values from Stnd:", unique_ysEdgeStnd

   # Now do west side
   GLindWest = np.nonzero(
           np.logical_and(
              (edgeMaskStnd[:] & GLbit) / GLbit == 1,
              xEdgeStnd < 0.0) ) [0]
   if len(GLindWest) != 5:
       sys.exit("ERROR: West: There are not 5 unique yEdge GL values in the Stnd file but this appears to be a minimal width domain.")
   GLindWest = GLindWest[ [0,1,2,3] ]
   print "West: Using yEdge values from Stnd:", yEdgeStnd[GLindEast]
   print "West: All possible yEdge values from Stnd:", unique_ysEdgeStnd

GLposEast = xEdgeStnd[GLindEast].mean()
GLposWest = xEdgeStnd[GLindWest].mean()
print "Calculated GL x-positions (m).  East:", GLposEast, " West:", GLposWest
print "WARNING: The GL position calculation may be incorrect for meshes generated by a tool other than periodic_hex!!!"

print "Defining beta." 
# The beta units in MPAS are a mess right now.  This value 10^7 Pa m^-1/3 s^1/3 translates to 31880 in the current MPAS units.
# For the basal friction law being used, beta holds the 'C' coefficient. 
xc = 150000.0
yc = 10000.0
a = float(options.perturb) / 100.0
Ceast = 31880.0 * (1.0 - a * np.exp(-0.5 * (xCell[:] - GLposEast)**2 / xc**2 - 0.5 * (yCell[:] - 0.0)**2 / yc**2) )
Cwest = 31880.0 * (1.0 - a * np.exp(-0.5 * (xCell[:] - GLposWest)**2 / xc**2 - 0.5 * (yCell[:] - 0.0)**2 / yc**2) )
Cboth = Ceast
ind = np.where(xCell<0.0)
Cboth[ind] = Cwest[ind]
gridfile.variables['beta'][0,:] = Cboth

gridfile.sync()
gridfile.close()

print 'Successfully added MISMIP3D perturbation initial conditions to: ', options.filename

