# -*- coding: utf-8 -*-
"""
Created on Fri Jun  1 14:18:19 2018

@author: Cibion
"""

# -*- coding: utf-8 -*-
"""
Created on Wed Oct  1 13:41:48 2014
@authors: Federico Barabas, Luciano Masullo
"""

import numpy as np
import time
import scipy.ndimage as ndi
import matplotlib.pyplot as plt

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.dockarea import Dock, DockArea
import pyqtgraph.ptime as ptime

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar

import matplotlib.pyplot as plt
import matplotlib.figure
import matplotlib

class ScanWidget(QtGui.QFrame):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

#        imageWidget = pg.GraphicsLayoutWidget()
#        self.vb = imageWidget.addViewBox(row=1, col=1)



        # LiveView Button
        
        self.liveviewButton = QtGui.QPushButton('confocal LIVEVIEW')
#        self.liveviewButton.setCheckable(True)
        self.liveviewButton.clicked.connect(self.liveview)    
        
        # Scanning parameters
        
#        self.initialPositionLabel = QtGui.QLabel('acel vback/V [x0, y0] (µm)')
#        self.initialPositionEdit = QtGui.QLineEdit('120 25')
        self.scanRangeLabel = QtGui.QLabel('Scan range (µm)')
        self.scanRangeEdit = QtGui.QLineEdit('10')
        self.pixelTimeLabel = QtGui.QLabel('Pixel time (ms)')
        self.pixelTimeEdit = QtGui.QLineEdit('0.01')
        self.numberofPixelsLabel = QtGui.QLabel('Number of pixels')
        self.numberofPixelsEdit = QtGui.QLineEdit('500')
        self.pixelSizeLabel = QtGui.QLabel('Pixel size (nm)')
        self.pixelSizeValue = QtGui.QLabel('')
        
        self.numberofPixelsEdit.textChanged.connect(self.paramChanged)
        self.scanRangeEdit.textChanged.connect(self.paramChanged)
        self.pixelTimeEdit.textChanged.connect(self.paramChanged)
#        self.initialPositionEdit.textChanged.connect(self.paramChanged)

        self.aLabel = QtGui.QLabel('aceleration (µm/ms2)')
        self.aEdit = QtGui.QLineEdit('120')
        self.mLabel = QtGui.QLabel('Vback (µm/ms)')
        self.mEdit = QtGui.QLineEdit('10')
        self.aEdit.textChanged.connect(self.paramChanged)
        self.mEdit.textChanged.connect(self.paramChanged)

        self.startXLabel = QtGui.QLabel('startX')
        self.startXEdit = QtGui.QLineEdit('0')
        self.startXEdit.textChanged.connect(self.paramChanged)
        self.paramChanged()



        self.paramWidget = QtGui.QWidget()
        
        grid = QtGui.QGridLayout()
        self.setLayout(grid)
#        grid.addWidget(imageWidget, 0, 0)
        grid.addWidget(self.paramWidget, 1, 1)
        
        subgrid = QtGui.QGridLayout()
        self.paramWidget.setLayout(subgrid)
        subgrid.addWidget(self.liveviewButton, 14, 1,2,2)
#        subgrid.addWidget(self.initialPositionLabel, 0, 1)
#        subgrid.addWidget(self.initialPositionEdit, 1, 1)
        subgrid.addWidget(self.aLabel, 0, 1)
        subgrid.addWidget(self.aEdit, 1, 1)
        subgrid.addWidget(self.mLabel, 2, 1)
        subgrid.addWidget(self.mEdit, 3, 1)
        subgrid.addWidget(self.scanRangeLabel, 4, 1)
        subgrid.addWidget(self.scanRangeEdit, 5, 1)
        subgrid.addWidget(self.pixelTimeLabel, 6, 1)
        subgrid.addWidget(self.pixelTimeEdit, 7, 1)
        subgrid.addWidget(self.numberofPixelsLabel, 8, 1)
        subgrid.addWidget(self.numberofPixelsEdit, 9, 1)
        subgrid.addWidget(self.pixelSizeLabel, 10, 1)
        subgrid.addWidget(self.pixelSizeValue, 11, 1)
        subgrid.addWidget(self.startXLabel, 12, 1)
        subgrid.addWidget(self.startXEdit, 13, 1)

        self.figure = matplotlib.figure.Figure()
#        plt.close(self.figure)        
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
#        grid.addWidget(self.canvas, 0, 5, 10, 1)
        grid.addWidget(self.toolbar, 0, 0,)
        grid.addWidget(self.canvas,1,0)
        self.paramWidget.setFixedHeight(300)

        self.liveview()

    def paramChanged(self):
        
        self.scanRange = float(self.scanRangeEdit.text())
        self.numberofPixels = int(self.numberofPixelsEdit.text())
        self.pixelTime = float(self.pixelTimeEdit.text())
#        self.initialPosition = np.array(self.initialPositionEdit.text().split(' '))
        self.a = float(self.aEdit.text())
        self.m = float(self.mEdit.text())
        self.startX = float(self.startXEdit.text())

        self.pixelSize = 1000*self.scanRange/self.numberofPixels

        self.pixelSizeValue.setText('{}'.format(np.around(self.pixelSize, 2)))

        
        size = (self.numberofPixels, self.numberofPixels)
        
        self.inputImage = 100 * np.random.normal(size=size)
        self.blankImage = np.zeros(size)
        self.image = self.blankImage
        self.i = 0
        
            # This is the function triggered by pressing the liveview button
    def liveview(self):
        """
        a = self.a  # aceleracion um/ms2
        #m = 15  # Velocidad de vuelta respecto a la de ida
        av = a # a vuelta
#        """

        R = self.scanRange  # rango
        Npix = self.numberofPixels  # numerode pixeles
        tpix = self.pixelTime  # tiempo de pixel en ms
        T = tpix * Npix  # tiempo total de la linea
        V = (R/T)  # velocidad de la rampa
        #V = 100  # um/ms
        m=self.m
        #Npuntos= int(R / reDAQ)
        #rate = Npuntos / T
        rate = (1/tpix)  # 10**5 * 10**-3
        Npuntos = int(rate*T)
#        """
        a = (200*R)/((Npix*tpix)**2)
        av=a
#        """

#        x0 = 0
#        V0 = 0  #==> c=0
        startX = self.startX #0
        #quiero ver cuando alcanza velocidad V (a*ti =V )
        ti = V / a
        #xi = a*ti**2 + V0*ti  # no lo uso
        Ni = int(np.ceil(ti * rate)) +10  # xipuntos
        tiempoi=np.linspace(0,ti,Ni)
        xti=np.zeros(Ni)
        for i in range(Ni):
            xti[i] = 0.5*a*((tiempoi[i])**2-tiempoi[-1]**2) + startX  # + V0*tiempoi[i]
        
        rampax = np.linspace(xti[-1],R+xti[-1],int(Npuntos))
        
        #ahora la otra parte. Llega con vel V a xr=R+xi, en tr=T+ti
        xr = xti[-1] + R
#        tr = T +ti
        # ==> tr=0 por comodidad, despues lo corro
        #a*tr + c =V. 0.5*a*tr**2 + c*tr + d = xr
        c=V
        d=xr
        
        ##Busco a que tiempo alcanza velocidad -m*V: -a*tcasi +c = -m*V
        
        tcasi =-(c+(m*V))/-a
        #xcasi = -0.5*a*tcasi**2 + c*tcasi + d  # no lo uso
        Ncasi = int(np.ceil(tcasi * rate)) +10 # xchangepuntos
        tiempocasi=np.linspace(0,tcasi,Ncasi)  # tiempofin
        xtcas=np.zeros(Ncasi)  # xchange
        for i in range(Ncasi):
            xtcas[i] = -0.5*a*(tiempocasi[i]**2) + c*tiempocasi[i] + d
        
        # por ultimo, quiero que baje con vel = -m*V lineal. tarda t=x/-m*V
        
        tflip = m*V/(av)  # tlow
        xflip = 0.5*(av)*(tflip**2) + startX  # xlow
        
        #tfin=(xflip-xtcas[-1]/(-m*V)) + tr + tcasi
        Nfin = abs(int(np.round(((xflip-xtcas[-1])/((-m*V))*rate))))  # Nvuelta
        #Nfin = Npuntos /m
        Nflip = int(np.ceil(tflip * rate)) +10 # xlowpuntos

        # Una curva mas para la repeticion de cada señal. 
        #nuevamente salgo de vel = 0 y voy para atras en el tiempo
        #  en t0 v=0, x=0;; a*tflip = m*V
        """
        # -a*tfin + f = -m*V ==> f = m*V/a*tfin ;;; -a *tflip + f = 0 ==> tflip = f/a ;;; 
        #f = -m*V/(-a*tfin)
        """
        
        if xtcas[-1] < xflip:
            if xtcas[-1] < startX:
                q = np.where(xtcas<=startX)[0][0]
                xtcas = xtcas[:q]
                print("! xtcas < 0")
                rfin = np.linspace(0,0,2) + startX  # xback
        
            else:
                q = np.where(xtcas<=xflip)[0][0]
                xtcas = xtcas[:q]
                rfin = np.linspace(xflip,startX,Nfin)
                print("xtcas < xflip")
            rflip = np.linspace(0,0,2) + startX
            print("a")
        else:
        
            rfin= np.linspace(xtcas[-1],xflip,Nfin)
        
            tiempoflip=np.linspace(0,tflip,Nflip)  # tiempolow
            print("normal")
            rflip=np.zeros(Nflip)
            for i in range(Nflip):
                rflip[i] = 0.5*(av)*(tiempoflip[i]**2) + startX  # xstops
            
            rflip = np.flip(rflip,axis=0)
            
            #rflip =np.flip(xti,axis=0)
        print(Ni, "Ni\n",Npuntos, "Npuntos\n", Ncasi, "Ncasi\n",
              Nfin, "Nfin\n", Nflip, "Nflip\n")
        barridox = np.concatenate((          xti[:-1],            rampax[:],        xtcas[1:-1], rfin[:],rflip[1:]))
        verxi= np.concatenate(  (            xti[:-1],np.zeros(len(rampax)),np.zeros(len(xtcas)-2), np.zeros(len(rfin)), np.zeros(len(rflip)-1)))
        verxcas= np.concatenate((np.zeros(len(xti)-1),np.zeros(len(rampax)),        xtcas[1:-1]   , np.zeros(len(rfin)), np.zeros(len(rflip)-1)))
        verfin= np.concatenate( (np.zeros(len(xti)-1),np.zeros(len(rampax)),np.zeros(len(xtcas)-2),        rfin[:]     , np.zeros(len(rflip)-1)))
        verflip =np.concatenate((np.zeros(len(xti)-1),np.zeros(len(rampax)),np.zeros(len(xtcas)-2), np.zeros(len(rfin)),          rflip[1:]    ))

        
        #tvuelta = np.linspace(0, (-xcasi/(-m*V)), Nfin)+tr+tcasi
        
        #ejex = np.concatenate((tiempoi[:-1],np.linspace(ti,tr,Npuntos)[:] , tiempocasi[:]+tr,
        #                       tvuelta[1:-1], tiempoflip+tvuelta[-1]))
        
        #resta=np.zeros((len(barridox)))
        #for i in range(1,len(barridox)):
        #    resta[i] = barridox[i] - barridox[i-1]
        self.figure.clf()
        ax = self.figure.add_subplot(111)
        ax.autoscale(True)
#        plt.subplots_adjust(left=0.25, bottom=0.25)
        ax.set_title('Curva del barrido en x')
        ax.set_xlabel('Puntos')
        ax.set_ylabel('Moviemiento X (nm)')
        ax.minorticks_on()
        ax.grid(color='k',which='major', linestyle='-', linewidth=0.1)
        ax.grid(color='b',which='minor', linestyle='-', linewidth=0.05)
#        ax.grid(b=True, which='minor', color='b', linestyle='--')
    #    plt.figure(1)
        ax.plot(barridox,'.-')

        ax.plot(verfin,'.-c')
        ax.plot(verxcas, '.-g')
        ax.plot(verxi, '.-m')
        ax.plot(verflip, '.-y')
        self.canvas.draw_idle()
    
        #plt.plot(resta,'r.-')
        #plt.xlim(-0.5,10)
        #plt.ylim(-0.1,0.1)
        #
        #plt.plot(ejex, barridox, '.-')
        ##
        #plt.plot(ejex,verfin, '.c')
        #plt.plot(ejex,verxcas, '.g')
        #plt.plot(ejex,verxi, '.m')
        #
        #plt.plot(ejex,resta,'*-r')
        
        #plt.plot(xti)
        #cuantos puntos tengo entre tcasi y tr?
        
        #Ny=3
        #
        #
        #startY = 0
        #stepy = R/Ny
        #rampay = np.ones(len(barridox))*startY
        #
        #muchasrampasy=np.tile(rampay,(Ny,1))
        #barridoychico=np.zeros((Ny,len(rampay)))
        #
        #p = len(xti)-1 + len(rampax)-1 + int(len(xtcas))
        #for i in range(Ny):
        #
        #    barridoychico[i,:p]= muchasrampasy[i,:p] + (i)*stepy
        #    barridoychico[i,p:]= muchasrampasy[i,p:] + (i+1)*stepy
        #
        #
        #todo = np.tile(barridox,Ny)
        #barridoy = barridoychico.ravel()
        ###
        #plt.figure(2)
        #plt.plot(todo,'.-')
        #plt.plot(barridoy, 'y')
#
#plt.show()
#    def liveviewStart(self):
#        
#        self.viewtimer.start(self.linetime)
#        
#    def liveviewStop(self):
#        
#        self.viewtimer.stop()
#        
#    def updateView(self):
#        
#        self.lineData = self.inputImage[:, self.i]
#        self.image[:, self.numberofPixels-1-self.i] = self.lineData
#        
#        self.img.setImage(self.image, autoLevels=False)
#        
#        if self.i < self.numberofPixels-1:
#            self.i = self.i + 1
#        else:
#            self.i = 0
#            self.inputImage = 100 * np.random.normal(size=(self.numberofPixels))#, self.numberofPixels))
#

if __name__ == '__main__':

    app = QtGui.QApplication([])
    win = ScanWidget()
#    win = FileDialog()
    win.show()  
    
    app.exec_()
### Start Qt event loop unless running in interactive mode or using pyside.
#if __name__ == '__main__':
#    import sys
#    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
#        QtGui.QApplication.instance().exec_()