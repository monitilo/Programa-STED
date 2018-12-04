# -*- coding: utf-8 -*-
"""
Created on Wed Nov 28 11:00:54 2018

@author: Santiago
"""
#import pyqtgraph.examples
#pyqtgraph.examples.run()
# corriendolo por consola anda
# %%
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
root.withdraw()
#name = "10x15(para_probar_grilla)"
name  = filedialog.askopenfilename()
f=open(name,"r")
datos = np.loadtxt(name, unpack=True)
f.close()
x=datos[0,:]
y=datos[1,:]
z=datos[2,:]
plt.plot(x,y)

mode = "full"  # ["valid"  # "full"  # "same"]  #
for moda in ["full","same","valid"]:
    a=np.correlate(x, x, moda)
    b=np.correlate(x, y, moda)
    c=np.correlate(y, x, moda)
    d=np.correlate(y, y, moda)
    plt.figure()
    plt.plot(a, 'm')
    plt.plot(b, 'b')
    plt.plot(c, 'r')
    plt.plot(d, 'c')

ejes = np.zeros((3,len(x)))
ejes[0,:] =x
ejes[1,:] = y
ejes[2,:] = z
for moda in ["full","same","valid"]:
    for i in range(ejes.shape[0]):
        for j in range(ejes.shape[0]):
#            print(i,j,moda)
            p=np.correlate(ejes[i,:], ejes[j,:], moda)
            plt.plot(p)


#%%
import numpy as np
import matplotlib.pyplot as plt

name= "Pepe.txt"
data = (np.linspace(0,9,10))
data2 = np.round(np.linspace(-3,1,10))
data3 = np.round(np.linspace(-30,29,10))
a=2
f=open(name,"w")
np.savetxt(name, np.transpose([data,data2,data3]),fmt='%.18g',
           header= "cosas{} y otras cosas{}".format(a,2*a))
#np.savetxt(name, data2)
#np.savetxt(name, data3)
f.close()
# %%
name= "03122018-160240Traza.txt"
f=open(name,"r")
j=np.loadtxt(name, unpack=True)
f.close()
x =j[0,:]
y =j[1,:]

plt.figure()
plt.plot(x,y)
#%%
f=open(name,"r")
lines=f.readlines()
result=[0]
for x in lines:
    result.append(x.split(' ')[1])
f.close()
# %%
# -*- coding: utf-8 -*-
# author: Sebastian Hoefer
#"""
#This is an example how to use an ImageView with Matplotlib Colormaps (cmap).
#
#The function 'cmapToColormap' converts the Matplotlib format to the internal 
#format of PyQtGraph that is used in the GradientEditorItem. The function 
#itself has no dependencies on Matplotlib! Hence the weird if clauses with 
#'hasattr' instead of 'isinstance'.
#
#The class 'MplCmapImageView' demonstrates, how to integrate converted
#colormaps into a GradientEditorWidget. This is just monkey patched into the 
#class and should be implemented properly into the GradientEditorItem's 
#constructor. But this is one way to do it, if you don't want to touch your
#PyQtGraph installation.
#
#The 'main' block is just the modified 'ImageView' example from pyqtgraph.
#"""
#
#
#import numpy as np
#from pyqtgraph.Qt import QtCore, QtGui
#import pyqtgraph
#
## additional imports for this to work ...
#import collections
#import matplotlib.cm
#
#
#def cmapToColormap(cmap, nTicks=16):
#    """
#    Converts a Matplotlib cmap to pyqtgraphs colormaps. No dependency on matplotlib.
#
#    Parameters:
#    *cmap*: Cmap object. Imported from matplotlib.cm.*
#    *nTicks*: Number of ticks to create when dict of functions is used. Otherwise unused.
#    """
#
#    # Case #1: a dictionary with 'red'/'green'/'blue' values as list of ranges (e.g. 'jet')
#    # The parameter 'cmap' is a 'matplotlib.colors.LinearSegmentedColormap' instance ...
#    if hasattr(cmap, '_segmentdata'):
#        colordata = getattr(cmap, '_segmentdata')
#        if ('red' in colordata) and isinstance(colordata['red'], collections.Sequence):
#            # print("[cmapToColormap] RGB dicts with ranges")
#
#            # collect the color ranges from all channels into one dict to get unique indices
#            posDict = {}
#            for idx, channel in enumerate(('red', 'green', 'blue')):
#                for colorRange in colordata[channel]:
#                    posDict.setdefault(colorRange[0], [-1, -1, -1])[idx] = colorRange[2]
#
#            indexList = list(posDict.keys())
#            indexList.sort()
#            # interpolate missing values (== -1)
#            for channel in range(3):  # R,G,B
#                startIdx = indexList[0]
#                emptyIdx = []
#                for curIdx in indexList:
#                    if posDict[curIdx][channel] == -1:
#                        emptyIdx.append(curIdx)
#                    elif curIdx != indexList[0]:
#                        for eIdx in emptyIdx:
#                            rPos = (eIdx - startIdx) / (curIdx - startIdx)
#                            vStart = posDict[startIdx][channel]
#                            vRange = (posDict[curIdx][channel] - posDict[startIdx][channel])
#                            posDict[eIdx][channel] = rPos * vRange + vStart
#                        startIdx = curIdx
#                        del emptyIdx[:]
#            for channel in range(3):  # R,G,B
#                for curIdx in indexList:
#                    posDict[curIdx][channel] *= 255
#
#            posList = [[i, posDict[i]] for i in indexList]
#            return posList
#
#        # Case #2: a dictionary with 'red'/'green'/'blue' values as functions (e.g. 'gnuplot')
#        elif ('red' in colordata) and isinstance(colordata['red'], collections.Callable):
#            # print("[cmapToColormap] RGB dict with functions")
#            indices = np.linspace(0., 1., nTicks)
#            luts = [np.clip(np.array(colordata[rgb](indices), dtype=np.float), 0, 1) * 255 \
#                    for rgb in ('red', 'green', 'blue')]
#            return list(zip(indices, list(zip(*luts))))
#
#    # If the parameter 'cmap' is a 'matplotlib.colors.ListedColormap' instance, with the attributes 'colors' and 'N'
#    elif hasattr(cmap, 'colors') and hasattr(cmap, 'N'):
#        colordata = getattr(cmap, 'colors')
#        # Case #3: a list with RGB values (e.g. 'seismic')
#        if len(colordata[0]) == 3:
#            # print("[cmapToColormap] list with RGB values")
#            indices = np.linspace(0., 1., len(colordata))
#            scaledRgbTuples = [(rgbTuple[0] * 255, rgbTuple[1] * 255, rgbTuple[2] * 255) for rgbTuple in colordata]
#            return list(zip(indices, scaledRgbTuples))
#
#        # Case #3: a list of tuples with positions and RGB-values (e.g. 'terrain')
#        # -> this section is probably not needed anymore!?
#        elif len(colordata[0]) == 2:
#            # print("[cmapToColormap] list with positions and RGB-values. Just scale the values.")
#            scaledCmap = [(idx, (vals[0] * 255, vals[1] * 255, vals[2] * 255)) for idx, vals in colordata]
#            return scaledCmap
#
#    # Case #X: unknown format or datatype was the wrong object type
#    else:
#        raise ValueError("[cmapToColormap] Unknown cmap format or not a cmap!")
#
#
#class MplCmapImageView(pyqtgraph.ImageView):
#    def __init__(self, additionalCmaps=[], setColormap=None, **kargs):
#        super(MplCmapImageView, self).__init__(**kargs)
#
#        self.gradientEditorItem = self.ui.histogram.item.gradient
#
#        self.activeCm = "grey"
#        self.mplCmaps = {}
#
#        if len(additionalCmaps) > 0:
#            self.registerCmap(additionalCmaps)
#
#        if setColormap is not None:
#            self.gradientEditorItem.restoreState(setColormap)
#
#
#
#    def registerCmap(self, cmapNames):
#        """ Add matplotlib cmaps to the GradientEditors context menu"""
#        self.gradientEditorItem.menu.addSeparator()
#        savedLength = self.gradientEditorItem.length
#        self.gradientEditorItem.length = 100
#
#        # iterate over the list of cmap names and check if they're avaible in MPL
#        for cmapName in cmapNames:
#            if not hasattr(matplotlib.cm, cmapName):
#                print('[extendedimageview] Unknown cmap name: \'{}\'. Your Matplotlib installation might be outdated.'.format(cmapName))
#            else:
#                # create a Dictionary just as the one at the top of GradientEditorItem.py
#                cmap = getattr(matplotlib.cm, cmapName)
#                self.mplCmaps[cmapName] = {'ticks': cmapToColormap(cmap), 'mode': 'rgb'}
#
#                # Create the menu entries
#                # The following code is copied from pyqtgraph.ImageView.__init__() ...
#                px = QtGui.QPixmap(100, 15)
#                p = QtGui.QPainter(px)
#                self.gradientEditorItem.restoreState(self.mplCmaps[cmapName])
#                grad = self.gradientEditorItem.getGradient()
#                brush = QtGui.QBrush(grad)
#                p.fillRect(QtCore.QRect(0, 0, 100, 15), brush)
#                p.end()
#                label = QtGui.QLabel()
#                label.setPixmap(px)
#                label.setContentsMargins(1, 1, 1, 1)
#                act = QtGui.QWidgetAction(self.gradientEditorItem)
#                act.setDefaultWidget(label)
#                act.triggered.connect(self.cmapClicked)
#                act.name = cmapName
#                self.gradientEditorItem.menu.addAction(act)
#        self.gradientEditorItem.length = savedLength
#
#
#    def cmapClicked(self, b=None):
#        """onclick handler for our custom entries in the GradientEditorItem's context menu"""
#        act = self.sender()
#        self.gradientEditorItem.restoreState(self.mplCmaps[act.name])
#        self.activeCm = act.name
#
#
#
### Start Qt event loop unless running in interactive mode.
#if __name__ == '__main__':
#    import sys
#    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
#        app = QtGui.QApplication([])
#
#        ## Create window with ImageView widget
#        win = QtGui.QMainWindow()
#        win.resize(800,800)
#
#        # Instantiate the modified ImageView class ...
##        imv = pyqtgraph.ImageView()
#        imv = MplCmapImageView(additionalCmaps=['jet', 'viridis', 'seismic', 'cubehelix','Greens','Reds'])
#        imv = MplCmapImageView(additionalCmaps=['jet', 'viridis', 'seismic', 'cubehelix','Reds','Greens'])
#
#
#        win.setCentralWidget(imv)
#        win.show()
#        win.setWindowTitle('pyqtgraph example: ImageView')
#
#        ## Create random 3D data set with noisy signals
#        img = pyqtgraph.gaussianFilter(np.random.normal(size=(200, 200)), (5, 5)) * 20 + 100
#        img = img[np.newaxis,:,:]
#        decay = np.exp(-np.linspace(0,0.3,100))[:,np.newaxis,np.newaxis]
#        data = np.random.normal(size=(100, 200, 200))
#        data += img * decay
#        data += 2
#
#        ## Add time-varying signal
#        sig = np.zeros(data.shape[0])
#        sig[30:] += np.exp(-np.linspace(1,10, 70))
#        sig[40:] += np.exp(-np.linspace(1,10, 60))
#        sig[70:] += np.exp(-np.linspace(1,10, 30))
#
#        sig = sig[:,np.newaxis,np.newaxis] * 3
#        data[:,50:60,50:60] += sig
#
#
#        ## Display the data and assign each frame a time value from 1.0 to 3.0
#        imv.setImage(data, xvals=np.linspace(1., 3., data.shape[0]))
#
#        QtGui.QApplication.instance().exec_()

# %%

#import pyqtgraph as pg
#from pyqtgraph.Qt import QtCore, QtGui
#import numpy as np
#
#win = pg.GraphicsWindow()
#win.resize(800,350)
#win.setWindowTitle('pyqtgraph example: Histogram')
#plt1 = win.addPlot()
#plt2 = win.addPlot()
#
### make interesting distribution of values
##vals = np.hstack([np.random.normal(size=(500)), np.random.normal(size=260, loc=4)])
#vals = np.ones((500,500))
#for i in range(500):
#    for j in range(500):
#        vals[i,j] = i+j
### compute standard histogram
#y,x = np.histogram(vals, bins=np.linspace(-5, 1005, 254))
#
### Using stepMode=True causes the plot to draw two lines for each sample.
### notice that len(x) == len(y)+1
#plt1.plot(x, y, stepMode=True, fillLevel=0, brush=(0,0,255,150))
#
#### Now draw all points as a nicely-spaced scatter plot
##y = pg.pseudoScatter(vals, spacing=0.15)
###plt2.plot(vals, y, pen=None, symbol='o', symbolSize=5)
##plt2.plot(vals, y, pen=None, symbol='o', symbolSize=5, symbolPen=(255,255,255,200), symbolBrush=(0,0,255,150))
##
#### Start Qt event loop unless running in interactive mode or using pyside.
#if __name__ == '__main__':
#    import sys
#    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
#        QtGui.QApplication.instance().exec_()

# %%

#import pyqtgraph as pg
#from pyqtgraph.Qt import QtCore, QtGui
#import numpy as np
#
#win = pg.GraphicsWindow()
#win.setWindowTitle('pyqtgraph example: Scrolling Plots')
#
#
## 1) Simplest approach -- update data in the array such that plot appears to scroll
##    In these examples, the array size is fixed.
#p2 = win.addPlot()
#data1 = np.random.normal(size=300)
#curve2 = p2.plot(data1)
#ptr1 = 0
#def update1():
#    global data1, curve1, ptr1
##    data1[:-1] = data1[1:]  # shift data in the array one sample left
#    data1= np.roll(data1,-1)                        # (see also: np.roll)
#    data1[-1] = np.random.normal()
#    ptr1 += 1
#    curve2.setData(data1)
#    curve2.setPos(ptr1, 0)
#    
#
## 2) Allow data to accumulate. In these examples, the array doubles in length
##    whenever it is full. 
#win.nextRow()
#p4 = win.addPlot()
#p4.setDownsampling(mode='peak')
#p4.setClipToView(True)
#curve4 = p4.plot()
#
#data3 = np.empty(100)
#ptr3 = 0
#
#def update2():
#    global data3, ptr3
#    data3[ptr3] = np.random.normal()
#    ptr3 += 1
#    if ptr3 >= data3.shape[0]:
#        tmp = data3
#        data3 = np.empty(data3.shape[0] * 2)
#        data3[:tmp.shape[0]] = tmp
#
#    curve4.setData(data3[:ptr3])
#
## update all plots
#def update():
#    update1()
#    update2()
#timer = pg.QtCore.QTimer()
#timer.timeout.connect(update)
#timer.start(50)
#
#
#
### Start Qt event loop unless running in interactive mode or using pyside.
#if __name__ == '__main__':
#    import sys
#    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
#        QtGui.QApplication.instance().exec_()
#
#%%
#"""
#Demonstrates some customized mouse interaction by drawing a crosshair that follows 
#the mouse.
#
#
#"""
#
#import numpy as np
#import pyqtgraph as pg
#from pyqtgraph.Qt import QtGui, QtCore
#from pyqtgraph.Point import Point
#
##generate layout
#app = QtGui.QApplication([])
#win = pg.GraphicsWindow()
#win.setWindowTitle('pyqtgraph example: crosshair')
#label = pg.LabelItem(justify='right')
#win.addItem(label)
#
#p1 = win.addPlot(row=1, col=0)
#region = pg.LinearRegionItem()
#region.setZValue(10)
#
##pg.dbg()
#p1.setAutoVisible(y=True)
#
#
##create numpy arrays
##make the numbers large to show that the xrange shows data from 10000 to all the way 0
#data1 = 10000 + 15000 * pg.gaussianFilter(np.random.random(size=10000), 10) + 3000 * np.random.random(size=10000)
#data2 = 15000 + 15000 * pg.gaussianFilter(np.random.random(size=10000), 10) + 3000 * np.random.random(size=10000)
#
#p1.plot(data1, pen="r")
#p1.plot(data2, pen="g")
#
#
#def update():
#    region.setZValue(10)
#    minX, maxX = region.getRegion()
#    p1.setXRange(minX, maxX, padding=0)    
#
#region.sigRegionChanged.connect(update)
#
#def updateRegion(window, viewRange):
#    rgn = viewRange[0]
#    region.setRegion(rgn)
#
#p1.sigRangeChanged.connect(updateRegion)
#
#region.setRegion([1000, 2000])
#
##cross hair
#vLine = pg.InfiniteLine(angle=90, movable=False)
#hLine = pg.InfiniteLine(angle=0, movable=False)
#p1.addItem(vLine, ignoreBounds=True)
#p1.addItem(hLine, ignoreBounds=True)
#
#
#vb = p1.vb
#
#def mouseMoved(evt):
#    pos = evt[0]  ## using signal proxy turns original arguments into a tuple
#    if p1.sceneBoundingRect().contains(pos):
#        mousePoint = vb.mapSceneToView(pos)
#        index = int(mousePoint.x())
#        if index > 0 and index < len(data1):
#            label.setText("<span style='font-size: 12pt'>x=%0.1f,   <span style='color: red'>y1=%0.1f</span>,   <span style='color: green'>y2=%0.1f</span>" % (mousePoint.x(), data1[index], data2[index]))
#        vLine.setPos(mousePoint.x())
#        hLine.setPos(mousePoint.y())
#
#
#
#proxy = pg.SignalProxy(p1.scene().sigMouseMoved, rateLimit=60, slot=mouseMoved)
##p1.scene().sigMouseMoved.connect(mouseMoved)
#
#
### Start Qt event loop unless running in interactive mode or using pyside.
#if __name__ == '__main__':
#    import sys
#    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
#        QtGui.QApplication.instance().exec_()

#%% 
#!/usr/bin/env python
#-*- coding: utf-8 -*-
import numpy as np
import sys
#from PyQt4.Qt import *
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
#from PyQt4.Qt import QWidget, QPainter, QMainWindow,QRect,QPushButton,SIGNAL,QApplication
from PIL import Image
im = Image.open('Z:/German/FACU/Doctorado/Carpeta donde guardo las cosas/imagenScan.tiff')
#im.show()
#from PyQt5 import QtCore, QtWidgets
#from PyQt5.QtWidgets import QMainWindow, QWidget, QPushButton, QAction
#from PyQt5.QtCore import QSize
#from PyQt5.QtGui import QIcon

class MyPopup(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)

        self.traza_Widget2 = pg.GraphicsLayoutWidget()

        grid = QtGui.QGridLayout()
        self.setLayout(grid)

        self.p6 = self.traza_Widget2.addPlot(row=2,col=1,title="Traza")
        self.p6.showGrid(x=True, y=True)
        self.curve = self.p6.plot(open='y')

        self.curve.setData(np.array(im)[10])

        grid.addWidget(self.traza_Widget2,      0, 0)

    def paintEvent(self, e):
        dc = QtGui.QPainter(self)
        dc.drawLine(0, 0, 100, 100)
        dc.drawLine(100, 0, 0, 100)

class MainWindow(QtGui.QMainWindow):
    def __init__(self, *args):
        QtGui.QMainWindow.__init__(self, *args)
        self.cw = QtGui.QWidget(self)
        self.setCentralWidget(self.cw)
        self.btn1 = QtGui.QPushButton("Click me", self.cw)
        self.btn1.setGeometry(QtCore.QRect(0, 0, 100, 30))
        self.connect(self.btn1, QtCore.SIGNAL("clicked()"), self.doit)
        self.w = None



    def doit(self):
        print ("Opening a new popup window...")
        self.w = MyPopup()
        self.w.setGeometry(QtCore.QRect(100, 100, 400, 200))
        self.w.show()

class App(QtGui.QApplication):
    def __init__(self, *args):
        QtGui.QApplication.__init__(self, *args)
        self.main = MainWindow()
        self.connect(self, QtCore.SIGNAL("lastWindowClosed()"), self.byebye )
        self.main.show()

    def byebye( self ):
        self.exit(0)

def main(args):
    global app
    app = App(args)
    app.exec_()

if __name__ == "__main__":
    main(sys.argv)