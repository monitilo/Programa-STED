# -*- coding: utf-8 -*-
"""
Created on Fri Oct  5 17:25:14 2018

@author: Santiago
"""
#import pyqtgraph.examples
#pyqtgraph.examples.run()
# corriendolo por consola anda
# %%

#import numpy as np
#import matplotlib.pyplot as plt
#
##-- Generate some data...
#x, y = np.mgrid[-5:5:0.1, -5:5:0.1]
#z = np.sqrt(x**2 + y**2) + np.sin(x**2 + y**2)
#
##-- Extract the line...
## Make a line with "num" points...
#x0, y0 = 5, 4.5 # These are in _pixel_ coordinates!!
#x1, y1 = 60, 75
#length = int(np.hypot(x1-x0, y1-y0))
#x, y = np.linspace(x0, x1, length), np.linspace(y0, y1, length)
#
## Extract the values along the line
#zi = z[x.astype(np.int), y.astype(np.int)]
#
##-- Plot...
#fig, axes = plt.subplots(nrows=2)
#axes[0].imshow(z)
#axes[0].plot([x0, x1], [y0, y1], 'ro-')
#axes[0].axis('image')
#
#axes[1].plot(zi)
#
#plt.show()
#%%
import numpy as np
#from numpy import pi, r_
import matplotlib.pyplot as plt
from scipy import optimize

def gaussian(height, center_x, center_y, width_x, width_y):
    """Returns a gaussian function with the given parameters"""
    width_x = float(width_x)
    width_y = float(width_y)
    return lambda x,y: height*np.exp(
                -(((center_x-x)/width_x)**2+((center_y-y)/width_y)**2)/2)

def moments(data):
    """Returns (height, x, y, width_x, width_y)
    the gaussian parameters of a 2D distribution by calculating its
    moments """
    total = data.sum()
    X, Y = np.indices(data.shape)
    x = (X*data).sum()/total
    y = (Y*data).sum()/total
    col = data[:, int(y)]
    width_x = np.sqrt(np.abs((np.arange(col.size)-y)**2*col).sum()/col.sum())
    row = data[int(x), :]
    width_y = np.sqrt(np.abs((np.arange(row.size)-x)**2*row).sum()/row.sum())
    height = data.max()
    return height, x, y, width_x, width_y

def fitgaussian(data):
    """Returns (height, x, y, width_x, width_y)
    the gaussian parameters of a 2D distribution found by a fit"""
    params = moments(data)
    errorfunction = lambda p: np.ravel(gaussian(*p)(*np.indices(data.shape)) -
                                 data)
    p, success = optimize.leastsq(errorfunction, params)
    return p

# Create the gaussian data
Xin, Yin = np.mgrid[0:201, 0:201]
data = gaussian(3, 20, 191, 30, 30)(Xin, Yin) + 0.5*np.random.random(Xin.shape)

plt.matshow(data, cmap=plt.cm.gist_earth_r, origin='lower',
            interpolation='none', extent=[80,120,32,0])
plt.colorbar()
params = fitgaussian(data)
fit = gaussian(*params)

plt.contour(fit(*np.indices(data.shape)), cmap=plt.cm.copper,
            interpolation='none', extent=[80,120,32,0])
ax = plt.gca()
(height, x, y, width_x, width_y) = params



plt.text(0.95, 0.05, """
x : %.1f
y : %.1f
width_x : %.1f
width_y : %.1f""" %(x, y, width_x, width_y),
        fontsize=16, horizontalalignment='right',
        verticalalignment='bottom', transform=ax.transAxes)
#plt.colorbar()
print(x)


#print("centrado en x,y=", x,y)
#%%
import scipy.optimize as opt
import numpy as np
import pylab as plt


#define model function and pass independant variables x and y as a list
def twoD_Gaussian(xdata_tuple, amplitude, xo, yo, sigma_x, sigma_y, theta, offset):
    (x, y) = xdata_tuple                                                        
    xo = float(xo)                                                              
    yo = float(yo)                                                              
    a = (np.cos(theta)**2)/(2*sigma_x**2) + (np.sin(theta)**2)/(2*sigma_y**2)   
    b = -(np.sin(2*theta))/(4*sigma_x**2) + (np.sin(2*theta))/(4*sigma_y**2)    
    c = (np.sin(theta)**2)/(2*sigma_x**2) + (np.cos(theta)**2)/(2*sigma_y**2)   
    g = offset + amplitude*np.exp( - (a*((x-xo)**2) + 2*b*(x-xo)*(y-yo)         
                        + c*((y-yo)**2)))                                   
    return g.ravel()

# Create x and y indices
x = np.linspace(0, 200, 201)
y = np.linspace(0, 200, 201)
x, y = np.meshgrid(x, y)

#create data
data = twoD_Gaussian((x, y), 3, 100, 100, 20, 40, 0, 10)

# plot twoD_Gaussian data generated above
plt.figure()
plt.imshow(data.reshape(201, 201))
plt.colorbar()

# add some noise to the data and try to fit the data generated beforehand
initial_guess = (3,100,100,20,50,0,10)

data_noisy = data + 0.2*np.random.normal(size=data.shape)

popt, pcov = opt.curve_fit(twoD_Gaussian, (x, y), data_noisy, p0=initial_guess)

data_fitted = twoD_Gaussian((x, y), *popt)

fig, ax = plt.subplots(1, 1)
ax.hold(True)
ax.imshow(data_noisy.reshape(201, 201), cmap=plt.cm.jet, origin='bottom',
    extent=(x.min(), x.max(), y.min(), y.max()))
ax.contour(x, y, data_fitted.reshape(201, 201), 8, colors='w')
plt.show()



