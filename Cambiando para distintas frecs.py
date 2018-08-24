
import numpy as np
#import time
#import scipy.ndimage as ndi
import matplotlib.pyplot as plt

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui

#from pyqtgraph.dockarea import Dock, DockArea
import pyqtgraph.ptime as ptime

#from PIL import Image


import nidaqmx

device = nidaqmx.system.System.local().devices['Dev1']

convFactors = {'x': 25, 'y': 25, 'z': 1.683}
# la calibracion es 1 µm = 40 mV en x,y (galvos);
# en z, 0.17 µm = 0.1 V  ==> 1 µm = 0.58 V
# 1.68 um = 1 V ==> 1 um = 0.59V  # asi que promedie.
minVolt = {'x': -10, 'y': -10, 'z': 0}
maxVolt = {'x': 10, 'y': 10, 'z': 10}
resolucionDAQ = 0.0003 * 2 * convFactors['x'] # V => µm; uso el doble para no errarle


class ScanWidget(QtGui.QFrame):

    def steptype(self):
        if self.working == False:
            self.paramChanged()
        if self.stepcheck.isChecked():
#            self.img.setImage(self.image, autoLevels=True)
            a=a+1
        else:
            verxi = np.concatenate((self.xini[:-1],
                                   np.zeros(len(self.wantedrampx)),
                                   np.zeros(len(self.xchange[1:])),
                                   np.zeros(len(self.xback[1:-1])),
                                   np.zeros(len(self.xstops))))

    #        verxbar = np.concatenate((np.zeros(len(self.xini[:-1])),
    #                               ((self.wantedrampx)),
    #                               np.zeros(len(self.xchange[1:])),
    #                               np.zeros(len(self.xback[1:-1])),
    #                               np.zeros(len(self.xstops))))

            verxchange = np.concatenate((np.zeros(len(self.xini[:-1])),
                                   np.zeros(len(self.wantedrampx)),
                                   ((self.xchange[1:])),
                                   np.zeros(len(self.xback[1:-1])),
                                   np.zeros(len(self.xstops))))

            verxback = np.concatenate((np.zeros(len(self.xini[:-1])),
                                   np.zeros(len(self.wantedrampx)),
                                   np.zeros(len(self.xchange[1:])),
                                   ((self.xback[1:-1])), 
                                   np.zeros(len(self.xstops))))

            verxstops = np.concatenate((np.zeros(len(self.xini[:-1])),
                                   np.zeros(len(self.wantedrampx)),
                                   np.zeros(len(self.xchange[1:])),
                                   np.zeros(len(self.xback[1:-1])),
                                   self.xstops))


            plt.plot(verxi,'*-m')
            plt.plot(self.onerampx * convFactors['x'],'b.-')
            plt.plot(verxchange,'.-g')
            plt.plot(verxback,'.-c')
            plt.plot(verxstops,'*-y')
            plt.plot(self.onerampy[0,:],'k')
            plt.plot(self.onerampy[1,:],'k')
            plt.show()


    def __init__(self, device, *args, **kwargs):  # agregue device

        super().__init__(*args, **kwargs)

        self.nidaq = device  # esto tiene que ir

        imageWidget = pg.GraphicsLayoutWidget()
        self.vb = imageWidget.addViewBox(row=1, col=1)

    # Parameters for smooth moving (to no go hard on the piezo (or galvos))
        self.moveTime = 0.01  # total time to move(s)
        self.moveSamples = 1000  # samples to move
        self.moveRate = self.moveSamples / self.moveTime  # 10**5

        self.activeChannels = ["x", "y", "z"]
        self.AOchans = [0, 1, 2]

    # LiveView Button

        self.liveviewButton = QtGui.QPushButton('confocal LIVEVIEW')
        self.liveviewButton.setCheckable(True)
        self.liveviewButton.clicked.connect(self.liveview)

    # save image Button

        self.saveimageButton = QtGui.QPushButton('Scan and Save')
        self.saveimageButton.setCheckable(True)
        self.saveimageButton.clicked.connect(self.saveimage)
        self.saveimageButton.setStyleSheet(
                "QPushButton { background-color: gray; }"
                "QPushButton:pressed { background-color: blue; }")

    # useful Booleans
        self.canales = False
        self.inStart = False
        self.working = False


    # Defino el tipo de Scan que quiero

        self.scanMode = QtGui.QComboBox()
        self.scanModes = ['apdrate', 'full', 'pixel']  # ahora estoy probando frecuencias
        self.scanMode.addItems(self.scanModes)

        self.stepcheck = QtGui.QCheckBox('Scan Barckward')
        self.stepcheck.clicked.connect(self.steptype)
        self.step = False

    # Scanning parameters

        self.initialPositionLabel = QtGui.QLabel('Initial Pos [x0 y0 z0] (µm)')
        self.initialPositionEdit = QtGui.QLineEdit('0 0 1')
        self.scanRangeLabel = QtGui.QLabel('Scan range (µm)')
        self.scanRangeEdit = QtGui.QLineEdit('5')
        self.pixelTimeLabel = QtGui.QLabel('Pixel time (ms)')
        self.pixelTimeEdit = QtGui.QLineEdit('0.01')
        self.numberofPixelsLabel = QtGui.QLabel('Number of pixels')
        self.numberofPixelsEdit = QtGui.QLineEdit('500')
        self.pixelSizeLabel = QtGui.QLabel('Pixel size (nm)')
        self.pixelSizeValue = QtGui.QLabel('')
        self.acelerationLabel = QtGui.QLabel('Acceleration (µm/ms^2)')
        self.acelerationEdit = QtGui.QLineEdit('120')
        self.vueltaLabel = QtGui.QLabel('Back Velocity (relative)')
        self.vueltaEdit = QtGui.QLineEdit('15')

        self.triggerLabel = QtGui.QLabel('Trigger ')
        self.triggerEdit = QtGui.QLineEdit('5000')

        self.timeTotalLabel = QtGui.QLabel('total scan time (s)')
        self.timeTotalValue = QtGui.QLabel('')

        self.numberofPixelsEdit.textChanged.connect(self.paramChanged)
        self.scanRangeEdit.textChanged.connect(self.paramChanged)
        self.pixelTimeEdit.textChanged.connect(self.paramChanged)
        self.initialPositionEdit.textChanged.connect(self.paramChanged)
        self.acelerationEdit.textChanged.connect(self.paramChanged)
        self.vueltaEdit.textChanged.connect(self.paramChanged)
        self.scanMode.textChanged.connect(self.paramChanged)
        self.paramChanged()

        self.paramWidget = QtGui.QWidget()

        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        grid.addWidget(imageWidget, 0, 0)
        grid.addWidget(self.paramWidget, 0, 1)

        subgrid = QtGui.QGridLayout()
        self.paramWidget.setLayout(subgrid)
        subgrid.addWidget(self.liveviewButton, 10, 1)
        subgrid.addWidget(self.initialPositionLabel, 0, 1)
        subgrid.addWidget(self.initialPositionEdit, 1, 1)
        subgrid.addWidget(self.scanRangeLabel, 2, 1)
        subgrid.addWidget(self.scanRangeEdit, 3, 1)
        subgrid.addWidget(self.pixelTimeLabel, 4, 1)
        subgrid.addWidget(self.pixelTimeEdit, 5, 1)
        subgrid.addWidget(self.numberofPixelsLabel, 6, 1)
        subgrid.addWidget(self.numberofPixelsEdit, 7, 1)
        subgrid.addWidget(self.acelerationLabel, 6, 2)
        subgrid.addWidget(self.acelerationEdit, 7, 2)
        subgrid.addWidget(self.vueltaLabel, 8, 2)
        subgrid.addWidget(self.vueltaEdit, 9, 2)
        subgrid.addWidget(self.pixelSizeLabel, 8, 1)
        subgrid.addWidget(self.pixelSizeValue, 9, 1)
        subgrid.addWidget(self.timeTotalLabel, 13, 1)
        subgrid.addWidget(self.timeTotalValue, 14, 1)
        subgrid.addWidget(self.stepcheck, 11, 2)

        subgrid.addWidget(self.triggerLabel, 4, 2)
        subgrid.addWidget(self.triggerEdit, 5, 2)

        subgrid.addWidget(self.scanMode, 12, 1)
        subgrid.addWidget(self.saveimageButton, 15, 1)  #

        self.paramWidget.setFixedHeight(400)

        self.vb.setMouseMode(pg.ViewBox.RectMode)
        self.img = pg.ImageItem()
        self.img.translate(-0.5, -0.5)
        self.vb.addItem(self.img)
        self.vb.setAspectLocked(True)
        imageWidget.setAspectLocked(True)
        self.hist = pg.HistogramLUTItem(image=self.img)
        self.hist.gradient.loadPreset('thermal')
        self.hist.vb.setLimits(yMin=0, yMax=66000)


        for tick in self.hist.gradient.ticks:
            tick.hide()
        imageWidget.addItem(self.hist, row=1, col=2)

# TO DO:      self.ROI = guitools.ROI((0, 0), self.vb, (0, 0), handlePos=(1, 0),
#                               handleCenter=(0, 1), color='y', scaleSnap=True,
#                               translateSnap=True)

        self.viewtimer = QtCore.QTimer()
        self.viewtimer.timeout.connect(self.updateView)


    def paramChanged(self):
        """ Update the parameters when the user edit them """

        self.scanRange = float(self.scanRangeEdit.text())
        self.numberofPixels = int(self.numberofPixelsEdit.text())
        self.pixelTime = float(self.pixelTimeEdit.text()) / 10**3  # seconds
        self.initialPosition = np.array(
                        self.initialPositionEdit.text().split(' '))

        self.apdrate = 10**5  # 20*10**6  # samples/seconds
        self.Napd = int(np.round(self.apdrate * self.pixelTime))
        print(self.Napd, "=Napd\n")

        self.pixelSize = self.scanRange/self.numberofPixels

        self.pixelSizeValue.setText('{}'.format(np.around(
                                        1000 * self.pixelSize, 2)))  # en nm

        self.linetime = self.pixelTime * self.numberofPixels  # en s


#        print(self.linetime, "linetime")

        self.timeTotalValue.setText('{}'.format(np.around(
                         self.numberofPixels * self.linetime, 2)))

        size = (self.numberofPixels, self.numberofPixels)

        if self.scanMode.currentText() == "full":
            self.sampleRate = (self.scanRange /resolucionDAQ) / (self.linetime)
            self.nSamplesrampa = int(np.ceil(self.scanRange /resolucionDAQ))
            print("a full resolucion\n",
                  self.nSamplesrampa, "Nsamples", self.sampleRate, "sampleRate")

        if self.scanMode.currentText() == "apdrate":
            self.sampleRate = self.apdrate 
            self.nSamplesrampa = self.sampleRate * self.linetime
            print("iguales frecuencias\n",
                  self.nSamplesrampa, "Nsamples", self.sampleRate, "sampleRate")

        if self.scanMode.currentText() == "pixel":
            self.nSamplesrampa = self.numberofPixels
            self.sampleRate = 1 / self.pixelTime
            print("los Npix que corresponden y 1/tpix de frecuencia\n",
                  self.nSamplesrampa, "Nsamples", self.sampleRate, "sampleRate")

#        print(self.sampleRate, "sampleRate\n",
#              self.nSamplesrampa, "nSamplesrampa")
#        print(nSamplesrampa, "nSamplesrampa")

        self.barridos()

        self.reallinetime = len(self.onerampx) * self.pixelTime  # seconds
        print(self.linetime, "linetime\n", self.reallinetime, "reallinetime")

#        self.inputImage = 10 * np.random.normal(size=size)
        self.blankImage = np.zeros(size)
        self.image = self.blankImage

        self.dy = 0

#        self.counts = np.zeros((len(self.wantedrampx)))
        self.counts = np.zeros((self.numberofPixels))

      # numberofpixels + pixelsoffL is the relevant part of the total ramp.
        self.APD = np.zeros((((self.numberofPixels + self.pixelsofftotal)*self.Napd),
                             (self.numberofPixels)))


# cosas para el save image nuevo
    def saveimage(self):
        """ la idea es que escanee la zona deseada (desde cero) una sola vez,
        y guarde la imagen"""
        if self.saveimageButton.isChecked():
            self.save = True
            self.preRunTime()
            self.channelsOpen()
            self.saveimageButton.setText('Abort')
            self.liveviewStart()

        else:
            self.save = False
            print("Abort")
            self.saveimageButton.setText('retry Scan and Stop')
            self.liveviewStop()

# This is the function triggered by pressing the liveview button

    def liveview(self):
        """ Image live view when not recording
        """
        if self.liveviewButton.isChecked():
            self.save = False
            self.preRunTime()
            self.channelsOpen()
            self.liveviewStart()

        else:
            self.liveviewStop()

    def liveviewStart(self):

        self.movetoStart()
        self.iniciando()
        self.tic = ptime.time()
        self.viewtimer.start(2*self.reallinetime*10**3)  # imput in ms
#        if self.scanMode.currentText() == "step scan":
#        else:
#            print("solo anda el Step scan por ahora")

    def liveviewStop(self):
        if self.save:
#            print("listo el pollo")
            self.saveimageButton.setChecked(False)
            self.saveimageButton.setText('redo Scan and save')
            self.save = False
            self.movetoStart()
        self.working = False
        self.liveviewButton.setChecked(False)
        self.viewtimer.stop()
        self.done()

    def iniciando(self):
        self.working = True
    # Send the signals to the NiDaq, but only start when the trigger is on
        self.aotask.write(np.array([self.totalrampx,
                                    self.totalrampy,
                                    self.totalrampz]), auto_start=True)

        self.inStart = False
        print("ya arranca")
    # Starting the trigger. It have a controllable delay
        self.dotask.write(self.trigger, auto_start=True)

    def updateView(self):

#        tac = ptime.time()

    # The counter reads this numbers of points when the trigger starts
        self.APD[:, self.dy] = self.citask.read(
              ((self.numberofPixels + self.pixelsofftotal)*self.Napd))
                #len(self.onerampx)*self.Napd)

#        print((ptime.time()-tac)*10**3, "todo citask (ms)\n")

#        print("APD en i+1", self.APD[-1,self.dy])

#        toc = ptime.time()
    # have to analize the signal from the counter
        self.apdpostprocessing()


        self.image[:, -1-self.dy] = self.counts[:]


      # The plotting method is slow (2-3 ms each), so I´m plotting in packages
        multi5 = np.arange(0, self.numberofPixels, 10)  # looks like realtime
        if self.dy in multi5:
            self.img.setImage(self.image, autoLevels=True)

#        print(ptime.time()-toc, "time")

        if self.dy < self.numberofPixels-1:
            self.dy = self.dy + 1

        else:
            if self.save:
                self.saveFrame()

                self.saveimageButton.setText('End')
                self.liveviewStop()

            else:
    #            print(self.tiempolinea*10**3, "cada linea (ms)")
    #            self.movetoStart()
                print(ptime.time()-self.tic, "Tiempo imagen completa.")
                self.viewtimer.stop()
                self.dotask.stop()
                self.aotask.stop()
                self.citask.stop()
                self.liveviewStart()
    #            self.liveviewStop()
    #            self.liveview()



    def preRunTime(self):
        """
        if self.stepcheck.isChecked():
            self.sampleRate = (self.scanRange /resolucionDAQ) / (self.linetime)
            self.nSamplesrampa = int(np.ceil(self.scanRange /resolucionDAQ))


        else:
            self.sampleRate = self.apdrate 
            self.nSamplesrampa = self.sampleRate * self.linetime
#       """
        print(self.nSamplesrampa, "nSamplesrampa")


    def barridos(self):
        # arma los barridos con los parametros dados
        self.acceleration()

        #       Barrido x
#        startX = float(self.initialPosition[0])
        sizeX = self.scanRange
        Npuntos = self.nSamplesrampa  # self.numberofPixels  # 
        wantedrampx = np.linspace(0, sizeX, Npuntos) + self.xini[-1]

        self.onerampx = np.concatenate((self.xini[:-1],
                                             wantedrampx,
                                             self.xchange[1:],
                                             self.xback[1:-1],
                                             self.xstops)) / convFactors['x']
        self.wantedrampx = wantedrampx

        print(len(self.xini[:-1]), "xipuntos\n",
              len(wantedrampx), "Npuntos\n",
              len(self.xchange[1:]), "xchangepuntos\n",
              len(self.xback[1:-1]), "xbackpuntos\n",
              len(self.xstops), "xstopspuntos\n")

        self.totalrampx = np.tile(self.onerampx, self.numberofPixels)

        #       Barrido z (se queda en la posicion inicial)
        startZ = float(self.initialPosition[2])
        self.totalrampz = np.ones(len(self.totalrampx)) * startZ / convFactors['z']

#        #       Barrido y
        startY = float(self.initialPosition[1])
#        self.totalrampy = np.ones(len(self.totalrampx))*startY / convFactors['y']

        stepy = self.scanRange / self.numberofPixels
        rampay = np.ones(len(self.onerampx))*startY

        muchasrampasy = np.tile(rampay, (self.numberofPixels, 1))
        self.onerampy = np.zeros((self.numberofPixels, len(rampay)))

        p = len(self.xini[:-1]) + len(wantedrampx) + int(len(self.xchange[1:])/2)#·+ int(len(self.xback[1:-1])/2)
        for i in range(self.numberofPixels):
            self.onerampy[i, :p] = muchasrampasy[i, :p] + (i)  *stepy
            self.onerampy[i, p:] = muchasrampasy[i, p:] + (i+1)*stepy

        self.totalrampy = (self.onerampy.ravel()) / convFactors['y']


        """
    # La parte del apd
        NoffR = len(self.onerampx)-len(wantedrampx)-3
        NoffL = len(self.xini[:-1])
        
#        ttotal = (len(self.totalrampx)-3)/self.sampleRate
#        tposta = len(wantedrampx)/self.sampleRate # = T
        toffR = NoffR/self.sampleRate
        toffL = NoffL/self.sampleRate
        
#        Nposta = tposta* self.apdrate  # = Npix*Napd
        
#        print(self.apdrate, "apdrate")
#        print(Nposta, "Nposta", self.numberofPixels*self.Napd)
        
        self.NoffR = int(np.round(toffR *self.apdrate))
        self.NoffL = int(np.round(toffL *self.apdrate))
#        print(self.NoffR, "NoffR", self.NoffL, "NoffL")
#        print(toffR, "toffR", toffL, "toffL")
#        """



    def apdpostprocessing(self):
        """ takes the evergrowing valors from the counter measure and convert
        it in "number or events" """
#        tic = ptime.time()
#        Ntirar = self.NoffL+self.NoffR
#        NoffL = 0*self.pixelsoffL
#        Npix = self.numberofPixels
#        Nramp = Ntirar + Npix  # len(totalrampx)  # len(rampay)  # el largo de cara rampa sola (completa).
#        Ntotal = Nramp * Npix  # len(todo)  # len(totalrampy)  # que son todos los puntos de las rampas, despues corto.

#        Nramp = self.numberofPixels + self.NoffL + self.NoffR

        Napd = self.Napd

        j = self.dy

        if self.pixelsoffL == 0:
            self.counts[0] = self.APD[Napd-1,j] - self.APD[0,j]
        else:
            self.counts[0] = self.APD[(Napd*(1+self.pixelsoffL))-1,j]-self.APD[(Napd*(1+self.pixelsoffL-1))-1,j]

        for i in range(1, self.numberofPixels-1):
            ei = ((self.pixelsoffL+i) * Napd)-1
            ef = ((self.pixelsoffL+i+1) * Napd)-1
            self.counts[i] = self.APD[ef,j] - self.APD[ei,j]
#        self.counts[-1] = self.APD[-1,j] - self.counts[-2]
#        self.counts = counts
#        print((ptime.time()-tic)*10**3, "tiempo apdpostprocessing (ms)")


# -------Aceleracion----------------------------------------------
    def acceleration(self):
        """ it creates the smooths-edge signals to send to the piezo
        It´s just an u.a.r.m. movement equation"""  # MRUV
    #        aceleracion = 120  # µm/ms^2  segun inspector
        aceleration = float(self.acelerationEdit.text())  # editable
        T = self.numberofPixels * self.pixelTime * 10**3  # working in ms
        velocity = (self.scanRange / T)
        rate = self.sampleRate*10**-3

#        print(aceleration, "aceleracion\n", velocity, "velocidad\n",
#              T, "T(linea en ms)\n")
        startX = float(self.initialPosition[0])

        ti = velocity / aceleration
#        xi = 0.5*aceleration*(ti**2)
        xipuntos = int(np.ceil(ti * rate))

        xini = np.zeros(xipuntos)
        tiempoi = np.linspace(0,ti,xipuntos)
        for i in range(xipuntos):
            xini[i] = 0.5*aceleration*((tiempoi[i])**2) + startX

        xr = xini[-1] + self.scanRange
#        tr = T + ti

        m = float(self.vueltaEdit.text())
        # si busco una velocidad de vuelta Vdeseado veces mayor a la de ida
        tcasi = ((1+m) * velocity) / aceleration  # Vdeseado + V = -m*V
#        xcasi = -0.5 * aceleration * (tcasi**2) + velocity * tcasi  # +xr
#        xchangepuntos = abs(int(np.ceil((xcasi) / resolucionDAQ )))  # -xr
        xchangepuntos = int(np.ceil(tcasi * rate))
#        tiempofin = abs(tcasi/(xcasi / resolucionDAQ))
        tiempofin = np.linspace(0, tcasi, xchangepuntos)
        xchange = np.zeros(xchangepuntos)
        for i in range(xchangepuntos):
            xchange[i] = (-0.5*aceleration*((tiempofin[i])**2) + velocity * (tiempofin[i]) ) + xr

    # After the wanted ramp, it get a negative acceleration:
        av = aceleration  # *m
        tlow = m*velocity/av
#        print(tlow, "tlow")
        xlow = 0.5*av*(tlow**2)
#        print(xlow, "xlow")
#        tvuelta =int(np.ceil(((xchange[-1])/(m*velocity))))
        Nvuelta = abs(int(np.ceil(((xlow-xchange[-1])/(m*velocity)) * (rate))))

    # To avoid wrong going back in x
        if xchange[-1] < xlow + startX:
            if xchange[-1] < 0:
                q = np.where(xchange<=0)[0][0]
                xchange = xchange[:q]
                print("xchange < 0")
                self.xback = np.linspace(0,0,4)

            else:
                q = np.where(xchange <= xlow + startX)[0][0]
                xchange = xchange[:q]
                self.xback = np.linspace(xlow, 0, Nvuelta) + startX
                print("xchange < xlow")
            xstops = np.linspace(0,0,2)
        else:

            self.xback = np.linspace(xchange[-1], xlow+startX, Nvuelta)

            xlowpuntos = int(np.ceil(tlow * rate))
            tiempolow=np.linspace(0,tlow,xlowpuntos)
            print("without cut the ramps")
            xstops=np.zeros(xlowpuntos)
            for i in range(xlowpuntos):
                xstops[i] = 0.5*(av)*(tiempolow[i]**2)
                
            xstops=np.flip(xstops,axis=0)
        print("\n")
#        print(m*velocity, "v vuelta", Nvuelta, "Nvuelta")
#        print(np.round(tiempoi[-2]-tiempoi[-1], 4), "tiempoi\n",
#              np.round(tiempofin[-2]-tiempofin[-1], 4), "tiempofin\n",
#              np.round(1/rate, 4), "1/sampleRate")

        self.xini = xini
        self.xchange = xchange
        self.xstops = xstops

    # Don't want all the accelerated zones
        NoffL = len(xini[:-1])
        NoffR = len(xchange[1:]) + len(self.xback[1:-1]) + len(xstops)
        toffL = NoffL/self.sampleRate
        toffR = NoffR/self.sampleRate
#        toff = toffL + toffR
        self.pixelsoffL = int(np.round(toffL*self.apdrate)/self.Napd)
        self.pixelsoffR = int(np.round(toffR*self.apdrate)/self.Napd)
        self.pixelsofftotal = int(np.round((toffL+toffR)*self.apdrate)/self.Napd)
#        self.pixelsoffini = int(np.ceil(xipuntos / (self.pixelTime*self.sampleRate)))
        print(self.pixelsoffR+self.pixelsoffL, "pixelsoff total")

#        pixelsofffin = np.ceil(tcasi*self.sampleRate)
#        self.pixelsoffvuelta = len(self.xback) * self.sampleRate + pixelsofffin

#        self.puntosAPD = pixelsoffini + self.numberofPixels + self.pixelsoffvuelta

    def channelsOpen(self):
        """ Open and Config of all the channels for use"""

        if self.canales:
            print("Ya estan abiertos los canales")  # to dont open again 
            #  usando esto podria no cerrarlos nunca.
        else:
            self.canales = True
        # Create all the channels
            self.aotask = nidaqmx.Task('aotask')
            self.dotask = nidaqmx.Task('dotask')
#            self.aitask = nidaqmx.Task('aitask')
#            self.ditask = nidaqmx.Task('ditask')
            self.citask = nidaqmx.Task('citask')

        # Configure the counter channel to read the APD
            self.citask.ci_channels.add_ci_count_edges_chan(counter='Dev1/ctr0',
                                name_to_assign_to_channel=u'conter',
                                initial_count=0)

            totalcinumber = ((self.numberofPixels+self.pixelsofftotal)*self.Napd)*self.numberofPixels

            self.citask.timing.cfg_samp_clk_timing(
              rate=self.apdrate, sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
              source=r'100kHzTimebase',
              samps_per_chan = totalcinumber)  # int(len(self.totalrampx)*self.Napd))

    #        # Tengo que hacer que dotask accione el/los shutters.
        # Configure the digital channels to open/close shutters
    #        self.dotask.do_channels.add_do_chan(  # se ocuparia del shutter
    #            lines="Dev1/port0/line6", name_to_assign_to_lines='chan6',
    #            line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)  # Ger

        # Create the signal trigger
            triggerrate = self.apdrate
            num = int(self.triggerEdit.text())
            trigger = np.zeros((len(self.onerampx)*self.Napd),dtype="bool")

            trigger[:] = True
#            trigger1 = np.concatenate((trigger, np.zeros(100,dtype="bool")))  # 2ms de apagado, hace cosas raras
            trigger2 = np.tile(trigger, self.numberofPixels)

            self.trigger = np.concatenate((np.zeros(num,dtype="bool"), trigger2))

            print((num/self.apdrate)*10**3, "delay (ms)")  # "\n", num, "num elegido", 

        # Configure the digital channels to trigger the synchronization signal
            self.dotask.do_channels.add_do_chan(
                lines="Dev1/port0/line6", name_to_assign_to_lines='chan6',
                line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
    
            self.dotask.timing.cfg_samp_clk_timing(
                         rate=triggerrate,  # muestras por segundo
                         sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
    #                         source='100kHzTimebase',
                         active_edge = nidaqmx.constants.Edge.RISING,
                         samps_per_chan=len(self.trigger))


        # Following loop creates the voltage channels
            for n in range(len(self.AOchans)):
                self.aotask.ao_channels.add_ao_voltage_chan(
                    physical_channel='Dev1/ao%s' % self.AOchans[n],
                    name_to_assign_to_channel='chan_%s' % self.activeChannels[n],
                    min_val=minVolt[self.activeChannels[n]],
                    max_val=maxVolt[self.activeChannels[n]])

            self.aotask.timing.cfg_samp_clk_timing(
                rate=self.sampleRate,
#                source=r'100kHzTimeBase',
                sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                samps_per_chan=len(self.totalrampx))

        # Configure a start trigger to synchronizate the measure and movement
            triggerchannelname = "PFI4"
            self.aotask.triggers.start_trigger.cfg_dig_edge_start_trig(
                                trigger_source = triggerchannelname)#,
    #                                trigger_edge = nidaqmx.constants.Edge.RISING)
    
            self.citask.triggers.arm_start_trigger.dig_edge_src = triggerchannelname
            self.citask.triggers.arm_start_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_EDGE
#            self.citask.triggers.arm_start_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING

        # Pause trigger to get the signal on only when is a True in the referense
            self.aotask.triggers.pause_trigger.dig_lvl_src = triggerchannelname
            self.aotask.triggers.pause_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_LEVEL
            self.aotask.triggers.pause_trigger.dig_lvl_when = nidaqmx.constants.Level.LOW

            self.citask.triggers.pause_trigger.dig_lvl_src = triggerchannelname
            self.citask.triggers.pause_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_LEVEL
            self.citask.triggers.pause_trigger.dig_lvl_when = nidaqmx.constants.Level.LOW
        # En realidad mando un vector con muchos True's, asi que no lo uso

    def done(self):
        """ stop and close all the channels"""
        if self.canales:
#            print("Cierro todos los canales")  # para evitar el error
            self.aotask.stop()
            self.aotask.close()
            self.dotask.stop()
            self.dotask.close()
#            self.aitask.stop()  # Ger
#            self.aitask.close()  # Ger
#            self.ditask.stop()  # Ger
#            self.ditask.close()  # Ger
            self.citask.stop()
            self.citask.close()
#            self.nidaq.reset_device()
#            self.finalizeDone.emit()
            self.canales = False

        else:
            print("llego hasta el done pero no tenia nada que cerrar")
            # Esto no tendria que pasar

    def openShutter(self, color):
        if color == "red":
            print("abre shutter rojo")
#            self.dotask.write(5, auto_start=True)
# TOD O: Es una idea de lo que tendria que hacer la funcion

    def movetoStart(self):
        """ When called, it gets to the start point"""
        if self.inStart:
            print("is already in start")
        else:
            print("moving to start")
            self.done()
            N = self.moveSamples
    
    #         Creates the voltage channels to move "slowly"
            self.aotask = nidaqmx.Task('aotask')
            for n in range(len(self.AOchans)):
                self.aotask.ao_channels.add_ao_voltage_chan(
                    physical_channel='Dev1/ao%s' % self.AOchans[n],
                    name_to_assign_to_channel='chan_%s' % self.activeChannels[n],
                    min_val=minVolt[self.activeChannels[n]],
                    max_val=maxVolt[self.activeChannels[n]])
    
            self.aotask.timing.cfg_samp_clk_timing(
                rate=(self.moveRate),
                sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                samps_per_chan=N)
    
    #        tic = ptime.time()
            startY = float(self.initialPosition[1])
            maximoy = self.onerampy[-1, -1]
            volviendoy = np.linspace(maximoy, startY, N)
            volviendox = np.ones(len(volviendoy)) * float(self.initialPosition[0])
            volviendoz = np.ones(len(volviendoy)) * float(self.initialPosition[2])
            volviendotodo = np.zeros((len(self.AOchans), len(volviendoy)))
            volviendotodo[0, :] = volviendox / convFactors['x']
            volviendotodo[1, :] = volviendoy / convFactors['y']
            volviendotodo[2, :] = volviendoz / convFactors['z']
    
            self.aotask.write(
                 volviendotodo, auto_start=True)
            self.aotask.wait_until_done()
    #        print(np.round(ptime.time() - tic, 5)*10**3, "movetostart (ms)")
            self.dy = 0

            self.aotask.stop()
            self.aotask.close()

            self.channelsOpen()
            self.inStart = True

    def saveFrame(self):
        """ Config the path and name of the file to save, and save it"""
        print("\n Hipoteticamente Guardo la imagen\n")

#        name = str(self.edit_save.text())
#        filepath = "C:/Users/Santiago/Desktop/Germán Tesis de lic/Winpython (3.5.2 para tormenta)/WinPython-64bit-3.5.2.2/notebooks/Guardando tiff/"
#        timestr = time.strftime("%Y%m%d-%H%M%S")
#        name = str(filepath + "image-" + timestr + ".tiff")  # nombre con la fecha -hora
#        guardado = Image.fromarray(self.image)
#        guardado.save(name)

#        name = str(filepath + "imageVUELTA-" + timestr + ".tiff")  # nombre con la fecha -hora
#        guardado = Image.fromarray(self.imagevuelta)
#        guardado.save(name)



app = QtGui.QApplication([])
win = ScanWidget(device)
win.show()

app.exec_()


