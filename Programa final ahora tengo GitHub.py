
import os
import tkinter as tk
from tkinter import filedialog

import numpy as np
import time
#import scipy.ndimage as ndi
import matplotlib.pyplot as plt

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui

#from pyqtgraph.dockarea import Dock, DockArea
import pyqtgraph.ptime as ptime

from PIL import Image

import re

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

    def graphplot(self):
        if self.dy == 0:
            self.paramChanged()

        verxi = np.concatenate((self.xini[:-1],
                               np.zeros(len(self.wantedrampx)),
                               np.zeros(len(self.xchange[1:])),
                               np.zeros(len(self.xback[1:-1])),
                               np.zeros(len(self.xstops))))

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
#            plt.plot(self.onerampy[1,:],'k')
        plt.show()


    def __init__(self, device, *args, **kwargs):  # agregue device

        super().__init__(*args, **kwargs)

        self.nidaq = device  # esto tiene que ir

        imageWidget = pg.GraphicsLayoutWidget()
        self.vb = imageWidget.addViewBox(row=1, col=1)

    # Parameters for smooth moving (to no go hard on the piezo (or galvos))
        self.moveTime = 1 / 10**3  # total time to move(s)
        self.moveSamples = 1000  # samples to move
        self.moveRate = self.moveSamples / self.moveTime  # 10**5

        self.activeChannels = ["x", "y", "z"]
        self.AOchans = [0, 1, 2]

    # LiveView Button

        self.liveviewButton = QtGui.QPushButton('confocal LIVEVIEW')
        self.liveviewButton.setCheckable(True)
        self.liveviewButton.clicked.connect(self.liveview)

    # XZ PSF scan
        self.XYcheck = QtGui.QRadioButton('XY normal scan')
        self.XYcheck.setChecked(True)

        self.XZcheck = QtGui.QRadioButton('XZ psf scan')
        self.XZcheck.setChecked(False)

        self.YZcheck = QtGui.QRadioButton('YZ psf scan')
        self.YZcheck.setChecked(False)
    # para que guarde todo (trazas de Alan)

        self.Alancheck = QtGui.QCheckBox('Alan continous save')
        self.Alancheck.setChecked(False)

    # save image Button

        self.saveimageButton = QtGui.QPushButton('Scan and Save')
        self.saveimageButton.setCheckable(True)
        self.saveimageButton.clicked.connect(self.saveimage)
        self.saveimageButton.setStyleSheet(
                "QPushButton { background-color: gray; }"
                "QPushButton:pressed { background-color: blue; }")

#        label_save = QtGui.QLabel('Nombre del archivo (archivo.tiff)')
#        label_save.resize(label_save.sizeHint())
#        self.edit_save = QtGui.QLineEdit('imagenScan.tiff')
#        self.edit_save.resize(self.edit_save.sizeHint())

        self.NameDirButton = QtGui.QPushButton('Open')
        self.NameDirButton.clicked.connect(self.openFolder)
        self.file_path = os.path.abspath("")
        self.NameDirValue = QtGui.QLabel('')
        self.NameDirValue.setText(self.file_path)

    # Defino el tipo de Scan que quiero

        self.scanMode = QtGui.QComboBox()
        self.scanModes = ['ramp scan', 'step scan', 'full frec ramp']
        self.scanMode.addItems(self.scanModes)

        self.graphcheck = QtGui.QCheckBox('Scan Plot')
        self.graphcheck.clicked.connect(self.graphplot)
        self.step = False

    # useful Booleans
        self.channelramp = False #canales
#        self.inStart = False
#        self.working = False
        self.channelsteps = False
        self.shuttering = False
        self.shuttersignal = [False, False, False]

    # Shutters buttons
        self.shutterredbutton = QtGui.QCheckBox('shutter 640')
        self.shutterredbutton.clicked.connect(self.shutterred)

        self.shuttergreenbutton = QtGui.QCheckBox('shutter 532')
        self.shuttergreenbutton.clicked.connect(self.shuttergreen)
        self.shutterotrobutton = QtGui.QCheckBox('shutter otro')
        self.shutterotrobutton.clicked.connect(self.shutterotro)

    # Scanning parameters

#        self.initialPositionLabel = QtGui.QLabel('Initial Pos [x0 y0 z0] (µm)')
#        self.initialPositionEdit = QtGui.QLineEdit('0 0 1')
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

        self.onlyInt = QtGui.QIntValidator(0,10**6)
        self.numberofPixelsEdit.setValidator(self.onlyInt)
        self.onlypos = QtGui.QDoubleValidator(0, 10**6,10)
        self.pixelTimeEdit.setValidator(self.onlypos)
        self.scanRangeEdit.setValidator(self.onlypos)

        self.numberofPixelsEdit.textChanged.connect(self.paramChanged)
        self.scanRangeEdit.textChanged.connect(self.paramChanged)
        self.pixelTimeEdit.textChanged.connect(self.paramChanged)
#        self.initialPositionEdit.textChanged.connect(self.paramChanged)
        self.acelerationEdit.textChanged.connect(self.paramChanged)
        self.vueltaEdit.textChanged.connect(self.paramChanged)
        self.XYcheck.clicked.connect(self.paramChanged)
        self.XZcheck.clicked.connect(self.paramChanged)
        self.YZcheck.clicked.connect(self.paramChanged)
        self.scanMode.activated.connect(self.paramChanged)

        self.paramWidget = QtGui.QWidget()

        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        grid.addWidget(imageWidget, 0, 0)
        grid.addWidget(self.paramWidget, 0, 1)

        subgrid = QtGui.QGridLayout()
        self.paramWidget.setLayout(subgrid)


#        subgrid.addWidget(self.initialPositionLabel, 0, 1)
#        subgrid.addWidget(self.initialPositionEdit, 1, 1)
        subgrid.addWidget(self.scanRangeLabel, 2, 1)
        subgrid.addWidget(self.scanRangeEdit, 3, 1)
        subgrid.addWidget(self.pixelTimeLabel, 4, 1)
        subgrid.addWidget(self.pixelTimeEdit, 5, 1)
        subgrid.addWidget(self.triggerLabel, 4, 2)
        subgrid.addWidget(self.triggerEdit, 5, 2)
        subgrid.addWidget(self.numberofPixelsLabel, 6, 1)
        subgrid.addWidget(self.numberofPixelsEdit, 7, 1)
        subgrid.addWidget(self.acelerationLabel, 6, 2)
        subgrid.addWidget(self.acelerationEdit, 7, 2)
        subgrid.addWidget(self.pixelSizeLabel, 8, 1)
        subgrid.addWidget(self.pixelSizeValue, 9, 1)
        subgrid.addWidget(self.vueltaLabel, 8, 2)
        subgrid.addWidget(self.vueltaEdit, 9, 2)
        subgrid.addWidget(self.liveviewButton, 10, 1)
        subgrid.addWidget(self.graphcheck, 11, 2)
        subgrid.addWidget(self.timeTotalLabel, 13, 1)
        subgrid.addWidget(self.timeTotalValue, 14, 1)
#        subgrid.addWidget(self.XZButton, 10, 2)
        subgrid.addWidget(self.Alancheck, 10, 2)
        subgrid.addWidget(self.XYcheck, 14, 2)
        subgrid.addWidget(self.XZcheck, 15, 2)
        subgrid.addWidget(self.YZcheck, 16, 2)

        subgrid.addWidget(self.shutterredbutton, 1, 1)


        subgrid.addWidget(self.scanMode, 12, 1)
        subgrid.addWidget(self.saveimageButton, 15, 1)
        subgrid.addWidget(self.NameDirButton, 1, 2)


# ---  Positioner part ---------------------------------
        # Axes control
        self.xLabel = QtGui.QLabel('5.0')
        self.xLabel.setTextFormat(QtCore.Qt.RichText)
        self.xname =  QtGui.QLabel("<strong>x =")
        self.xname.setTextFormat(QtCore.Qt.RichText)
        self.xUpButton = QtGui.QPushButton("(+x) ►")  # →
        self.xUpButton.pressed.connect(self.xMoveUp)
        self.xDownButton = QtGui.QPushButton("◄ (-x)")  # ←
        self.xDownButton.pressed.connect(self.xMoveDown)
        self.xStepEdit = QtGui.QLineEdit("1")
        self.xStepUnit = QtGui.QLabel(" µm")

        self.yLabel = QtGui.QLabel('5.0')
        self.yLabel.setTextFormat(QtCore.Qt.RichText)
        self.yname =  QtGui.QLabel("<strong>y =")
        self.yname.setTextFormat(QtCore.Qt.RichText)
        self.yUpButton = QtGui.QPushButton("(+y) ▲")  # ↑
        self.yUpButton.pressed.connect(self.yMoveUp)
        self.yDownButton = QtGui.QPushButton("(-y) ▼")  # ↓
        self.yDownButton.pressed.connect(self.yMoveDown)
        self.yStepEdit = QtGui.QLineEdit("1")
        self.yStepUnit = QtGui.QLabel(" µm")

        self.zLabel = QtGui.QLabel('5.0')
        self.zLabel.setTextFormat(QtCore.Qt.RichText)
        self.zname =  QtGui.QLabel("<strong>z =")
        self.zname.setTextFormat(QtCore.Qt.RichText)
        self.zUpButton = QtGui.QPushButton("+z ▲")
        self.zUpButton.pressed.connect(self.zMoveUp)
        self.zDownButton = QtGui.QPushButton("-z ▼")
        self.zDownButton.pressed.connect(self.zMoveDown)
        self.zStepEdit = QtGui.QLineEdit("1")
        self.zStepUnit = QtGui.QLabel(" µm")

        self.positioner = QtGui.QWidget()
        grid.addWidget(self.positioner, 1, 0)
        layout = QtGui.QGridLayout()
        self.positioner.setLayout(layout)
        layout.addWidget(self.xname, 1, 0)
        layout.addWidget(self.xLabel, 1, 1)
        layout.addWidget(self.xUpButton, 2, 4,2,1)
        layout.addWidget(self.xDownButton, 2, 2,2,1)
#        layout.addWidget(QtGui.QLabel("Step x"), 1, 6)
#        layout.addWidget(self.xStepEdit, 1, 7)
#        layout.addWidget(self.xStepUnit, 1, 8)

        layout.addWidget(self.yname, 2, 0)
        layout.addWidget(self.yLabel, 2, 1)
        layout.addWidget(self.yUpButton, 1, 3,2,1)
        layout.addWidget(self.yDownButton, 3, 3,2,1)
        layout.addWidget(QtGui.QLabel("Length of step xy"), 1, 7)
        layout.addWidget(self.yStepEdit, 2, 7)
        layout.addWidget(self.yStepUnit, 2, 8)
        
        layout.addWidget(self.zname, 4, 0)
        layout.addWidget(self.zLabel, 4, 1)
        layout.addWidget(self.zUpButton, 1, 5,2,1)
        layout.addWidget(self.zDownButton, 3, 5,2,1)
        layout.addWidget(QtGui.QLabel("Length of step z"), 3, 7)
        layout.addWidget(self.zStepEdit, 4, 7)
        layout.addWidget(self.zStepUnit, 4, 8)
#        layout.addWidget(QtGui.QLabel("||"), 1, 7)
#        layout.addWidget(QtGui.QLabel("||"), 2, 7)
#        layout.addWidget(QtGui.QLabel("||"), 4, 7)
        layout.addWidget(self.NameDirValue, 8, 0, 1, 8)
        self.yStepEdit.setValidator(self.onlypos)
        self.zStepEdit.setValidator(self.onlypos)

        self.gotoWidget = QtGui.QWidget()
        grid.addWidget(self.gotoWidget, 1, 1)
        layout2 = QtGui.QGridLayout()
        self.gotoWidget.setLayout(layout2)
        layout2.addWidget(QtGui.QLabel("||x"), 1, 7)
        layout2.addWidget(QtGui.QLabel("||y"), 2, 7)
        layout2.addWidget(QtGui.QLabel("||z"), 3, 7)
        self.xgotoLabel = QtGui.QLineEdit("0")
        self.ygotoLabel = QtGui.QLineEdit("0")
        self.zgotoLabel = QtGui.QLineEdit("0")
        self.gotoButton = QtGui.QPushButton("♫ G0 To ♪")
        self.gotoButton.pressed.connect(self.goto)
        layout2.addWidget(self.gotoButton, 1, 9, 2, 2)
        layout2.addWidget(self.xgotoLabel, 1, 8)
        layout2.addWidget(self.ygotoLabel, 2, 8)
        layout2.addWidget(self.zgotoLabel, 3, 8)
        self.zgotoLabel.setValidator(self.onlypos)

        self.CMxLabel = QtGui.QLabel('CM X')
        self.CMxValue = QtGui.QLabel('NaN')
        self.CMyLabel = QtGui.QLabel('CM Y')
        self.CMyValue = QtGui.QLabel('NaN')
        layout2.addWidget(self.CMxLabel, 4, 8)
        layout2.addWidget(self.CMxValue, 5, 8)
        layout2.addWidget(self.CMyLabel, 4, 9)
        layout2.addWidget(self.CMyValue, 5, 9)
        self.goCMButton = QtGui.QPushButton("♠ Go CM ♣")
        self.goCMButton.pressed.connect(self.goCM)
        layout2.addWidget(self.goCMButton, 2, 9, 2, 2)


        # Nueva interface mas comoda!
        hbox = QtGui.QHBoxLayout(self)
        topleft=QtGui.QFrame()
        topleft.setFrameShape(QtGui.QFrame.StyledPanel)
        bottom = QtGui.QFrame()
        bottom.setFrameShape(QtGui.QFrame.StyledPanel) 
        topleft.setLayout(grid)
        downright=QtGui.QFrame()
        downright.setFrameShape(QtGui.QFrame.StyledPanel)

        splitter1 = QtGui.QSplitter(QtCore.Qt.Horizontal)
        splitter1.addWidget(imageWidget)
        splitter1.addWidget(topleft)
        splitter1.setSizes([10**6, 1])

        splitter15 = QtGui.QSplitter(QtCore.Qt.Horizontal)
        splitter15.addWidget(self.positioner)
#        splitter15.addWidget(bottom)
        splitter15.addWidget(self.gotoWidget)
        splitter15.setSizes([1000, 1])

        splitter2 = QtGui.QSplitter(QtCore.Qt.Vertical)
        splitter2.addWidget(splitter1)
        splitter2.addWidget(splitter15)
        splitter2.setSizes([10, 10])

        hbox.addWidget(splitter2)

        self.setLayout(hbox)
# ---- fin positioner part----------

        self.paramChanged()
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

        self.steptimer = QtCore.QTimer()
        self.steptimer.timeout.connect(self.stepScan)

#--- paramChanged
    def paramChanged(self):
        """ Update the parameters when the user edit them """

        self.scanRange = float(self.scanRangeEdit.text())
        self.numberofPixels = int(self.numberofPixelsEdit.text())
        self.pixelTime = float(self.pixelTimeEdit.text()) / 10**3  # seconds
#        self.initialPosition = np.array(
#                        self.initialPositionEdit.text().split(' '))

        self.initialPosition = (float(self.xLabel.text()),
                                float(self.yLabel.text()),
                                float(self.zLabel.text()))

        self.apdrate = 10**5  # 20*10**6  # samples/seconds
        self.Napd = int(np.round(self.apdrate * self.pixelTime))
        print(self.Napd, "=Napd\n")

        self.pixelSize = self.scanRange / self.numberofPixels

        self.pixelSizeValue.setText('{}'.format(np.around(
                                        1000 * self.pixelSize, 2)))  # en nm

        self.linetime = self.pixelTime * self.numberofPixels  # en s

#        print(self.linetime, "linetime")

        self.timeTotalValue.setText('{}'.format(np.around(
                         self.numberofPixels * self.linetime, 2)))

        size = (self.numberofPixels, self.numberofPixels)

        if self.scanMode.currentText() == "step scan":
        # en el caso step no hay frecuencias
            print("Step time, lets see the velocity")

        if self.scanMode.currentText() == "ramp scan":
            self.nSamplesrampa = self.numberofPixels  # self.apdrate*self.linetime
            self.sampleRate = 1 / self.pixelTime  # self.apdrate
            print("los Nsamples = Npix y 1/tpix la frecuencia\n",
                  self.nSamplesrampa, "Nsamples", self.sampleRate, "sampleRate")

        if self.scanMode.currentText() == "full frec ramp":
            self.sampleRate = (self.scanRange /resolucionDAQ) / (self.linetime)
            self.nSamplesrampa = int(np.ceil(self.scanRange /resolucionDAQ))
            print("a full resolucion\n",
                  self.nSamplesrampa, "Nsamples", self.sampleRate, "sampleRate")


        print(self.linetime, "linetime\n")

        if self.scanMode.currentText() == "step scan":
            self.Steps()
        else:
#        if self.scanMode.currentText() == "ramp scan" or self.scanMode.currentText() == "otra frec ramp":
            self.Ramps()
            self.reallinetime = len(self.onerampx) * self.pixelTime  # seconds
            print(self.reallinetime, "reallinetime")

#        self.barridos()

        self.blankImage = np.zeros(size)
        self.image = self.blankImage

        self.dy = 0

      # numberofpixels is the relevant part of the total ramp.
        self.APD = np.zeros((((self.numberofPixels + self.pixelsofftotal)*self.Napd),
                             (self.numberofPixels)))


# cosas para el save image nuevo
    def saveimage(self):
        """ la idea es que escanee la zona deseada (desde cero) una sola vez,
        y guarde la imagen"""
        if self.saveimageButton.isChecked():
            self.save = True
            self.channelsOpen()
            self.saveimageButton.setText('Abort')
            self.liveviewStart()

        else:
            self.save = False
            print("Abort")
            self.saveimageButton.setText('retry Scan and Stop')
            self.liveviewStop()

# This is the function triggered by pressing the liveview button
#--- liveview
    def liveview(self):
        """ Image live view when not recording
        """
        if self.liveviewButton.isChecked():
            self.save = False
            self.liveviewStart()

        else:
            self.liveviewStop()

    def liveviewStart(self):
#        self.working = True
        self.openShutter("red")
        if self.scanMode.currentText() == "step scan":
            self.channelsOpenStep()
#            self.inStart = False
            self.tic = ptime.time()
            self.steptimer.start(5)#100*self.pixelTime*10**3)  # imput in ms
        else:
#        if self.scanMode.currentText() == "ramp scan" or self.scanMode.currentText() == "otra frec ramp":
            self.channelsOpen()
            self.rampScan()

    def rampScan(self):
        self.MovetoStart()
        self.startingRamps()
        self.tic = ptime.time()
        self.viewtimer.start(self.reallinetime*10**3)  # imput in ms


    def liveviewStop(self):
        if self.save:
#            print("listo el pollo")
            self.saveimageButton.setChecked(False)
            self.saveimageButton.setText('redo Scan and save')
            self.save = False
            self.MovetoStart()


        self.liveviewButton.setChecked(False)
        self.viewtimer.stop()
        self.steptimer.stop()
        self.closeShutter("red")
        self.done()


    def stepLine(self):
        tic = ptime.time()
        APD = np.zeros((self.Napd+1))

        for i in range(self.numberofPixels):
#            tec = ptime.time()
#            self.citask.stop()
            self.aotask.stop()

            self.aotask.write(
             [self.allstepsx[i, self.dy] / convFactors['x'],
              self.allstepsy[i, self.dy] / convFactors['y'],
              self.allstepsz[i, self.dy] / convFactors['z']],
                             auto_start=True)

#                self.aotask.start()
            self.aotask.wait_until_done()

#            tac = ptime.time()
            APD[:] = self.citask.read(1+self.Napd)
            self.citask.wait_until_done()
#            toc = ptime.time()

            self.citask.stop()
            self.aotask.stop()
#            self.cuentas[i] = aux + np.random.rand(1)[0]
            self.image[i, self.numberofPixels-1-self.dy] = APD[-1] - APD[0]

# ---stemScan ---
    def stepScan(self):
    # the step clock calls this function
        self.stepLine()

#        self.image[:, self.numberofPixels-1-(self.dy)] = self.cuentas
        self.img.setImage(self.image, autoLevels=True)


        if self.dy < self.numberofPixels-1:
            self.dy = self.dy + 1
        else:
            if self.save:
                self.guardarimagen()

                self.saveimageButton.setText('Fin')  # ni se ve
                self.MovetoStart()
                self.liveviewStop()
            else:
                if self.Alancheck.isChecked():
                    self.guardarimagen()  # para guardar siempre (Alan idea)
                print(ptime.time()-self.tic, "Tiempo imagen completa.")
                self.viewtimer.stop()
                self.MovetoStart()
                self.liveviewStart()

    def Steps(self):
        self.pixelsofftotal = 0
        self.cuentas = np.zeros((self.numberofPixels))

#    Barrido x: Primal signal
#        self.allstepsx = np.zeros((self.numberofPixels,self.numberofPixels))
        startX = float(self.initialPosition[0])
        sizeX = self.scanRange
        Npuntos = self.numberofPixels
        gox = (np.linspace(0, sizeX, Npuntos) + startX )
        self.allstepsx = np.transpose(np.tile(gox,(self.numberofPixels,1)))
    # a matrix [i,j] where i go for the complete ramp and j evolves in y lines


#    Barrido y: secondary signal
        startY = float(self.initialPosition[1])
        goy = np.ones(Npuntos) * startY
        self.allstepsy = np.zeros((self.numberofPixels,self.numberofPixels))
        stepy = self.scanRange / self.numberofPixels
        for j in range (len(self.allstepsy)):
            self.allstepsy[:,j] = goy + (j) * stepy

#    Barrido z (se queda en la posicion inicial): thirth signal (static)
        startZ = float(self.initialPosition[2])
        goz = np.ones(Npuntos) * startZ 
        self.allstepsz = np.tile(goz,(self.numberofPixels,1))

        if self.XYcheck.isChecked():
            print("escaneo x y normal S")

        if self.XZcheck.isChecked():
            print("intercambio y por z S")
            self.allstepsz = self.allstepsy - startY + startZ  # -(sizeX/2)
            goy= np.ones(len(self.allstepsx)) * startY
            self.allstepsy = np.tile(goy,(self.numberofPixels,1))


        if self.YZcheck.isChecked():
            print("intercambio x por y S")
            self.allstepsz = self.allstepsy - startY + startZ  # -(sizeX/2)
            self.allstepsy = self.allstepsx - startX + startY
            gox= np.ones(len(self.allstepsy)) * startX
            self.allstepsx = np.tile(gox, (self.numberofPixels,1))


#    def startingSteps(self):

    def startingRamps(self):

#        self.working = True
    # Send the signals to the NiDaq, but only start when the trigger is on
        self.aotask.write(np.array([self.totalrampx / convFactors['x'],
                                    self.totalrampy / convFactors['y'],
                                    self.totalrampz / convFactors['z']]), auto_start=True)

#        self.inStart = False
        print("ya arranca")
    # Starting the trigger. It have a controllable 'delay'
        self.dotask.write(self.trigger, auto_start=True)

    def updateView(self):

    # The counter reads this numbers of points when the trigger starts
        self.APD[:, self.dy] = self.citask.read(
              ((self.numberofPixels + self.pixelsofftotal)*self.Napd))

    # have to analize the signal from the counter
        self.apdpostprocessing()

        self.image[:, -1-self.dy] = self.counts[:]

      # The plotting method is slow (2-3 ms each), so I´m plotting in packages
        if self.pixelTime <= (0.1*10**3):
            multi5 = np.arange(0, self.numberofPixels, 10)  # looks like realtime
        else:
            multi5 = np.arange(0, self.numberofPixels, 2)

        if self.dy in multi5:
            self.img.setImage(self.image, autoLevels=True)

        if self.dy < self.numberofPixels-1:
            self.dy = self.dy + 1

        else:
            if self.save:
                self.saveFrame()

                self.saveimageButton.setText('End')
                self.liveviewStop()

            else:
                if self.Alancheck.isChecked():
                    self.guardarimagen()  # para guardar siempre (Alan idea)
                print(ptime.time()-self.tic, "Tiempo imagen completa.")
                self.viewtimer.stop()
                self.dotask.stop()
                self.aotask.stop()
                self.citask.stop()
                self.liveviewStart()

# --- Ramps / startingRamps ----
    def Ramps(self):
    # arma los barridos con los parametros dados
        self.counts = np.zeros((self.numberofPixels))

        self.acceleration()

#    Barrido x
        startX = float(self.initialPosition[0])
        sizeX = self.scanRange
        Npuntos = self.nSamplesrampa  # self.numberofPixels  # 
        wantedrampx = np.linspace(0, sizeX, Npuntos) + self.xini[-1]

        self.onerampx = np.concatenate((self.xini[:-1],
                                             wantedrampx,
                                             self.xchange[1:],
                                             self.xback[1:-1],
                                             self.xstops))  # / convFactors['x']
        self.wantedrampx = wantedrampx

        print(len(self.xini[:-1]), "xipuntos\n",
              len(wantedrampx), "Npuntos\n",
              len(self.xchange[1:]), "xchangepuntos\n",
              len(self.xback[1:-1]), "xbackpuntos\n",
              len(self.xstops), "xstopspuntos\n")

        self.totalrampx = np.tile(self.onerampx, self.numberofPixels)

#    Barrido z (se queda en la posicion inicial)
        startZ = float(self.initialPosition[2])
        self.totalrampz = np.ones(len(self.totalrampx)) * startZ  # / convFactors['z']

#    Barrido y
        startY = float(self.initialPosition[1])

        stepy = self.scanRange / self.numberofPixels
        rampay = np.ones(len(self.onerampx))*startY

        muchasrampasy = np.tile(rampay, (self.numberofPixels, 1))
        self.onerampy = np.zeros((self.numberofPixels, len(rampay)))

        p = len(self.xini[:-1]) + len(wantedrampx) + int(len(self.xchange[1:])/2)#·+ int(len(self.xback[1:-1])/2)
        for i in range(self.numberofPixels):
            self.onerampy[i, :p] = muchasrampasy[i, :p] + (i)  *stepy
            self.onerampy[i, p:] = muchasrampasy[i, p:] + (i+1)*stepy

        self.totalrampy = (self.onerampy.ravel())  # / convFactors['y']

        if self.XYcheck.isChecked():
            print("escaneo x y normal R")

        if self.XZcheck.isChecked():
            print("intercambio y por z R")
            self.totalrampz = self.totalrampy - startY + startZ  # -(sizeX/2)
            self.totalrampy = np.ones(len(self.totalrampx)) * startY  # / convFactors['y']

        if self.YZcheck.isChecked():
            print("intercambio x por z R")
            self.totalrampz = self.totalrampy - startY + startZ  # -(sizeX/2)
            self.totalrampy = self.totalrampx - startX + startY
            self.totalrampx = np.ones(len(self.totalrampx)) * startX  # / convFactors['x']


    def apdpostprocessing(self):
        """ takes the evergrowing valors from the counter measure and convert
        it into "number or events" """

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

# puede fallar en la primer y/o ultima fila


# -------Aceleracion----------------------------------------------
    def acceleration(self):
        """ it creates the smooths-edge signals to send to the piezo
        It´s just an u.a.r.m. movement equation"""  # MRUV
    #        aceleracion = 120  # µm/ms^2  segun inspector
        aceleration = float(self.acelerationEdit.text())  # editable
        T = self.numberofPixels * self.pixelTime * 10**3  # all in ms
        velocity = (self.scanRange / T)
        rate = self.sampleRate*10**-3

        startX = float(self.initialPosition[0])

        ti = velocity / aceleration
        xipuntos = int(np.ceil(ti * rate))

        xini = np.zeros(xipuntos)
        tiempoi = np.linspace(0,ti,xipuntos)
        for i in range(xipuntos):
            xini[i] = 0.5*aceleration*((tiempoi[i])**2) + startX

        xr = xini[-1] + self.scanRange
#        tr = T + ti

        m = float(self.vueltaEdit.text())
    # impongo una velocidad de vuelta m veces mayor a la de ida
        tcasi = ((1+m) * velocity) / aceleration  # -a*t + V = -m*V
        xchangepuntos = int(np.ceil(tcasi * rate))
        tiempofin = np.linspace(0, tcasi, xchangepuntos)
        xchange = np.zeros(xchangepuntos)
        for i in range(xchangepuntos):
            xchange[i] = (-0.5*aceleration*((tiempofin[i])**2) + velocity * (tiempofin[i]) ) + xr

    # After the wanted ramp, it get a negative acceleration:
        av = aceleration  # *m
        tlow = m*velocity/av
        xlow = 0.5*av*(tlow**2)
        Nvuelta = abs(int(np.ceil(((xlow-xchange[-1])/(m*velocity)) * (rate))))

    # To avoid wrong going back in x
        if xchange[-1] < xlow + startX:
            if xchange[-1] < startX:
                q = np.where(xchange<=startX)[0][0]
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
                xstops[i] = 0.5*(av)*(tiempolow[i]**2) + startX
                
            xstops=np.flip(xstops,axis=0)
        print("\n")

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

# --- ChannelsOpen (rampas)
    def channelsOpen(self):
        """ Open and Config of all the channels for use"""
        if self.channelsteps:
            self.done()

        if self.channelramp:
            print("Ya estan abiertos los canales")  # to dont open again 
            #  usando esto podria no cerrarlos nunca.
        else:
            self.channelramp = True
        # Create all the channels
            self.aotask = nidaqmx.Task('aotask')
            self.dotask = nidaqmx.Task('dotask')
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

        # Create the signal trigger
            triggerrate = self.apdrate
            num = int(self.triggerEdit.text()) * self.Napd
#            trigger = np.zeros((len(self.onerampx)*self.Napd),dtype="bool")

#            trigger[:] = True
#            trigger1 = np.concatenate((trigger, np.zeros(100,dtype="bool")))  # 2ms de apagado, hace cosas raras
            trigger2 = [True, True, False]  # np.tile(trigger, self.numberofPixels)

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
#            self.aotask.triggers.pause_trigger.dig_lvl_src = triggerchannelname
#            self.aotask.triggers.pause_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_LEVEL
#            self.aotask.triggers.pause_trigger.dig_lvl_when = nidaqmx.constants.Level.LOW
#
#            self.citask.triggers.pause_trigger.dig_lvl_src = triggerchannelname
#            self.citask.triggers.pause_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_LEVEL
#            self.citask.triggers.pause_trigger.dig_lvl_when = nidaqmx.constants.Level.LOW
        # En realidad mando un vector con muchos True's, asi que no lo estoy usando

#---- done
    def done(self):
        """ stop and close all the channels"""
        if self.channelramp or self.channelsteps:
            try:
    #            print("Cierro todos los canales")  # para evitar el error
                self.aotask.stop()
                self.aotask.close()
            except:
                print("a")
            try:
                self.dotask.stop()
                self.dotask.close()
            except:
                print("d")
            try:
                self.citask.stop()
                self.citask.close()
            except:
                print("c")
            self.channelramp = False
            self.channelsteps = False

        else:
            print("llego hasta el done pero no tenia nada que cerrar")
            # Esto no tendria que pasar

# --- channelsOpenStep  (step) --------------------------------

    def channelsOpenStep(self):
        """ Open and Config of all the channels for use step by step"""
        if self.channelramp:
            self.done()

        if self.channelsteps:
            print("Ya estan abiertos los canales step")  # to dont open again 
            #  usando esto podria no cerrarlos nunca.
        else:
            self.channelsteps = True
        # Create all the channels
            self.aotask = nidaqmx.Task('aotask')
            self.citask = nidaqmx.Task('citask')

        # Configure the counter channel to read the APD
            self.citask.ci_channels.add_ci_count_edges_chan(counter='Dev1/ctr0',
                                name_to_assign_to_channel=u'conter',
                                initial_count=0)

            totalcinumber = self.Napd + 1

            self.citask.timing.cfg_samp_clk_timing(
              rate=self.apdrate, sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
              source=r'100kHzTimebase',
              samps_per_chan = totalcinumber)

        # Following loop creates the voltage channels
            for n in range(len(self.AOchans)):
                self.aotask.ao_channels.add_ao_voltage_chan(
                    physical_channel='Dev1/ao%s' % self.AOchans[n],
                    name_to_assign_to_channel='chan_%s' % self.activeChannels[n],
                    min_val=minVolt[self.activeChannels[n]],
                    max_val=maxVolt[self.activeChannels[n]])

# ---Move----------------------------------------

    def move(self, axis, dist):
        """moves the position along the axis specified a distance dist."""
        self.channelsOpenStep()  # cambiar a movimiento por puntos
#        t = self.moveTime
        N = self.moveSamples
        # read initial position for all channels
        texts = [getattr(self, ax + "Label").text()
                 for ax in self.activeChannels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]
#        initPos = np.array(initPos, dtype=float)[:, np.newaxis]
#        fullPos = np.repeat(initPos, N, axis=1)

        # make position ramp for moving axis
#        ramp = np.linspace(0, dist, N)
#        fullPos[self.activeChannels.index(axis)] += ramp

#        factors = np.array([convFactors['x'], convFactors['y'],
#                           convFactors['z']])[:, np.newaxis]
#        fullSignal = fullPos/factors
        toc = ptime.time()
        rampx = np.linspace(float(initPos[0]), float(initPos[0]), N)
        rampy = np.linspace(float(initPos[1]), float(initPos[1]), N)
        rampz = np.linspace(float(initPos[2]), float(initPos[2]), N)

        if axis == "x":
            rampx = np.linspace(0, dist, N) + float(initPos[0])
        if axis == "y":
            rampy = np.linspace(0, dist, N) + float(initPos[1])
        if axis == "z":
            rampz = np.linspace(0, dist, N) + float(initPos[2])

        for i in range(N):
            self.aotask.write([rampx[i] / convFactors['x'],
                               rampy[i] / convFactors['y'],
                               rampz[i] / convFactors['z']], auto_start=True)
#            time.sleep(t / N)

        print("se mueve en", np.round(ptime.time() - toc, 4), "segs")

        # update position text
#        newPos = fullPos[self.activeChannels.index(axis)][-1]
#        newText = "{}".format(newPos)
#        getattr(self, axis + "Label").setText(newText)
        self.xLabel.setText("{}".format(np.around(float(rampx[-1]), 2)))
        self.yLabel.setText("{}".format(np.around(float(rampy[-1]), 2)))
        self.zLabel.setText("{}".format(np.around(float(rampz[-1]), 2)))

        self.paramChanged()
        if self.working:
            if self.scanMode.currentText() == "step scan":
                self.channelsOpenStep()
            else:
#            if self.scanMode.currentText() == "ramp scan" or self.scanMode.currentText() == "otra frec ramp":
                self.channelsOpen()


    def xMoveUp(self):
        self.move('x', float(getattr(self, 'y' + "StepEdit").text()))

    def xMoveDown(self):
        self.move('x', -float(getattr(self, 'y' + "StepEdit").text()))

    def yMoveUp(self):
        self.move('y', float(getattr(self, 'y' + "StepEdit").text()))

    def yMoveDown(self):
        self.move('y', -float(getattr(self, 'y' + "StepEdit").text()))

    def zMoveUp(self):
        self.move('z', float(getattr(self, 'z' + "StepEdit").text()))
        self.zDownButton.setEnabled(True)
        self.zDownButton.setStyleSheet(
            "QPushButton { background-color: }")
        self.zStepEdit.setStyleSheet("{ background-color: }")

    def zMoveDown(self):
        if self.initialPosition[2] < float(getattr(self, 'z' + "StepEdit").text()):
            print("OJO!, te vas a Z's negativos")
            self.zStepEdit.setStyleSheet(" background-color: red; ")
#            setStyleSheet("color: rgb(255, 0, 255);")
        else:
            self.move('z', -float(getattr(self, 'z' + "StepEdit").text()))
            self.zStepEdit.setStyleSheet("{ background-color: }")
        if self.initialPosition[2] == 0:  # para no ira z negativo
            self.zDownButton.setStyleSheet(
                "QPushButton { background-color: red; }"
                "QPushButton:pressed { background-color: blue; }")
            self.zDownButton.setEnabled(False)


    def goCM(self):
            self.zgotoLabel.setStyleSheet(" background-color: ")
            print("arranco en",float(self.xLabel.text()), float(self.yLabel.text()),
                  float(self.zLabel.text()))

            self.moveto(float(self.CMxValue.text()),
                        float(self.CMyValue.text()),
                        float(self.zLabel.text()))

            print("termino en", float(self.xLabel.text()), float(self.yLabel.text()),
                  float(self.zLabel.text()))

# ---goto. Para ir a una posicion especifica
    def goto(self):

        print("arranco en", float(self.xLabel.text()),
              float(self.yLabel.text()), float(self.zLabel.text()))

        self.moveto(float(self.xgotoLabel.text()),
                    float(self.ygotoLabel.text()),
                    float(self.zgotoLabel.text()))

        print("termino en", float(self.xLabel.text()),
              float(self.yLabel.text()), float(self.zLabel.text()))

        self.paramChanged()

# ---moveto ---
    def moveto(self, x, y, z):
        """moves the position along the axis to a specified point."""
        self.channelsOpenStep()  # se mueve de a puntos, no rampas.
        t = self.moveTime
        N = self.moveSamples

    # read initial position for all channels
        texts = [getattr(self, ax + "Label").text()
                 for ax in self.activeChannels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]

        if float(initPos[0]) != x or float(initPos[1]) != y or float(initPos[2]) != z:
            rampx = np.linspace(float(initPos[0]), x, N)
            rampy = np.linspace(float(initPos[1]), y, N)
            rampz = np.linspace(float(initPos[2]), z, N)

            tuc = ptime.time()
            for i in range(N):
                self.aotask.write([rampx[i] / convFactors['x'],
                                   rampy[i] / convFactors['y'],
                                   rampz[i] / convFactors['z']], auto_start=True)
                time.sleep(t / N)

            print("se mueve todo en", np.round(ptime.time()-tuc, 4), "segs")

            self.xLabel.setText("{}".format(np.around(float(rampx[-1]), 2)))
            self.yLabel.setText("{}".format(np.around(float(rampy[-1]), 2)))
            self.zLabel.setText("{}".format(np.around(float(rampz[-1]), 2)))
        else:
            print("¡YA ESTOY EN ESAS COORDENADAS!")


# ---  Shutters zone ---------------------------------
    def shutterred(self):
        if self.shutterredbutton.isChecked():
            self.openShutter("red")
        else:
            self.closeShutter("red")
    def shuttergreen(self):
        if self.shuttergreenbutton.isChecked():
            self.openShutter("green")
        else:
            self.closeShutter("green")
    def shutterotro(self):
        if self.shutterotrobutton.isChecked():
            self.openShutter("otro")
        else:
            self.closeShutter("otro")

    def openShutter(self, p):
        self.shuttersnidaq()
#        self.opendo()
        print("abre shutter", p)
        shutters = ["red", "green", "otro"]
        for i in range(3):
            if p == shutters[i]:
                self.shuttersignal[i] = True
        self.shuttertask.write(self.shuttersignal, auto_start=True)
        print(self.shuttersignal)

    def closeShutter(self, p):
        self.channelsOpen()
#        self.closedo()
        print("cierra shutter", p)
        shutters = ["red", "green", "otro"]
        for i in range(3):
            if p == shutters[i]:
                self.shuttersignal[i] = False
        self.shuttertask.write(self.shuttersignal, auto_start=True)
        print(self.shuttersignal)

    def shuttersnidaq(self):
        if self.shuttering == False:
            self.shuttering = True
            self.shuttertask = nidaqmx.Task("shutter")
            self.shuttertask.do_channels.add_do_chan(
                lines="Dev1/port0/line0:2", name_to_assign_to_lines='shutters',
                line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
        else:
            print("ya estaban abiertos los canales shutters")

# --- MovetoStart ---
    def MovetoStart(self):
        """ When called, it gets to the start point"""
        if self.dy==0:
            print("is already in start")
        else:
            self.inStart = True
            print("moving to start")
            self.done()

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
                samps_per_chan=self.moveSamples)


    #        tic = ptime.time()
            startX = float(self.initialPosition[0])
            startY = float(self.initialPosition[1])
            startZ = float(self.initialPosition[2])
            if self.scanMode.currentText() == "step scan":
                maximox = self.allstepsx[-1,self.dy]
                maximoy = self.allstepsy[-1,self.dy]
                maximoz = self.allstepsz[-1,self.dy]
            else:
#            if self.scanMode.currentText() == "ramp scan" or self.scanMode.currentText() == "otra frec ramp":
                stops = ((len(self.onerampx))-1) * self.dy
                maximox = self.totalrampx[stops]
                maximoy = self.totalrampy[stops]
                maximoz = self.totalrampz[stops]

            volviendox = np.linspace(maximox, startX, self.moveSamples)
            volviendoy = np.linspace(maximoy, startY, self.moveSamples)
            volviendoz = np.linspace(maximoz, startZ, self.moveSamples)

            volviendotodo = np.zeros((len(self.AOchans), len(volviendoy)))
            volviendotodo[0, :] = volviendox / convFactors['x']
            volviendotodo[1, :] = volviendoy / convFactors['y']
            volviendotodo[2, :] = volviendoz / convFactors['z']
    
            self.aotask.write(
                 volviendotodo, auto_start=True)
            self.aotask.wait_until_done()
    #        print(np.round(ptime.time() - tic, 5)*10**3, "MovetoStart (ms)")


            self.aotask.stop()
            self.aotask.close()

            if self.scanMode.currentText() == "step scan":
                self.channelsOpenStep()
            else:
#            if self.scanMode.currentText() == "ramp scan" or self.scanMode.currentText() == "otra frec ramp":
                self.channelsOpen()

        self.dy = 0



#--- SaveFrame ---
    def saveFrame(self):
        """ Config the path and name of the file to save, and save it"""


        timestr = time.strftime("%Y%m%d-%H%M%S")
        name = str(self.file_path + "/image-" + timestr + ".tiff")  # nombre con la fecha -hora
        guardado = Image.fromarray(self.image)
        guardado.save(name)

        print("\n Hipoteticamente Guardo la imagen\n")

    def openFolder(self):

        root = tk.Tk()
        root.withdraw()
        
        self.file_path = filedialog.askdirectory()
        print(self.file_path,2)
        self.NameDirValue.setText(self.file_path)

#--- CMmeasure que tambien arma los datos para modular.
    def CMmeasure(self):
        from scipy import ndimage
        Z = self.image
        N = len(Z)  # numberfoPixels
#        xcm = 0
#        ycm = 0
#        for i in range(N):
#            for j in range(N):
#                xcm = xcm + (Z[i,j]*i)
#                ycm = ycm + (Z[i,j]*j)
#        M = np.sum(Z)
#        xcm = xcm/M
#        ycm = ycm/M
        xcm, ycm = ndimage.measurements.center_of_mass(Z)  # Los calculo y da lo mismo
#        xc = int(np.round(xcm,2))
#        yc = int(np.round(ycm,2))
        Normal = self.scanRange / self.numberofPixels
        self.CMxValue.setText(str(xcm*Normal))
        self.CMyValue.setText(str(ycm*Normal))
#        resol = 2
#        for i in range(resol):
#            for j in range(resol):
#                ax.text(X[xc+i,yc+j],Y[xc+i,yc+j],"☻",color='w')
        lomas = np.max(Z)
        Npasos = 4
        paso = lomas/Npasos
        tec=time.time()
        SZ = Z.ravel()
        mapa = np.zeros((N,N))
        Smapa = mapa.ravel()
        for i in range(len(SZ)):
            if SZ[i] > paso:
                Smapa[i] = 1
            if SZ[i] > paso*2:
                Smapa[i] = 2
            if SZ[i] > paso*3:
                Smapa[i] = 3
        mapa = np.split(Smapa,N)
        print(np.round(time.time()-tec,4),"s tarda con 1 for\n")




app = QtGui.QApplication([])
win = ScanWidget(device)
win.show()

app.exec_()


