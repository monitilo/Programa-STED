
import numpy as np
import time
#import scipy.ndimage as ndi
import matplotlib.pyplot as plt

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui

#from pyqtgraph.dockarea import Dock, DockArea
#import pyqtgraph.ptime as ptime

#from PIL import Image

#import multiprocessing as mp


import nidaqmx

device = nidaqmx.system.System.local().devices['Dev1']

convFactors = {'x': 25, 'y': 25, 'z': 1.683}
# la calibracion es 1 µm = 40 mV;
# en z, 0.17 µm = 0.1 V  ==> 1 µm = 0.58 V
# 1.68 um = 1 V ==> 1 um = 0.59V
minVolt = {'x': -10, 'y': -10, 'z': 0}
maxVolt = {'x': 10, 'y': 10, 'z': 10}
resolucionDAQ = 0.0003 * 2 * convFactors['x'] # V => µm; uso el doble para no errarle


def makeRamp(start, end, samples):
    return np.linspace(start, end, num=samples)


class ScanWidget(QtGui.QFrame):

    def steptype(self):
        if self.stepcheck.isChecked():
            print("Samplerate !=no=! 10**5")
            
        else:
            print("Samplerate = apdrate")
            verxi = np.concatenate((self.xini[:-1],
                                   np.zeros(len(self.barridonormal)),
                                   np.zeros(len(self.xfin[1:])),
                                   np.zeros(len(self.xvuelta[1:-1])),
                                   np.zeros(len(self.rlow))))
    
    #        verxbar = np.concatenate((np.zeros(len(self.xini[:-1])),
    #                               ((self.barridonormal)),
    #                               np.zeros(len(self.xfin[1:])),
    #                               np.zeros(len(self.xvuelta[1:-1])),
    #                               np.zeros(len(self.rlow))))
     
            verxfin = np.concatenate((np.zeros(len(self.xini[:-1])),
                                   np.zeros(len(self.barridonormal)),
                                   ((self.xfin[1:])),
                                   np.zeros(len(self.xvuelta[1:-1])),
                                   np.zeros(len(self.rlow))))
    
            verxvuelta = np.concatenate((np.zeros(len(self.xini[:-1])),
                                   np.zeros(len(self.barridonormal)),
                                   np.zeros(len(self.xfin[1:])),
                                   ((self.xvuelta[1:-1])), 
                                   np.zeros(len(self.rlow))))
    
            verrlow = np.concatenate((np.zeros(len(self.xini[:-1])),
                                   np.zeros(len(self.barridonormal)),
                                   np.zeros(len(self.xfin[1:])),
                                   np.zeros(len(self.xvuelta[1:-1])),
                                   self.rlow))
    
    #        plt.plot(self.barridoxchico)
            plt.plot(verxi,'*-m')
            plt.plot(self.barridoxchico * convFactors['x'],'b.-')
            plt.plot(verxfin,'.-g')
            plt.plot(verxvuelta,'.-c')
            plt.plot(verrlow,'*-y')
            plt.plot(self.barridoychico[0,:],'k')
            plt.plot(self.barridoychico[1,:],'k')
            plt.show()




    def keyPressEvent(self, e):

        if e.key() == QtCore.Qt.Key_Escape:
            self.close()
            self.liveviewStop()

    def __init__(self, device, *args, **kwargs):  # agregue device

        super().__init__(*args, **kwargs)

        self.nidaq = device  # esto tiene que ir

        imageWidget = pg.GraphicsLayoutWidget()
        self.vb = imageWidget.addViewBox(row=1, col=1)

#        imageWidget2 = pg.GraphicsLayoutWidget()
#        self.vb2 = imageWidget2.addViewBox(row=1, col=1)

        # Parameters for smooth moving (to no shake hard the piezo)
        self.moveTime = 0.1  # total time to move(s)
        self.moveSamples = 1000  # samples to move
        self.moveRate = self.moveSamples / self.moveTime
        self.activeChannels = ["x", "y", "z"]
        self.AOchans = [0, 1, 2]

        # LiveView Button

        self.liveviewButton = QtGui.QPushButton('confocal LIVEVIEW')
        self.liveviewButton.setCheckable(True)
        self.liveviewButton.clicked.connect(self.liveview)
#        self.liveviewButton.clicked.connect(self.channelsOpen)

        # save image Button

        self.saveimageButton = QtGui.QPushButton('Scan and Save')
        self.saveimageButton.setCheckable(True)
        self.saveimageButton.clicked.connect(self.saveimage)
        self.saveimageButton.setStyleSheet(
                "QPushButton { background-color: gray; }"
                "QPushButton:pressed { background-color: blue; }")

        # Defino el tipo de Scan que quiero

        self.scanMode = QtGui.QComboBox()
        self.scanModes = ['step scan', 'otro scan', 'tempesta scan']
        self.scanMode.addItems(self.scanModes)
#        self.scanMode.currentIndexChanged.connect(
#            lambda: self.setScanMode(self.scanMode.currentText()))

#        def setScanMode(self, mode):
##            self.stageScan.setScanMode(mode)
#            self.scanParameterChanged('scanMode')

        self.stepcheck = QtGui.QCheckBox('Scan Barckward')
        self.stepcheck.clicked.connect(self.steptype)
        self.step = False


        self.canales = False
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
        self.acelerationLabel = QtGui.QLabel('Aceleration (µm/ms^2)')
        self.acelerationEdit = QtGui.QLineEdit('120')
        self.vueltaLabel = QtGui.QLabel('Velocidad de vuelta V (V / Vida)')
        self.vueltaEdit = QtGui.QLineEdit('15')

        self.triggerLabel = QtGui.QLabel('Jugando con el trigger ')
        self.triggerEdit = QtGui.QLineEdit('2000')

        self.timeTotalLabel = QtGui.QLabel('tiempo total del escaneo (s)')
        self.timeTotalValue = QtGui.QLabel('')

        self.numberofPixelsEdit.textChanged.connect(self.paramChanged)
        self.scanRangeEdit.textChanged.connect(self.paramChanged)
        self.pixelTimeEdit.textChanged.connect(self.paramChanged)
        self.initialPositionEdit.textChanged.connect(self.paramChanged)
        self.acelerationEdit.textChanged.connect(self.paramChanged)
        self.vueltaEdit.textChanged.connect(self.paramChanged)
        self.paramChanged()

        self.paramWidget = QtGui.QWidget()

        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        grid.addWidget(imageWidget, 0, 0)
        grid.addWidget(self.paramWidget, 0, 1)
#        grid.addWidget(imageWidget2, 0, 2)

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

#        subgrid.addWidget(self.scanMode, 12, 1)
        subgrid.addWidget(self.saveimageButton, 15, 1)  #

        self.paramWidget.setFixedHeight(400)

        self.vb.setMouseMode(pg.ViewBox.RectMode)
#        self.vb2.setMouseMode(pg.ViewBox.RectMode)
        self.img = pg.ImageItem()
        self.img.translate(-0.5, -0.5)
        self.vb.addItem(self.img)
        self.vb.setAspectLocked(True)
#        self.vb2.addItem(self.img)
#        self.vb2.setAspectLocked(True)
        imageWidget.setAspectLocked(True)
#        imageWidget2.setAspectLocked(True)
        self.hist = pg.HistogramLUTItem(image=self.img)
        self.hist.gradient.loadPreset('thermal')
        self.hist.vb.setLimits(yMin=0, yMax=66000)
#        self.hist.vb2.setLimits(yMin=0, yMax=66000)

#        self.cubehelixCM = pg.ColorMap(np.arange(0, 1, 1/256),
#                                       guitools.cubehelix().astype(int))
#        self.hist.gradient.setColorMap(self.cubehelixCM)

        for tick in self.hist.gradient.ticks:
            tick.hide()
        imageWidget.addItem(self.hist, row=1, col=2)
#        imageWidget2.addItem(self.hist, row=1, col=2)

#        self.ROI = guitools.ROI((0, 0), self.vb, (0, 0), handlePos=(1, 0),
#                               handleCenter=(0, 1), color='y', scaleSnap=True,
#                               translateSnap=True)

        self.viewtimer = QtCore.QTimer()
        self.viewtimer.timeout.connect(self.updateView)


        self.APDtimer = QtCore.QTimer()
        self.APDtimer.timeout.connect(self.dibujando)

    def paramChanged(self):

        self.scanRange = float(self.scanRangeEdit.text())
        self.numberofPixels = int(self.numberofPixelsEdit.text())
        self.pixelTime = float(self.pixelTimeEdit.text()) / 10**3  # segs
        self.initialPosition = np.array(
                        self.initialPositionEdit.text().split(' '))

        self.apdrate = 10**5  # 20*10**6
        self.Napd = int(np.round(self.apdrate * self.pixelTime))
#        print(self.Napd, "=Napd\n")
        self.pixelSize = self.scanRange/self.numberofPixels

        self.pixelSizeValue.setText('{}'.format(np.around(
                                        1000 * self.pixelSize, 2)))  # en nm

#        self.linetime = (1 / 100000)*float(self.pixelTimeEdit.text()) * float(
#                                        self.numberofPixelsEdit.text())
        self.linetime = self.pixelTime * self.numberofPixels


        print(self.linetime, "linetime")

        self.timeTotalValue.setText('{}'.format(np.around(
                         self.numberofPixels * self.linetime, 2)))

        size = (self.numberofPixels, self.numberofPixels)

#        self.rampTime = self.linetime  # Time for each ramp in s
#        self.nSamplesrampa = int(np.ceil(self.scanRange /resolucionDAQ))
#        self.sampleRate = (self.scanRange /resolucionDAQ) / (self.linetime)
        self.sampleRate = 10**5
        self.nSamplesrampa = self.sampleRate * self.linetime

        print(self.sampleRate, "sampleRate\n", self.nSamplesrampa, "nSamplesrampa")
#        print(nSamplesrampa, "nSamplesrampa")

        self.barridos()
        self.otrotime = len(self.barridoxchico) * self.pixelTime
        print(self.otrotime, "otrotime")
        self.inputImage = 1 * np.random.normal(size=size)
        self.blankImage = np.zeros(size)
        self.image = self.blankImage
#        self.imagevuelta = np.zeros(size)
#        self.i = 0
        self.dy = 0

        self.image = np.zeros((len(self.barridoxchico), self.numberofPixels))


        self.contando = np.zeros((len(self.barridoxchico), (self.numberofPixels)))


# cosas para el save image nuevo
    def saveimage(self):
        """ la idea es que escanee la zona deseada (desde cero)
y guarde la imagen"""
        if self.saveimageButton.isChecked():
            self.save = True
            self.preRunTime()
            self.channelsOpen()
            self.movetoStart()
            self.saveimageButton.setText('Abort')
#            self.guarda = np.zeros((self.numberofPixels, self.numberofPixels))
            self.liveviewStart()

        else:
            self.save = False
            print("Abort")
            self.saveimageButton.setText('reintentar Scan and Stop')
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
        if self.scanMode.currentText() == "step scan":
            self.iniciando()
            self.viewtimer.start(self.linetime*10**3)
        else:
            print("solo anda el Step scan por ahora")

    def liveviewStop(self):
        if self.save:
#            print("listo el pollo")
            self.saveimageButton.setChecked(False)
            self.saveimageButton.setText('Otro Scan and Stop')
            self.save = False
#            self.movetoStart()

        self.liveviewButton.setChecked(False)
        self.viewtimer.stop()
        self.done()

    def iniciando(self):


        self.aotask.write(
           np.array([self.barridox,
            self.barridoy,  # + (self.dy * self.pixelSize / convFactors['y']),
            self.barridoz]), auto_start=True)
        print("ya arranca")
        self.dotask.write(self.trigger, auto_start=True)

    def updateView(self):

#        self.lineaida()

#        tac = time.time()
        self.contando[:,self.dy] = self.citask.read(len(self.barridoxchico))  # APDtodo
#        tec = time.time()
        self.citask.wait_until_done()
#        print(time.time()-tac, "todo citask\n", tec-tac,"sin el wait\n",
#              time.time()-tec, "solo el wait\n")
        self.apdpostprocessing()

#        toc = time.time()
        self.image[:, self.dy] = self.cuentas[:, self.dy]
        self.img.setImage(self.image, autoLevels=False)
#        print((time.time()-toc)*10**3, "Set Image (ms)\n")
#        print((time.time()-tac)*10**3)
#        self.image = np.zeros((len(self.barridoxchico), self.numberofPixels))

#        for i in range(self.numberofPixels):
#            self.image[:, -i] = self.cuentas[:,i]
#        tic = time.time()

#        self.img.setImage(self.image, autoLevels=True)

        if self.dy < self.numberofPixels-1:
#            self.i = self.i + 1
            self.dy = self.dy + 1
        else:
#            self.img.setImage(self.image, autoLevels=True)
#            self.dy = 0
#            print(self.tiempolinea*10**3, "cada linea (ms)")
            self.movetoStart()
            self.viewtimer.stop()
            self.aotask.stop()
            self.citask.stop()
            self.liveviewStart()
#            self.liveviewStop()
#            self.liveview()

        if self.save:
            self.guardarimagen()

            self.saveimageButton.setText('Fin')
            self.liveviewStop()

    def preRunTime(self):

        if self.stepcheck.isChecked():
            self.sampleRate = (self.scanRange /resolucionDAQ) / (self.linetime)
            self.nSamplesrampa = int(np.ceil(self.scanRange /resolucionDAQ))


        else:
            self.sampleRate = self.apdrate 
            self.nSamplesrampa = self.sampleRate * self.linetime

        print(self.nSamplesrampa, "nSamplesrampa")



    def dibujando(self):

        print("HACE ALGOO!!")
        self.contando[:,self.i] = self.citask.read(len(self.barridoxchico))  # APDtodo

        self.citask.wait_until_done()

        self.image[:, -self.i] = self.contando[:, self.i]  # no funciono asi nomas....
        self.img.setImage(self.image, autoLevels=True)
        print("HACE ALGOO 2")
        self.i = self.i +1


    def lineaida(self):
        tic = time.time()
        """
#        self.aotask.stop()
#        self.citask.stop()

        tiic = time.time()



#        self.i = 0
#        tiempo = len(self.barridoxchico) / (self.apdrate)
#        self.APDtimer.start(tiempo)


#        for i in range(self.numberofPixels):
##            tac = time.time()
#            self.i = i
#            self.contando[:,i] = self.citask.read(len(self.barridoxchico))  # APDtodo
#
##            toc = time.time()
##            self.image[:, -i] = self.contando[:, i]  # no funciono asi nomas....
##            self.img.setImage(self.image, autoLevels=True)
#
#            self.citask.wait_until_done()
##            print((tac-toc)*10**3, "Citask time")
##            self.citask.stop()
            
        tec = time.time()

#        self.aotask.wait_until_done()

#        self.APDtimer.stop()

#        self.aotask.stop()
#        self.citask.stop()

        tuc = time.time()
        print("\ncitask solo Real (ms) = ", np.round((tec-tiic), 5)*10**3,
              "linetime (ms)= ", self.linetime*10**3)
        print("total imagen REal (s)= ", np.round((tuc - tic), 5),
              "tiempo supuesto imagen (s)= ", self.otrotime*self.numberofPixels)
        #"""


    def barridos(self):
        # arma los barridos con los parametros dados
        self.aceleracion()
#        self.cuentas = np.zeros((self.numberofPixels*self.numberofPixels))
#        self.cuentasvuelta = np.zeros((self.numberofPixels))

        #       Barrido x
        startX = float(self.initialPosition[0])
        sizeX = self.scanRange + startX
        Npuntos = self.nSamplesrampa
        barridonormal = np.linspace(startX, sizeX, Npuntos) + self.xini[-1]

        self.barridoxchico = np.concatenate((self.xini[:-1],
                                             barridonormal,
                                             self.xfin[1:],
                                             self.xvuelta[1:-1],
                                             self.rlow)) / convFactors['x']

        print(len(self.xini[:-1]), "xipuntos\n",
              len(barridonormal), "Npuntos\n",
              len(self.xfin[1:]), "xfinpuntos\n",
              len(self.xvuelta[1:-1]), "xvueltapuntos\n",
              len(self.rlow), "rlowpuntos\n")

        self.barridox = np.tile(self.barridoxchico, self.numberofPixels)

        #       Barrido z (se queda en la posicion inicial)
        startZ = float(self.initialPosition[2])
        self.barridoz = np.ones(len(self.barridox)) * startZ / convFactors['z']

#        #       Barrido y
        startY = float(self.initialPosition[1])
#        self.barridoy = np.ones(len(self.barridox))*startY / convFactors['y']

        stepy = self.scanRange / self.numberofPixels
        rampay = np.ones(len(self.barridoxchico))*startY

        muchasrampasy = np.tile(rampay, (self.numberofPixels, 1))
        self.barridoychico = np.zeros((self.numberofPixels, len(rampay)))

        p = len(self.xini[:-1]) + len(barridonormal) + int(len(self.xfin[1:])/2)#·+ int(len(self.xvuelta[1:-1])/2)
        for i in range(self.numberofPixels):
            self.barridoychico[i, :p] = muchasrampasy[i, :p] + (i)*stepy
            self.barridoychico[i, p:] = muchasrampasy[i, p:] + (i+1)*stepy

        self.barridoy = (self.barridoychico.ravel()) / convFactors['y']
        #la parte del apd

        NoffR = len(self.barridoxchico)-len(barridonormal)-3
        NoffL = len(self.xini[:-1])
        
#        ttotal = (len(self.barridox)-3)/self.sampleRate
#        tposta = len(barridonormal)/self.sampleRate # = T
        toffR = NoffR/self.sampleRate
        toffL = NoffL/self.sampleRate
        
#        Nposta = tposta* self.apdrate  # = Npix*Napd
        
#        print(self.apdrate, "apdrate")
#        print(Nposta, "Nposta", self.numberofPixels*self.Napd)
        
        self.NoffR = int(np.round(toffR *self.apdrate))
        self.NoffL = int(np.round(toffL *self.apdrate))
#        print(self.NoffR, "NoffR", self.NoffL, "NoffL")
#        print(toffR, "toffR", toffL, "toffL")

        self.barridonormal = barridonormal


    def apdpostprocessing(self):
        tic = time.time()
#        Ntirar = self.NoffL+self.NoffR
#        NoffL = 0*self.pixelsoffL
        Npix = self.numberofPixels
#        Nramp = Ntirar + Npix  # len(barridox)  # len(rampay)  # el largo de cara rampa sola (completa).
#        Ntotal = Nramp * Npix  # len(todo)  # len(barridoy)  # que son todos los puntos de las rampas, despues corto.
#        Napd = self.Napd
#        Nramp = self.numberofPixels + self.NoffL + self.NoffR

        cuentas = np.zeros((len(self.barridoxchico), Npix))
        j = self.dy
#        for j in range(Npix):
        for i in range(len(self.barridoxchico)-1):
            cuentas[i,j] = self.contando[i+1,j] - self.contando[i,j]
        self.cuentas = cuentas
#        print((time.time()-tic)*10**3, "tiempo apdpostprocessing (ms)")

# -------Aceleracion----------------------------------------------
    def aceleracion(self):
        #        aceleracion = 120  # µm/ms^2
        aceleration = float(self.acelerationEdit.text())
        T = self.numberofPixels * self.pixelTime * 10**3  # lo paso a ms
        velocity = (self.scanRange / T)
        rate = self.sampleRate*10**-3

#        print(aceleration, "aceleracion\n", velocity, "velocidad\n",
#              T, "T(linea en ms)\n")
        startX = float(self.initialPosition[0])

        ti = velocity / aceleration
#        xi = 0.5*aceleration*(ti**2)
        xipuntos = int(np.ceil(ti * rate))
#        xipuntos = int(np.ceil(xr / self.pixelSize))

        xini = np.zeros(xipuntos)
#        tiempo= (1/self.sampleRate)
#        tiempo = ti/(xi / resolucionDAQ)
        tiempoi = np.linspace(0,ti,xipuntos)
        for i in range(xipuntos):
            xini[i] = 0.5*aceleration*((tiempoi[i])**2) + startX

        xr = xini[-1] + self.scanRange
#        tr = T + ti

        m = float(self.vueltaEdit.text())
        # si busco una velocidad de vuelta Vdeseado veces mayor a la de ida
        tcasi = ((1+m) * velocity) / aceleration  # Vdeseado + V = m*V
#        xcasi = -0.5 * aceleration * (tcasi**2) + velocity * tcasi  # +xr
#        xfinpuntos = abs(int(np.ceil((xcasi) / resolucionDAQ )))  # -xr
        xfinpuntos = int(np.ceil(tcasi * rate))
#        tiempofin = abs(tcasi/(xcasi / resolucionDAQ))
        tiempofin = np.linspace(0, tcasi, xfinpuntos)
        xfin = np.zeros(xfinpuntos)
        for i in range(xfinpuntos):
            xfin[i] = (-0.5*aceleration*((tiempofin[i])**2) + velocity * (tiempofin[i]) ) + xr + startX

        # desaceleracion final, para el loop
        av = m*aceleration
        tlow = m*velocity/av
#        print(tlow, "tlow")
        xlow = 0.5*av*(tlow**2)
#        print(xlow, "xlow")
#        tvuelta =int(np.ceil(((xfin[-1])/(m*velocity))))
        Nvuelta = abs(int(np.ceil(((xlow-xfin[-1])/(m*velocity)) * (rate))))

        if xfin[-1] < xlow + startX:
            if xfin[-1] < 0:
                q = np.where(xfin<=0)[0][0]
                xfin = xfin[:q]
                print("xfin < 0")
                self.xvuelta = np.linspace(0,0,4)

            else:
                q = np.where(xfin <= xlow + startX)[0][0]
                xfin = xfin[:q]
                self.xvuelta = np.linspace(xlow, 0, Nvuelta) + startX
                print("xfin < xlow")
            rlow = np.linspace(0,0,2)
        else:

            self.xvuelta = np.linspace(xfin[-1], xlow+startX, Nvuelta)

            xlowpuntos = int(np.ceil(tlow * rate))
            tiempolow=np.linspace(0,tlow,xlowpuntos)
            print("normal")
            rlow=np.zeros(xlowpuntos)
            for i in range(xlowpuntos):
                rlow[i] = 0.5*(av)*(tiempolow[i]**2)
                
            rlow=np.flip(rlow,axis=0)
        print("\n")
#        print(m*velocity, "v vuelta", Nvuelta, "Nvuelta")
#        print(np.round(tiempoi[-2]-tiempoi[-1], 4), "tiempoi\n",
#              np.round(tiempofin[-2]-tiempofin[-1], 4), "tiempofin\n",
#              np.round(1/rate, 4), "1/sampleRate")

        self.xini = xini
        self.xfin = xfin
        self.rlow = rlow

        NoffL = len(xini[:-1])
        NoffR = len(xfin[1:]) + len(self.xvuelta[1:-1]) + len(rlow)
        toffL = NoffL/self.sampleRate
        toffR = NoffR/self.sampleRate
        toff = toffL + toffR
        self.pixelsoffL = int(np.round(toffL*self.apdrate))
        self.pixelsoff = int(np.round(toff*self.apdrate))
#        self.pixelsoffini = int(np.ceil(xipuntos / (self.pixelTime*self.sampleRate)))
        print(self.pixelsoff, "pixelsoff")

#        pixelsofffin = np.ceil(tcasi*self.sampleRate)
#        self.pixelsoffvuelta = len(self.xvuelta) * self.sampleRate + pixelsofffin

#        self.puntosAPD = pixelsoffini + self.numberofPixels + self.pixelsoffvuelta

    def channelsOpen(self):
        if self.canales:
            print("Ya estan abiertos los canales")  # para evitar el error
            #  usando esto podria no cerrarlos nunca.
        else:
            self.canales = True

            self.aotask = nidaqmx.Task('aotask')
            self.dotask = nidaqmx.Task('dotask')
#            self.aitask = nidaqmx.Task('aitask')  # Ger
#            self.ditask = nidaqmx.Task('ditask')  # Ger
            self.citask = nidaqmx.Task('citask')
            

            self.citask.ci_channels.add_ci_count_edges_chan(counter='Dev1/ctr0',
                                name_to_assign_to_channel=u'conter',
                                initial_count=0)

            self.citask.timing.cfg_samp_clk_timing(
              rate=self.apdrate, sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
              source=r'100kHzTimebase',
              samps_per_chan = int(len(self.barridox)))

    #        # Tengo que hacer que dotask accione el/los shutters.
    
    #        self.dotask.do_channels.add_do_chan(  # se ocuparia del shutter
    #            lines="Dev1/port0/line6", name_to_assign_to_lines='chan6',
    #            line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)  # Ger

            triggerrate = self.apdrate
            num = int(self.triggerEdit.text())
            trigger = np.zeros((5+num),dtype="bool")  # np.zeros((10), dtype="bool")  # np.zeros((len(signaltodo)),dtype="bool")

            trigger[num] = True

            self.trigger = trigger
            print((num/self.apdrate)*10**3, "delay (ms)")  # "\n", num, "num elegido", 

            self.dotask.do_channels.add_do_chan(  # se ocuparia del shutter Pero no. Ahora es el trigger.
                lines="Dev1/port0/line6", name_to_assign_to_lines='chan6',
                line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)  # Ger
    
            self.dotask.timing.cfg_samp_clk_timing(
                         rate=triggerrate,  # muestras por segundo
                         sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
    #                         source='100kHzTimebase',
                         active_edge = nidaqmx.constants.Edge.RISING,
                         samps_per_chan=len(trigger))


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
                samps_per_chan=len(self.barridox))

            triggerchannelname = "PFI4"
            self.aotask.triggers.start_trigger.cfg_dig_edge_start_trig(
                                trigger_source = triggerchannelname)#,
    #                                trigger_edge = nidaqmx.constants.Edge.RISING)
    
            self.citask.triggers.arm_start_trigger.dig_edge_src = triggerchannelname
            self.citask.triggers.arm_start_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_EDGE
#            self.citask.triggers.arm_start_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING

    # Para que se pause cuando la señal de dotask esta en LOW
#            self.aotask.triggers.pause_trigger.dig_lvl_src = triggerchannelname
#            self.aotask.triggers.pause_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_LEVEL
#            self.aotask.triggers.pause_trigger.dig_lvl_when = nidaqmx.constants.Level.LOW
#
#            self.citask.triggers.pause_trigger.dig_lvl_src = triggerchannelname
#            self.citask.triggers.pause_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_LEVEL
#            self.citask.triggers.pause_trigger.dig_lvl_when = nidaqmx.constants.Level.LOW

    def done(self):
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
#            del NoseComoHacerloMejor
            self.canales = False
        else:
            print("llego hasta el done pero no tenia nada que cerrar")

    def openShutter(self, color):
        if color == "red":
            print("abre shutter rojo")
#            self.dotask.write(5, auto_start=True)
# TO DO: Es una idea de lo que tendria que hacer la funcion

    def movetoStart(self):
        self.done()
        N = self.moveSamples

#         Following loop creates the voltage channels
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

        tic = time.time()
        startY = float(self.initialPosition[1])
#        maximoy = startY + ((self.dy) * self.pixelSize)
        maximoy = self.barridoychico[-1, -1]
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
#        print(np.round(time.time() - tic, 5)*10**3, "movetostart (ms)")
        self.dy = 0

        self.aotask.stop()
        self.aotask.close()

        self.channelsOpen()

    def guardarimagen(self):
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

#if __name__ == '__main__':


app = QtGui.QApplication([])
win = ScanWidget(device)
win.show()

app.exec_()

#if __name__ == '__main__':
#    queue = mp.Queue()
#    p = mp.Process(target=worker, args=(queue,))
#    q = mp.Process(target=worker, args=(queue,))
#    p.start()

#    for i in range(N):
#        n = i  # random.random() * 5
#        print ("main: put:", n)
#        queue.put([n,5*n,n])
#        time.sleep(1.0)



#ScanWidget()
