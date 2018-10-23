
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
from scipy import ndimage

import re

import tools
import viewbox_tools

import nidaqmx

device = nidaqmx.system.System.local().devices['Dev1']

convFactors = {'x': 25, 'y': 25, 'z': 1.683}
# la calibracion es 1 µm = 40 mV en x,y (galvos);
# en z, 0.17 µm = 0.1 V  ==> 1 µm = 0.58 V
# 1.68 um = 1 V ==> 1 um = 0.59V  # asi que promedie.
minVolt = {'x': -10, 'y': -10, 'z': 0}
maxVolt = {'x': 10, 'y': 10, 'z': 10}
resolucionDAQ = 0.0003 * 2 * convFactors['x'] # V => µm; uso el doble para no errarle
activeChannels = ["x", "y", "z"]
AOchans = [0, 1]  # , 2]  # x,y,z
detectModes = ['APD red', 'APD yellow', 'both APDs', 'PMT']
# detectModes[1:n] son los apd's; detectMode[-1] es el PMT y [-2] otros.
COchans = [0,1]  # apd rojo y verde
PMTchan = 1
scanModes = ['ramp scan', 'step scan', 'full frec ramp', "slalom"]

shutters = ["red", "STED", "yellow"]  # digitals out channesl [0, 1, 2]


# %% ScanWidget
class ScanWidget(QtGui.QFrame):
    def imageplot(self):
        if self.imagecheck.isChecked():
            self.img.setImage(self.image2, autoLevels=self.autoLevels)
        else:
            self.img.setImage(self.image, autoLevels=self.autoLevels)

    def graphplot(self):
#        if self.dy==0:
#            self.paramChanged()
        self.getInitPos()
        self.paramChangedInitialize()
        if self.graphcheck.isChecked():
            if self.imagecheck.isChecked():
                self.img.setImage(self.backimage2, autoLevels=self.autoLevels)
            else:
                self.img.setImage(self.backimage, autoLevels=self.autoLevels)
        else:
            self.img.setImage(self.image, autoLevels=self.autoLevels)

        verxi = np.concatenate((self.xini[:-1],
                               np.zeros(len(self.wantedrampx)),
                               np.zeros(len(self.xchange[1:-1])),
                               np.zeros(len(self.xback[:])),
                               np.zeros(len(self.xstops[1:]))))

        verxchange = np.concatenate((np.zeros(len(self.xini[:-1])),
                               np.zeros(len(self.wantedrampx)),
                               ((self.xchange[1:-1])),
                               np.zeros(len(self.xback[:])),
                               np.zeros(len(self.xstops[1:]))))

        verxback = np.concatenate((np.zeros(len(self.xini[:-1])),
                               np.zeros(len(self.wantedrampx)),
                               np.zeros(len(self.xchange[1:-1])),
                               ((self.xback[:])),
                               np.zeros(len(self.xstops[1:]))))

        verxstops = np.concatenate((np.zeros(len(self.xini[:-1])),
                               np.zeros(len(self.wantedrampx)),
                               np.zeros(len(self.xchange[1:-1])),
                               np.zeros(len(self.xback[:])),
                               self.xstops[1:]))

        plt.plot(verxi,'*-m')
        plt.plot(self.onerampx,'b.-')
        plt.plot(verxchange,'.-g')
        plt.plot(verxback,'.-c')
        plt.plot(verxstops,'*-y')
        plt.plot(self.onerampy[0,:],'k')
#        plt.plot(self.onerampy[1,:],'k')
        plt.show()

    def __init__(self, device, *args, **kwargs):  # agregue device

        super().__init__(*args, **kwargs)


        self.nidaq = device  # esto tiene que ir

        imageWidget = pg.GraphicsLayoutWidget()
        self.vb = imageWidget.addViewBox(row=1, col=1)

    # Parameters for smooth moving (to no go hard on the piezo (or galvos))
        self.moveTime = 10  / 10**3  # total time to move (s ==>ms)
        self.moveSamples = 1000  # samples to move
        self.moveRate = self.moveSamples / self.moveTime  # 10**5

    # LiveView Button
        self.liveviewButton = QtGui.QPushButton('confocal LIVEVIEW')
        self.liveviewButton.setCheckable(True)
        self.liveviewButton.clicked.connect(self.liveview)
        self.liveviewButton.setStyleSheet(
                "QPushButton { background-color: green; }"
                "QPushButton:pressed { background-color: blue; }")

        self.PSFMode = QtGui.QComboBox()
        self.PSFModes = ['XY normal psf', 'XZ', 'YZ']
        self.PSFMode.addItems(self.PSFModes)
        self.PSFMode.activated.connect(self.PSFYZ)

    # Presets simil inspector
        self.presetsMode = QtGui.QComboBox()
        self.presetsModes = ['normal', '10', '5','0.6', '3']
        self.presetsMode.addItems(self.presetsModes)

    # To save all images until stops
        self.VideoCheck = QtGui.QCheckBox('"video" save')
        self.VideoCheck.setChecked(False)

    # to run continuously
        self.Continouscheck = QtGui.QCheckBox('Continous')
        self.Continouscheck.setChecked(False)

    # to Calculate the mass center
        self.CMcheck = QtGui.QCheckBox('calcula CM')
        self.CMcheck.setChecked(False)
        self.CMcheck.clicked.connect(self.CMmeasure)

    # 2D Gaussian fit to estimate the center of a NP
        self.Gausscheck = QtGui.QCheckBox('calcula centro gaussiano')
        self.Gausscheck.setChecked(False)
        self.Gausscheck.clicked.connect(self.GaussMeasure)

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

        self.NameDirButton = QtGui.QPushButton('Select Dir')
        self.NameDirButton.clicked.connect(self.selectFolder)
#        filepath = main.file_path  # os.path.abspath("")
        self.file_path = os.path.abspath("")
        self.NameDirValue = QtGui.QLabel('')
        self.NameDirValue.setText(self.file_path)
        self.NameDirValue.setStyleSheet(" background-color: red; ")
        self.OpenButton = QtGui.QPushButton('open dir')
        self.OpenButton.clicked.connect(self.openFolder)

    # Select the wanted scan mode
        self.scanMode = QtGui.QComboBox()
#        self.scanModes = ['ramp scan', 'step scan', 'full frec ramp', "slalom"]
        self.scanMode.addItems(scanModes)

    # Plot ramps scan button
        self.graphcheck = QtGui.QCheckBox('Scan Plot')
        self.graphcheck.clicked.connect(self.graphplot)
        self.step = False

    # Plot ramps scan button
        self.imagecheck = QtGui.QCheckBox('Image change')
        self.imagecheck.clicked.connect(self.imageplot)

    # useful Booleans
        self.channelramp = False #canales
        self.PMTon = False
        self.APDson = False
        self.triggerAPD = False # separo los canales en partes
        self.triggerPMT = False
        self.channelsteps = False
        self.piezoramp = False
        self.piezosteps = False
#        self.inStart = False
#        self.working = False
        self.shuttering = False
        self.shuttersignal = [False, False, False]
#        self.preseteado = False  # Era por si fijaba los valores, pero no
        self.autoLevels = True
        self.YZ = False

        self.shuttersChannelsNidaq()  # los prendo al principio y me olvido

    # autoLevel image
        self.autoLevelscheck = QtGui.QCheckBox('Image change')
        self.autoLevelscheck.clicked.connect(self.autoLevelset)

    # Shutters buttons
        self.shutter0button = QtGui.QCheckBox('shutter Red')
        self.shutter0button.clicked.connect(self.shutter0)
        self.shutter1button = QtGui.QCheckBox('shutter STED')
        self.shutter1button.clicked.connect(self.shutter1)
        self.shutter2button = QtGui.QCheckBox('shutter Yellow')
        self.shutter2button.clicked.connect(self.shutter2)

    # ploting image with matplotlib (slow). if Npix>500 is very slow
        self.plotLivebutton = QtGui.QPushButton('Plot this frame')
        self.plotLivebutton.setChecked(False)
        self.plotLivebutton.clicked.connect(self.plotLive)

    # Select the detector
        self.detectMode = QtGui.QComboBox()
#        self.detectModes = ['APD red', 'APD green', 'both APDs', 'PMT']  lo agregue antes.
        self.detectMode.addItems(detectModes)

    # ROI buttons
        self.roi = None
        self.ROIButton = QtGui.QPushButton('ROI')
        self.ROIButton.setCheckable(True)
        self.ROIButton.clicked.connect(self.ROImethod)

        self.selectROIButton = QtGui.QPushButton('select ROI')
        self.selectROIButton.clicked.connect(self.selectROI)

    # Point scan
        self.PointButton = QtGui.QPushButton('Point scan')
        self.PointButton.setCheckable(True)
        self.PointButton.clicked.connect(self.PointStart)
        self.PointLabel = QtGui.QLabel('<strong>0.0')

    # Max counts
        self.maxcountsLabel = QtGui.QLabel('Max Counts')
        self.maxcountsEdit = QtGui.QLabel('<strong>0.0')

    # Scanning parameters

#        self.initialPositionLabel = QtGui.QLabel('Initial Pos [x0 y0 z0] (µm)')
#        self.initialPositionEdit = QtGui.QLineEdit('0 0 1')
        self.scanRangeLabel = QtGui.QLabel('Scan range (µm)')
        self.scanRangeEdit = QtGui.QLineEdit('10')
        self.pixelTimeLabel = QtGui.QLabel('Pixel time (ms)')
        self.pixelTimeEdit = QtGui.QLineEdit('0.01')
        self.numberofPixelsLabel = QtGui.QLabel('Number of pixels')
        self.numberofPixelsEdit = QtGui.QLineEdit('500')
        self.pixelSizeLabel = QtGui.QLabel('Pixel size (nm)')
        self.pixelSizeValue = QtGui.QLabel('')
        self.accelerationLabel = QtGui.QLabel('Acceleration (µm/ms^2)')
        self.accelerationEdit = QtGui.QLineEdit('120')
        self.vueltaLabel = QtGui.QLabel('Back Velocity (relative)')
        self.vueltaEdit = QtGui.QLineEdit('10')

        self.triggerLabel = QtGui.QLabel('Trigger ')
        self.triggerEdit = QtGui.QLineEdit('1')

        self.timeTotalLabel = QtGui.QLabel('total scan time (s)')
        self.timeTotalValue = QtGui.QLabel('')

        self.onlyInt = QtGui.QIntValidator(0,5000)
        self.numberofPixelsEdit.setValidator(self.onlyInt)
        self.onlypos = QtGui.QDoubleValidator(0, 1000,10)
        self.pixelTimeEdit.setValidator(self.onlypos)
        self.scanRangeEdit.setValidator(self.onlypos)

#        self.numberofPixelsEdit.textChanged.connect(self.paramChanged)
#        self.numberofPixelsEdit.textChanged.connect(self.zeroImage)

#        self.scanRangeEdit.textChanged.connect(self.paramChanged)
#        self.pixelTimeEdit.textChanged.connect(self.paramChanged)
#        self.accelerationEdit.textChanged.connect(self.paramChanged)
#        self.vueltaEdit.textChanged.connect(self.paramChanged)

#        self.scanMode.activated.connect(self.done)
        self.scanMode.activated.connect(self.SlalomMode)
#
#        self.detectMode.activated.connect(self.done)
#        self.detectMode.activated.connect(self.paramChanged)
#
#        self.PSFMode.activated.connect(self.done)
#        self.PSFMode.activated.connect(self.paramChanged)

#        self.presetsMode.activated.connect(self.done)
        self.presetsMode.activated.connect(self.Presets)

        self.paramWidget = QtGui.QWidget()

        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        grid.addWidget(imageWidget, 0, 0)
        grid.addWidget(self.paramWidget, 0, 1)

        subgrid = QtGui.QGridLayout()
        self.paramWidget.setLayout(subgrid)


    # Columna 1
        subgrid.addWidget(self.shutter0button,      0, 1)
        subgrid.addWidget(self.shutter2button,      1, 1)
        subgrid.addWidget(self.shutter1button,      2, 1)
        subgrid.addWidget(self.scanRangeLabel,      3, 1)
        subgrid.addWidget(self.scanRangeEdit,       4, 1)
        subgrid.addWidget(self.pixelTimeLabel,      5, 1)
        subgrid.addWidget(self.pixelTimeEdit,       6, 1)
        subgrid.addWidget(self.numberofPixelsLabel, 7, 1)
        subgrid.addWidget(self.numberofPixelsEdit,  8, 1)
        subgrid.addWidget(self.pixelSizeLabel,      9, 1)
        subgrid.addWidget(self.pixelSizeValue,     10, 1)
        subgrid.addWidget(self.liveviewButton,     11, 1)
        subgrid.addWidget(self.scanMode,            13, 1)
        subgrid.addWidget(self.timeTotalLabel,      14, 1)
        subgrid.addWidget(self.timeTotalValue,      15, 1)
        subgrid.addWidget(self.saveimageButton,     16, 1)
        subgrid.addWidget(self.autoLevelscheck,     17, 1)

    # Columna 2
        subgrid.addWidget(self.detectMode,        0, 2)
        subgrid.addWidget(self.NameDirButton,     1, 2)
        subgrid.addWidget(self.OpenButton,        2, 2)
#        subgrid.addWidget(self.triggerLabel,       4, 2)
#        subgrid.addWidget(self.triggerEdit,        5, 2)
#        subgrid.addWidget(self.accelerationLabel,  6, 2)
#        subgrid.addWidget(self.accelerationEdit,   7, 2)
        subgrid.addWidget(self.vueltaLabel,        8, 2)
        subgrid.addWidget(self.vueltaEdit,         9, 2)
        subgrid.addWidget(self.VideoCheck,        10, 2)
        subgrid.addWidget(self.Continouscheck,    11, 2)
        subgrid.addWidget(self.graphcheck,        12, 2)
        subgrid.addWidget(self.CMcheck,           13, 2)
        subgrid.addWidget(self.PSFMode,            15, 2)
        subgrid.addWidget(self.maxcountsLabel,      17, 2)
        subgrid.addWidget(self.maxcountsEdit,       18, 2)
    # Columna 3
#        subgrid.addWidget(self.algobutton,     0, 3)
        subgrid.addWidget(self.ROIButton,       2, 3)
        subgrid.addWidget(self.selectROIButton, 3, 3)
        subgrid.addWidget(self.PointButton,      6, 3)
        subgrid.addWidget(self.PointLabel,       7, 3)
        subgrid.addWidget(self.plotLivebutton,    9, 3)
        subgrid.addWidget(self.imagecheck,       11, 3)
        subgrid.addWidget(self.Gausscheck,        13, 3)
        subgrid.addWidget(self.presetsMode,        15, 3)

# ---  Positioner part ---------------------------------
        # Axes control
        self.xLabel = QtGui.QLabel('-5.0')
        self.xLabel.setTextFormat(QtCore.Qt.RichText)
        self.xname =  QtGui.QLabel("<strong>x =")
        self.xname.setTextFormat(QtCore.Qt.RichText)
        self.xUpButton = QtGui.QPushButton("(+x) ►")  # →
        self.xUpButton.pressed.connect(self.xMoveUp)
        self.xDownButton = QtGui.QPushButton("◄ (-x)")  # ←
        self.xDownButton.pressed.connect(self.xMoveDown)
        self.xStepEdit = QtGui.QLineEdit("1")
        self.xStepUnit = QtGui.QLabel(" µm")

        self.yLabel = QtGui.QLabel('-5.0')
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
        layout.addWidget(self.xname,       1, 0)
        layout.addWidget(self.xLabel,      1, 1)
        layout.addWidget(self.xUpButton,   2, 4,2,1)
        layout.addWidget(self.xDownButton, 2, 2,2,1)
#        layout.addWidget(QtGui.QLabel("Step x"), 1, 6)
#        layout.addWidget(self.xStepEdit, 1, 7)
#        layout.addWidget(self.xStepUnit, 1, 8)

        layout.addWidget(self.yname,       2, 0)
        layout.addWidget(self.yLabel,      2, 1)
        layout.addWidget(self.yUpButton,   1, 3,2,1)
        layout.addWidget(self.yDownButton, 3, 3,2,1)
        layout.addWidget(QtGui.QLabel("Length of step xy"), 1, 6)
        layout.addWidget(self.yStepEdit,   2, 6)
        layout.addWidget(self.yStepUnit,   2, 7)

        layout.addWidget(self.zname,       4, 0)
        layout.addWidget(self.zLabel,      4, 1)
        layout.addWidget(self.zUpButton,   1, 5,2,1)
        layout.addWidget(self.zDownButton, 3, 5,2,1)
        layout.addWidget(QtGui.QLabel("Length of step z"), 3, 6)
        layout.addWidget(self.zStepEdit,   4, 6)
        layout.addWidget(self.zStepUnit,   4, 7)

        layout.addWidget(self.NameDirValue, 8, 0, 1, 7)
        
#        self.yStepEdit.setValidator(self.onlypos)
#        self.zStepEdit.setValidator(self.onlypos)

        self.gotoWidget = QtGui.QWidget()
        grid.addWidget(self.gotoWidget, 1, 1)
        layout2 = QtGui.QGridLayout()
        self.gotoWidget.setLayout(layout2)
        layout2.addWidget(QtGui.QLabel("X"), 1, 7)
        layout2.addWidget(QtGui.QLabel("Y"), 2, 7)
        layout2.addWidget(QtGui.QLabel("Z"), 3, 7)
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

        self.GaussxLabel = QtGui.QLabel('Gauss X')
        self.GaussxValue = QtGui.QLabel('NaN')
        self.GaussyLabel = QtGui.QLabel('Gauss Y')
        self.GaussyValue = QtGui.QLabel('NaN')
        layout2.addWidget(self.GaussxLabel, 6, 8)
        layout2.addWidget(self.GaussxValue, 7, 8)
        layout2.addWidget(self.GaussyLabel, 6, 9)
        layout2.addWidget(self.GaussyValue, 7, 9)

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

        self.viewtimer = QtCore.QTimer()
        self.viewtimer.timeout.connect(self.APDupdateView)

        self.PMTtimer = QtCore.QTimer()
        self.PMTtimer.timeout.connect(self.PMTupdate)

        self.steptimer = QtCore.QTimer()
        self.steptimer.timeout.connect(self.stepScan)

        self.blankImage = np.zeros((self.numberofPixels, self.numberofPixels))
        self.image = np.zeros((self.numberofPixels, self.numberofPixels))#self.blankImage
        self.image2 = np.zeros((self.numberofPixels, self.numberofPixels))#self.blankImage
        self.dy = 0

        #self.startRutine()  # que lea de algun lado la posicion y la setee como start x,y,z

#    def startRutine(self):
#        read algo
    def autoLevelset(self):
        if self.autoLevelscheck.isChecked():
            self.autoLevels = True
        else:
            self.autoLevels = False

    def PSFYZ(self):
        if self.PSFMode.currentText() == self.PSFMode[0]:
            self.YZ = False
        else:
            self.YZ = True

    def SlalomMode(self):
        if self.scanMode.currentText() == "slalom":
            self.vueltaEdit.setText("1")
            self.vueltaEdit.setStyleSheet(" background-color: red; ")
        else:
            self.vueltaEdit.setStyleSheet("{ background-color: }")

    def zeroImage(self):
        self.blankImage = np.zeros((self.numberofPixels, self.numberofPixels))
        self.image = np.zeros((self.numberofPixels, self.numberofPixels))#self.blankImage
        self.image2 = np.zeros((self.numberofPixels, self.numberofPixels))#self.blankImage

# %%--- paramChanged / PARAMCHANGEDinitialize
    def paramChangedInitialize(self):
        tic = ptime.time()

        a = [self.scanRange, self.numberofPixels, self.pixelTime,
             self.initialPosition, self.scanModeSet,self.PSFModeSet]
        b = [float(self.scanRangeEdit.text()), int(self.numberofPixelsEdit.text()),
             float(self.pixelTimeEdit.text()) / 10**3, (float(self.xLabel.text()),
                  float(self.yLabel.text()), float(self.zLabel.text())),
                  self.scanMode.currentText(), self.PSFMode.currentText()]
        print("\n",a)
        print(b, "\n")

        if a == b:
            #print("no cambió ningun parametro\n")
            p=0
        else:
            #print("pasaron cosas\n")
            self.paramChanged()

        toc = ptime.time()
        print("tiempo paramchangeInitailize (ms)", (toc-tic)*10**3,"\n")
    def paramChanged(self):
        tic = ptime.time()
        """ Update the parameters when the user edit them """

        self.scanModeSet = self.scanMode.currentText()
        self.PSFModeSet = self.PSFMode.currentText()

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
        #print(self.Napd, "=Napd\n")

        self.pixelSize = self.scanRange / self.numberofPixels

        self.pixelSizeValue.setText('{}'.format(np.around(
                                        1000 * self.pixelSize, 2)))  # en nm

        self.linetime = self.pixelTime * self.numberofPixels  # en s

#        #print(self.linetime, "linetime")

        self.timeTotalValue.setText('{}'.format(np.around(
                         self.numberofPixels * self.linetime, 2)))

        if self.scanMode.currentText() == scanModes[1]:  # "step scan":
        # en el caso step no hay frecuencias
            #print("Step time, very slow")
            self.Steps()
#            #print(self.linetime, "linetime\n")

        else:
            if self.scanMode.currentText() == scanModes[2]:  # "full frec ramp":
                self.sampleRate = (self.scanRange /resolucionDAQ) / (self.linetime)
                self.nSamplesrampa = int(np.ceil(self.scanRange /resolucionDAQ))
                #print("a full resolucion\n", self.nSamplesrampa,                "Nsamples", self.sampleRate, "sampleRate")

            else: #self.scanMode.currentText() == "ramp scan" or self.scanMode.currentText() == "slalom":
                self.nSamplesrampa = self.numberofPixels  # self.apdrate*self.linetime
                self.sampleRate = np.round(1 / self.pixelTime,9)  # self.apdrate
                #print("los Nsamples = Npix y 1/tpix la frecuencia\n",                self.nSamplesrampa, "Nsamples", self.sampleRate, "sampleRate")
            self.Ramps()
            self.reallinetime = len(self.onerampx) * self.pixelTime  # seconds
            #print(self.linetime, "linetime")
            print(self.reallinetime, "reallinetime\n")
            self.PMT = np.zeros(len(self.onerampx))
        #print(self.linetime, "linetime\n")

        self.autoLevels = True
        self.zeroImage()
      # numberofpixels is the relevant part of the total ramp.
        self.APD = np.zeros((self.numberofPixels + self.pixelsofftotal)*self.Napd)
        self.APD2 = self.APD
        self.APDstep = np.zeros((self.Napd+1))

        toc = ptime.time()
        print("\n tiempo paramCahnged (ms)", (toc-tic)*10**3,"\n")
#        self.PMT = np.zeros((self.numberofPixels + self.pixelsofftotal, self.numberofPixels))

# %% cosas para el save image
    def saveimage(self):
        """ la idea es que escanee la zona deseada (desde cero) una sola vez,
        y guarde la imagen"""
        if self.saveimageButton.isChecked():
            self.MovetoStart()
            self.save = True
            self.saveimageButton.setText('Abort')
            self.liveviewStart()

        else:
            self.save = False
            #print("Abort")
            self.saveimageButton.setText('Retry Scan and Stop')
            self.liveviewStop()

# %%--- liveview------
# This is the function triggered by pressing the liveview button
    def liveview(self):
        """ Image live view when not recording
        """
        if self.liveviewButton.isChecked():
            self.save = False
            self.paramChangedInitialize()
            self.MovetoStart()  # getini: se va
            self.liveviewStart()
        else:
            self.liveviewStop()

    def liveviewStart(self):
#        self.working = True
#        self.paramChangedInitialize()
        if self.scanMode.currentText() == scanModes[1]:  # "step scan":
            self.channelsOpenStep()
#            self.inStart = False
            self.tic = ptime.time()
            self.steptimer.start(5)#100*self.pixelTime*10**3)  # imput in ms
        else:
#        if self.scanMode.currentText() == "ramp scan" or self.scanMode.currentText() == "otra frec ramp":
            self.channelsOpenRamp()
            self.tic = ptime.time()
            if self.detectMode.currentText() == "PMT":
                self.rampScanPMT()
            else:
                self.rampScanAPD()

    def rampScanPMT(self):
#        self.MovetoStart()
        self.startingRamps()
#        self.tic = ptime.time()
        self.PMTtimer.start(self.reallinetime*10**3)  # imput in ms

    def rampScanAPD(self):
#        self.MovetoStart()
        self.startingRamps()
#        self.tic = ptime.time()
        self.viewtimer.start(self.reallinetime*10**3)  # imput in ms


    def liveviewStop(self):
        if self.save:
            self.saveimageButton.setChecked(False)
            self.saveimageButton.setText('Scan and save')
            self.save = False
        self.MovetoStart()
        #print("liveStop")
        self.liveviewButton.setChecked(False)
        self.viewtimer.stop()
        self.steptimer.stop()
        self.PMTtimer.stop()
        self.closeShutter("red")
        self.done()

#    def startingSteps(self):
# %%
    def startingRamps(self):
        self.openShutter("red")
#        self.working = True
    # Send the signals to the NiDaq, but only start when the trigger is on
        if self.YZ:
            self.aotask.write(np.array(
                [self.totalrampx / convFactors['x'],
                 self.totalrampy / convFactors['y'],
                 self.totalrampz / convFactors['z']]), auto_start=True)
        else:
            self.aotask.write(np.array(
                [self.totalrampx / convFactors['x'],
                 self.totalrampy / convFactors['y']]), auto_start=True)
    #             self.totalrampz / convFactors['z']]), auto_start=True)
#        self.inStart = False
        print("ya arranca...")
        self.APD1task.start()
        self.APD2task.start()
    # Starting the trigger. It have a controllable 'delay'
        self.triggertask.write(self.trigger, auto_start=True)


# %% runing Ramp loop (APD)
    def APDupdateView(self):
        paso = 1

    # The counter reads this numbers of points when the trigger starts
        if self.detectMode .currentText() == detectModes[0]:
            self.APD[:] = self.APD1task.read(
                      ((self.numberofPixels + self.pixelsofftotal)*self.Napd))
        elif self.detectMode .currentText() == detectModes[1]:
            self.APD[:] = self.APD2task.read(
                      ((self.numberofPixels + self.pixelsofftotal)*self.Napd))
        elif self.detectMode .currentText() == detectModes[-2]:
#            #print("se viene!")
            (self.APD, self.APD2) = (self.APD1task.read(((self.numberofPixels + self.pixelsofftotal)*self.Napd)),
                self.APD2task.read(((self.numberofPixels + self.pixelsofftotal)*self.Napd)))
#        elif self.detectMode .currentText() == detectModes[-1]:
#            print("algo salio muy mal. entró a APDupdate, con la opcion PMT")

        # have to analize the signal from the counter
        self.apdpostprocessing()

        self.image[:, -1-self.dy] = self.counts[:] #+ np.random.rand(self.numberofPixels)[:] # f
        """ verificar si Slalom es mas rapido que normal"""
        if self.scanMode.currentText() == scanModes[-1]:  # "slalom":
            self.image[:, -2-self.dy] = (self.backcounts[:])  # f
            paso = 2
        else:
            self.backimage[:, -1-self.dy] = self.backcounts[:]  # np.flip(,0)

        self.image2[:, -1-self.dy] = self.counts2[:]  #+ 50*np.random.rand(self.numberofPixels)[:] # f
        self.backimage2[:, -1-self.dy] = self.backcounts2[:]  # f

    # The plotting method is slow (2-3 ms each, for 500x500 pix)
    #, don't know how to do it fast
    #, so I´m plotting in packages. It's looks like realtime
        if self.numberofPixels >= 500:
            multi5 = np.arange(0, self.numberofPixels, 14)
        elif self.numberofPixels >= 200:
            multi5 = np.arange(0, self.numberofPixels, 9)
        else:
            multi5 = np.arange(0, self.numberofPixels, 2)

        if self.dy in multi5:
            if self.imagecheck.isChecked():
                self.img.setImage(self.image2, autoLevels=self.autoLevels)
            else:
                self.img.setImage(self.image, autoLevels=self.autoLevels)
            self.MaxCounts()

        if self.dy < self.numberofPixels-paso:
            self.dy = self.dy + paso
        else:
            self.autoLevels = False
#            self.img.setImage(self.image, autoLevels=self.autoLevels)
            if self.save:
                self.saveFrame()
                self.saveimageButton.setText('End')
                if self.CMcheck.isChecked():
                    self.CMmeasure()
                self.liveviewStop()
                self.mapa()
            else:
              if self.VideoCheck.isChecked():
                  self.saveFrame()  # para guardar siempre (Alan idea)
              print(ptime.time()-self.tic, "Tiempo imagen completa.")
              self.viewtimer.stop()
              self.triggertask.stop()
              self.aotask.stop()
              self.APDstop()
              if self.CMcheck.isChecked():
                  self.CMmeasure()
              if self.Gausscheck.isChecked():
                  self.GaussMeasure()
              self.MovetoStart()
              if self.Continouscheck.isChecked():
                  self.liveviewStart()
              else:
                  self.liveviewStop()


    def APDstop(self):
        try:
            self.APDtask.stop()
        except:
            pass
        try:
            self.APD2task.stop()
        except:
            pass

    def MaxCounts(self):
        m = np.max(self.image)
        if m >= (5000 * self.pixelTime):
            self.maxcountsEdit.setText("<strong>{}".format(float(m)))
            self.maxcountsEdit.setStyleSheet(" background-color: red; ")
        else:
            self.maxcountsEdit.setText("<strong>{}".format(float(m)))
            self.maxcountsEdit.setStyleSheet("{ background-color: }")
# %% runing Ramp loop (PMT)
    def PMTupdate(self):
        paso = 1
    # The counter reads this numbers of points when the trigger starts
        self.PMT[:] = self.PMTtask.read(len(self.onerampx))
        self.triggertask.write(self.trigger, auto_start=True)
#        self.PMTtask.wait_until_done()  # no va porque quiere medirlo TODO

    # limpio la parte acelerada.
        pixelsEnd = len(self.xini[:-1]) + self.numberofPixels
        self.image[:, -1-self.dy] = self.PMT[len(self.xini[:-1]):pixelsEnd]  # f

        pixelsIniB = pixelsEnd+len(self.xchange[1:-1])
        if self.scanMode.currentText() == scanModes[-1]:  # "slalom":
            self.image[:, -2-self.dy] = (self.PMT[pixelsIniB : -len(self.xstops[1:])])
            paso = 2
        else:
            self.backimage[:, -1-self.dy] = self.PMT[pixelsIniB : -len(self.xstops[1:])]  # f

    # The plotting method is slow (2-3 ms each, for 500x500 pix)
    #, don't know how to do it fast
    #, so I´m plotting in packages. It's looks like realtime
        if self.numberofPixels >= 1000:  # (self.pixelTime*10**3) <= 0.5:
            multi5 = np.arange(0, self.numberofPixels, 20)
        elif self.numberofPixels >= 101:
            multi5 = np.arange(0, self.numberofPixels, 10)
        else:
            multi5 = np.arange(0, self.numberofPixels, 2)

        if self.dy in multi5:
            if self.graphcheck.isChecked():
                self.img.setImage(self.backimage, autoLevels=self.autoLevels)
            else:
                self.img.setImage(self.image, autoLevels=self.autoLevels)

        if self.dy < self.numberofPixels-paso:
            self.dy = self.dy + paso
        else:
            self.autoLevels = False
            if self.save:
                self.saveFrame()
                self.saveimageButton.setText('End')
                if self.CMcheck.isChecked():
                    self.CMmeasure()
                self.liveviewStop()
                self.mapa()
            else:
              if self.VideoCheck.isChecked():
                  self.saveFrame()  # para guardar siempre (Alan idea)
              print(ptime.time()-self.tic, "Tiempo imagen completa.")
              self.PMTtimer.stop()
              self.triggertask.stop()
              self.aotask.stop()
              self.PMTtask.stop()
              if self.CMcheck.isChecked():
                  self.CMmeasure()
              self.MovetoStart()
              if self.Continouscheck.isChecked():
                  self.liveviewStart()
              else:
                  self.MovetoStart()
                  self.liveviewStop()


# %% --- Creating Ramps  ----
    def Ramps(self):
        tic = ptime.time()
    # arma los barridos con los parametros dados
        self.counts = np.zeros((self.numberofPixels))
        self.counts2 = np.zeros((self.numberofPixels))#self.counts

        self.acceleration()
        self.backcounts = np.zeros((self.pixelsoffB))
        self.backcounts2 = np.zeros((self.pixelsoffB)) # self.backcounts
        self.backimage = np.zeros((self.pixelsoffB, self.numberofPixels))  # para la vuelta (poner back Velocity=1)
        self.backimage2 = np.zeros((self.pixelsoffB, self.numberofPixels)) # self.backimage
#    Barrido x
        startX = float(self.initialPosition[0])
        sizeX = self.scanRange
        Npuntos = self.nSamplesrampa  # self.numberofPixels  #
        wantedrampx = np.linspace(0, sizeX, Npuntos) + self.xini[-1]

        self.onerampx = np.concatenate((self.xini[:-1],
                                             wantedrampx,
                                             self.xchange[1:-1],
                                             self.xback[:],
                                             self.xstops[1:]))
        self.wantedrampx = wantedrampx

        print(len(self.xini[:-1]), "xipuntos\n",
              len(wantedrampx), "Npuntos\n",
              len(self.xchange[1:-1]), "xchangepuntos\n",
              len(self.xback[:]), "xbackpuntos\n",
              len(self.xstops[1:]), "xstopspuntos\n")

        self.totalrampx = np.tile(self.onerampx, self.numberofPixels)

#    Barrido z (Stay in the initial position)
        startZ = float(self.initialPosition[2])
        self.totalrampz = np.ones(len(self.totalrampx)) * startZ

#    Barrido y (Constant in lines, grow every step y)
        startY = float(self.initialPosition[1])

        stepy = self.scanRange / self.numberofPixels
        rampay = np.ones(len(self.onerampx))*startY

        muchasrampasy = np.tile(rampay, (self.numberofPixels, 1))
        self.onerampy = np.zeros((self.numberofPixels, len(rampay)))

        if self.scanMode.currentText() == scanModes[-1]:  # "slalom":  # Gotta go fast
            fast=2
        else:
            fast=1

        p = len(self.xini[:-1]) + len(wantedrampx)
        for i in range(self.numberofPixels):
            j = fast*i
            self.onerampy[i, :p] = muchasrampasy[i, :p] + (j)  *stepy
            self.onerampy[i, p:] = muchasrampasy[i, p:] + (j+1)*stepy

        self.totalrampy = (self.onerampy.ravel())

        if self.PSFMode.currentText() == 'XY normal psf':
            #print("escaneo x y normal R")
            p=0

        elif self.PSFMode.currentText() == 'XZ':
            #print("intercambio y por z R")
            self.totalrampz = self.totalrampy - startY + startZ
            self.totalrampy = np.ones(len(self.totalrampx)) * startY

        elif self.PSFMode.currentText() == 'YZ':
            #print("intercambio x por z R")
            self.totalrampz = self.totalrampy - startY + startZ
            self.totalrampy = self.totalrampx - startX + startY
            self.totalrampx = np.ones(len(self.totalrampx)) * startX

        toc = ptime.time()
        print("\n tiempo Ramps (ms)", (toc-tic)*10**3,"\n")
# %% posptocessing APD signal
    def apdpostprocessing(self):
        """ takes the evergrowing valors from the counter measure and convert
        it into "number or events" """
#        tic = ptime.time()
        Napd = self.Napd

#        j = self.dy

#        if self.pixelsoffL == 0:
#            self.counts[0] = self.APD[Napd-1] - self.APD[0]
#            self.counts2[0] = self.APD2[Napd-1] - self.APD2[0]
#
#        else:
#            self.counts[0] = self.APD[(Napd*(1+self.pixelsoffL))-1]-self.APD[(Napd*(self.pixelsoffL))-1]
#            self.counts2[0] = self.APD2[(Napd*(1+self.pixelsoffL))-1]-self.APD2[(Napd*(1+self.pixelsoffL-1))-1]

        self.counts[0] = 0
        self.counts[0:5] = 5  # probando cosas

        for i in range(1, self.numberofPixels):
            ei = ((self.pixelsoffL+i)   * Napd)-1
            ef = ((self.pixelsoffL+i+1) * Napd)-1
            self.counts[i] = self.APD[ef] - self.APD[ei]
            self.counts2[i] = self.APD2[ef] - self.APD2[ei]
        # Lo que sigue esta en creacion, para la imagen de vuelta

        for i in range(len(self.backcounts)):  # len(back...)= pixelsoffB
#            evi = ((self.pixelsoffR + i + 1) * Napd)
#            evf = ((self.pixelsoffR + i) * Napd)
            evi = (-(self.pixelsoffR + self.pixelsoffB) + (i)  ) * Napd
            evf = (-(self.pixelsoffR + self.pixelsoffB) + (i+1)) * Napd
            self.backcounts[i] = self.APD[evf] - self.APD[evi]
            self.backcounts2[i] = self.APD2[evf] - self.APD2[evi]

#  puede fallar en la primer y/o ultima fila.

#        try:  No necesito hacer el try, como mucho hace las cuentas con una matriz de ceros
#            if self.pixelsoffL == 0:
#                self.counts2[0] = self.APD2[Napd-1] - self.APD2[0]
#            else:
#                self.counts2[0] = self.APD2[(Napd*(1+self.pixelsoffL))-1]-self.APD2[(Napd*(1+self.pixelsoffL-1))-1]
#
#            for i in range(1, self.numberofPixels):
#                ei = ((self.pixelsoffL+i)   * Napd)-1
#                ef = ((self.pixelsoffL+i+1) * Napd)-1
#                self.counts2[i] = self.APD2[ef] - self.APD2[ei]
#
##     Lo que sigue esta en creacion, para la imagen de vuelta
#
#            for i in range(len(self.backcounts2)):  # len(back...)= pixelsoffB
#    #            evi = ((self.pixelsoffR + i + 1) * Napd)
#    #            evf = ((self.pixelsoffR + i) * Napd)
#                evi = (-(self.pixelsoffR + self.pixelsoffB) + (i)  ) * Napd
#                evf = (-(self.pixelsoffR + self.pixelsoffB) + (i+1)) * Napd
#                self.backcounts2[i] = self.APD2[evf] - self.APD2[evi]
#        except:
#            pass
#        toc = ptime.time()
#        print("\n tiempo postprocessing (ms)", (toc-tic)*10**3,"\n")
# %%-------Aceleracion----------------------------------------------
    def acceleration(self):
        """ it creates the smooths-edge signals to send to the piezo
        It´s just an u.a.r.m. movement equation"""  # MRUV
    #        aceleracion = 120  # µm/ms^2  segun inspector
#        acceleration = float(self.accelerationEdit.text())  # editable
        T = self.numberofPixels * self.pixelTime * 10**3  # all in ms
        velocity = (self.scanRange / T)
        rate = self.sampleRate*10**-3
        acceleration = (200*self.scanRange)/((self.numberofPixels*self.pixelTime)**2)

        startX = float(self.initialPosition[0])

        ti = velocity / acceleration
        xipuntos = int(np.ceil(ti * rate)) + 10

        xini = np.zeros(xipuntos)
        tiempoi = np.linspace(0,ti,xipuntos)
        for i in range(xipuntos):
            xini[i] = 0.5*acceleration*(((tiempoi[i])**2-(tiempoi[-1]**2))) + startX

        xr = xini[-1] + self.scanRange
#        tr = T + ti

        Vback = float(self.vueltaEdit.text())  # /V

    # impongo una velocidad de vuelta Vback veces mayor a la de ida
        tcasi = ((1+Vback) * velocity) / acceleration  # -a*t + V = -Vback*V
        xchangepuntos = int(np.ceil(tcasi * rate)) +10
        tiempofin = np.linspace(0, tcasi, xchangepuntos)
        xchange = np.zeros(xchangepuntos)
        for i in range(xchangepuntos):
            xchange[i] = (-0.5*acceleration*((tiempofin[i])**2) + velocity * (tiempofin[i]) ) + xr

    # After the wanted ramp, it get a negative acceleration:
        av = acceleration
        tlow = Vback*velocity/av
        xlow = 0.5*av*(tlow**2) + startX
        Nvuelta = abs(int(np.round(((xchange[-1]-xlow)/(Vback*velocity)) * (rate))))

    # To avoid wrong going back in x
        if xchange[-1] < xlow:
            if xchange[-1] < startX:
                q = np.where(xchange<=startX)[0][0]
                xchange = xchange[:q]
                print("! xchange < 0")
                self.xback = np.linspace(0,0,4) + startX  #e lo creo para que no tire error nomas

            else:
                q = np.where(xchange <= xlow)[0][0]
                xchange = xchange[:q]
                self.xback = np.linspace(xlow, startX, Nvuelta)
                print("! xchange < xlow")
            xstops = np.linspace(0,0,2) + startX
        else:

            self.xback = np.linspace(xchange[-1], xlow, Nvuelta)

            xlowpuntos = int(np.ceil(tlow * rate)) +10
            tiempolow=np.linspace(0,tlow,xlowpuntos)
            #print("acceleration ok")
            xstops=np.zeros(xlowpuntos)
            for i in range(xlowpuntos):
                xstops[i] = 0.5*(av)*(tiempolow[i]**2) + startX

            xstops=np.flip(xstops,axis=0)
        #print("\n")

        self.xini = xini
        self.xchange = xchange
        self.xstops = xstops

    # Don't want to plot the accelerated zones
        NoffL = len(xini[:-1])
        NoffM = len(xchange[1:-1])
        NoffB = len(self.xback[:])
        NoffR = len(xstops[1:])
        toffL = NoffL/self.sampleRate
        toffR = NoffR/self.sampleRate
        toffM = NoffM/self.sampleRate
        toffB = NoffB/self.sampleRate
#        toff = toffL + toffR
        self.pixelsoffL = int(np.round(toffL*self.apdrate/self.Napd))
        self.pixelsoffM = int(np.round(toffM*self.apdrate/self.Napd))
        self.pixelsoffB = int(np.round(toffB*self.apdrate/self.Napd))
        self.pixelsoffR = int(np.round(toffR*self.apdrate/self.Napd))
        tofftotal = toffL+toffM+toffB+toffR
        self.pixelsofftotal = int(np.round((tofftotal)*self.apdrate/self.Napd))
        print("pixelsofftotal", self.pixelsofftotal,  # Si no dan lo mismo, puedo tener problemas
              "\n pixels off Suma", self.pixelsoffL+self.pixelsoffM+self.pixelsoffB+self.pixelsoffR)


# %% --- ChannelsOpen (todos)
    def channelsOpen(self):
        if self.scanMode.currentText() == scanModes[1]:  # "step scan":
            self.channelsOpenStep()
        else:
#            if self.scanMode.currentText() == "ramp scan" or self.scanMode.currentText() == "otra frec ramp":
            self.channelsOpenRamp()

    def channelsOpenRamp(self):  # channelsOpen
        """ Open and Config of all the channels for use"""
        if self.channelramp:
            print("ya esta abierto ramp")
        else:
            if self.channelsteps:
                self.done()
            self.PiezoOpenRamp()
            if self.detectMode.currentText() == 'PMT':
                self.PMTOpen()
                self.TriggerOpenPMT()
            else:
                self.APDOpen()
                self.TriggerOpenAPD()
            self.channelramp = True

    def channelsOpenStep(self):
        """ Open and Config of all the channels for use"""
        if self.channelsteps:
            print("ya esta abierto step")
        else:
            if self.channelramp:
                self.done()
            self.PiezoOpenStep()
            self.APDOpen()
            self.channelsteps = True

    def PiezoOpenRamp(self):
        if self.piezoramp:
            print("Ya estaban abiertos los canales rampa")  # to dont open again
        else:
            if self.piezosteps:
                self.aotask.stop()
                self.aotask.close()
                #print("cierro auque no es necesario")
        # Create the channels
            self.aotask = nidaqmx.Task('aotask')
            if self.YZ:
                AOchans = [0,1,2]
        # Following loop creates the voltage channels
            for n in range(len(AOchans)):
                self.aotask.ao_channels.add_ao_voltage_chan(
                    physical_channel='Dev1/ao%s' % AOchans[n],
                    name_to_assign_to_channel='chan_%s' % activeChannels[n],
                    min_val=minVolt[activeChannels[n]],
                    max_val=maxVolt[activeChannels[n]])

            self.piezoramp = True
            self.aotask.timing.cfg_samp_clk_timing(
                rate=self.sampleRate,
#                source=r'100kHzTimeBase',
                sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                samps_per_chan=len(self.totalrampx))

    def PiezoOpenStep(self):
        if self.piezosteps:
            print("Ya estaban abiertos los canales steps")  # to dont open again
        else:
            if self.piezoramp:
                self.aotask.stop()
                self.aotask.close()
                #print("cierro para abrir de nuevo")
#           else:
            self.piezosteps = True
        # Create the channels
            self.aotask = nidaqmx.Task('aotask')
        # Following loop creates the voltage channels
            for n in range(len(AOchans)):
                self.aotask.ao_channels.add_ao_voltage_chan(
                    physical_channel='Dev1/ao%s' % AOchans[n],
                    name_to_assign_to_channel='chan_%s' % activeChannels[n],
                    min_val=minVolt[activeChannels[n]],
                    max_val=maxVolt[activeChannels[n]])

    def APDOpen(self):
        if self.APDson:  # esto puede fallar cuando cambio de ramp a step
            print("Ya esta algun APD")  # to dont open again
            p=0
        else:
            if self.PMTon:
                #print("ojo que sigue preparado el PMT (no hago nada al respecto)")
                p=0
            self.APDson = True
            self.APD1task = nidaqmx.Task('APD1task')

            # Configure the counter channel to read the APD
            self.APD1task.ci_channels.add_ci_count_edges_chan(counter='Dev1/ctr{}'.format(COchans[0]),
                                name_to_assign_to_channel=u'conter_RED',
                                initial_count=0)
            if self.scanMode.currentText() == scanModes[1]:  # "step scan":
                totalcinumber = self.Napd + 1
            else:
                totalcinumber = ((self.numberofPixels+self.pixelsofftotal)*self.Napd)*self.numberofPixels

            self.APD1task.timing.cfg_samp_clk_timing(
              rate=self.apdrate, sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
              source=r'100kHzTimebase',  # 1000k
              samps_per_chan = totalcinumber)

            self.APD2task = nidaqmx.Task('APD2task')

            # Configure the counter channel to read the APD
            self.APD2task.ci_channels.add_ci_count_edges_chan(counter='Dev1/ctr{}'.format(COchans[1]),
                                name_to_assign_to_channel=u'conter_GREEN',
                                initial_count=0)

            self.APD2task.timing.cfg_samp_clk_timing(
              rate=self.apdrate, sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
              source=r'100kHzTimebase',
              samps_per_chan = totalcinumber)
            self.totalcinumber = totalcinumber

    def PMTOpen(self):
        if self.PMTon:
            print("Ya esta el PMT")  # to dont open again
            p=0
        else:
            if self.APDson:
                #print("ojo que sigue preparado el APD (no hago nada al respecto)")
                p=0
            self.PMTon = True
            self.PMTtask = nidaqmx.Task('PMTtask')
            self.PMTtask.ai_channels.add_ai_voltage_chan(
                physical_channel='Dev1/ai{}'.format(PMTchan),
                name_to_assign_to_channel='chan_PMT')
            self.PMTtask.timing.cfg_samp_clk_timing(
                    rate=self.sampleRate,
                    sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                    samps_per_chan=len(self.totalrampx))

    def TriggerOpenPMT(self):
        if self.triggerPMT:
            print("Ya esta el trigger PMT")  # to dont open again
            p=0
        else:
            if self.triggerAPD:
                self.triggertask.stop()
                self.triggertask.close()
                self.triggerAPD = False

            self.triggertask = nidaqmx.Task('TriggerPMTtask')
        # Create the signal trigger
            triggerrate = self.sampleRate
            num = int(self.triggerEdit.text())
            trigger2 = [True, True, False]  # np.tile(trigger, self.numberofPixels)
            self.trigger = np.concatenate((np.zeros(num,dtype="bool"), trigger2))

            #print((num/triggerrate)*10**3, "delay (ms)")  # "\n", num, "num elegido",

        # Configure the digital channels to trigger the synchronization signal
            self.triggertask.do_channels.add_do_chan(
                lines="Dev1/port0/line6", name_to_assign_to_lines='chan6',
                line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)

            self.triggertask.timing.cfg_samp_clk_timing(
                         rate=triggerrate,  # muestras por segundo
                         sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
    #                         source='100kHzTimebase',
                         active_edge = nidaqmx.constants.Edge.RISING,
                         samps_per_chan=len(self.trigger))
        # Configure a start trigger to synchronizate the measure and movement
            triggerchannelname = "PFI4"
            self.aotask.triggers.start_trigger.cfg_dig_edge_start_trig(
                                trigger_source = triggerchannelname)#,
    #                                trigger_edge = nidaqmx.constants.Edge.RISING)
            self.PMTtask.triggers.start_trigger.cfg_dig_edge_start_trig(
                            trigger_source = triggerchannelname)#,
            self.triggerPMT = True

    def TriggerOpenAPD(self):
        if self.triggerAPD:
            print("Ya esta el trigger APD")  # to dont open again
            p=0
        else:
            if self.triggerPMT:
                self.triggertask.stop()
                self.triggertask.close()
                self.triggerPMT = False

            self.triggertask = nidaqmx.Task('TriggerAPDtask')
        # Create the signal trigger
            triggerrate = self.apdrate
            num = int((int(self.triggerEdit.text()) * self.Napd)*self.apdrate/10**3)

#            trigger = np.zeros((len(self.onerampx)*self.Napd),dtype="bool")

#            trigger[:] = True
#            trigger1 = np.concatenate((trigger, np.zeros(100,dtype="bool")))  # 2ms de apagado, hace cosas raras
            trigger2 = np.ones(self.totalcinumber-num,dtype='bool') # [True,False,True, True, False]  # np.tile(trigger, self.numberofPixels)

            self.trigger = np.concatenate((np.zeros(num,dtype="bool"), trigger2))

#            print((num/self.apdrate)*10**3, "delay (ms)")  # "\n", num, "num elegido",

        # Configure the digital channels to trigger the synchronization signal
            self.triggertask.do_channels.add_do_chan(
                lines="Dev1/port0/line6", name_to_assign_to_lines='chan6',
                line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)

            self.triggertask.timing.cfg_samp_clk_timing(
                         rate=triggerrate,  # muestras por segundo
                         sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
    #                         source='100kHzTimebase',
                         active_edge = nidaqmx.constants.Edge.RISING,
                         samps_per_chan=len(self.trigger))

        # Configure a start trigger to synchronizate the measure and movement
            triggerchannelname = "PFI4"
            self.aotask.triggers.start_trigger.cfg_dig_edge_start_trig(
                                trigger_source = triggerchannelname)#,
    #                                trigger_edge = nidaqmx.constants.Edge.RISING)

            self.APD1task.triggers.arm_start_trigger.dig_edge_src = triggerchannelname
            self.APD1task.triggers.arm_start_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_EDGE

            self.APD2task.triggers.arm_start_trigger.dig_edge_src = triggerchannelname
            self.APD2task.triggers.arm_start_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_EDGE

#            self.APD2task.triggers.sync_type.MASTER = True
#            self.APD1task.triggers.sync_type.SLAVE = True
            self.triggerAPD = True
#            self.citask.triggers.arm_start_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING

        # Pause trigger to get the signal on only when is a True in the referense
#            self.aotask.triggers.pause_trigger.dig_lvl_src = triggerchannelname
#            self.aotask.triggers.pause_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_LEVEL
#            self.aotask.triggers.pause_trigger.dig_lvl_when = nidaqmx.constants.Level.LOW
#
#            self.citask.triggers.pause_trigger.dig_lvl_src = triggerchannelname
#            self.citask.triggers.pause_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_LEVEL
#            self.citask.triggers.pause_trigger.dig_lvl_when = nidaqmx.constants.Level.LOW
        # En realidad mando un vector con muchos False's, asi que no lo estoy usando

# %%---- done
    def done(self):
        """ stop and close all the channels"""
#        if self.channelramp or self.channelsteps:
        try:
#            print("Cierro todos los canales")
            self.aotask.stop()  # Piezo
            self.aotask.close()
        except:
            #print("a")
            pass
        try:
            self.APD1task.stop()  # Apd
            self.APD1task.close()
        except:
            pass
            #print("b_0")
        try:
            self.APD2task.stop()  # Apd
            self.APD2task.close()
        except:
            pass
            #print("b_1")
        try:
            self.PMTtask.stop()  # PMT
            self.PMTtask.close()
        except:
            pass
            #print("c")
        try:
            self.triggertask.stop()  # trigger, antes dotask
            self.triggertask.close()
        except:
            pass
            #print("d")
        try:
            self.pointtask.stop()
            self.pointtask.close()
        except:
            pass
            #print("d")

#        self.shuttertask.stop()
#        self.shuttertask.close()
#        self.shuttering = False
        self.channelramp = False
        self.channelsteps = False
        self.piezoramp = False
        self.piezosteps = False
        self.PMTon = False
        self.APDson = False
        self.triggeron = False # separo los canales en partes
        self.triggerAPD = False
        self.triggerPMT = False
#        else:
#            print("llego hasta el done pero no tenia nada que cerrar")
#            # Esto no tendria que pasar

# %%--- Step Cosas --------------
    def stepLine(self):
#        tic = ptime.time()

        for i in range(self.numberofPixels):
#            tec = ptime.time()
#            self.citask.stop()
            self.aotask.stop()

            self.aotask.write(
             [self.allstepsx[i, self.dy] / convFactors['x'],
              self.allstepsy[i, self.dy] / convFactors['y']], auto_start=True)
#              self.allstepsz[i, self.dy] / convFactors['z']],
#                             auto_start=True)

#                self.aotask.start()
            self.aotask.wait_until_done()

#            tac = ptime.time()
            self.APDstep[:] = self.APD1task.read(1+self.Napd)
            self.APD1task.wait_until_done()
#            toc = ptime.time()

            self.APD1task.stop()
            self.aotask.stop()
#            self.cuentas[i] = aux + np.random.rand(1)[0]
            self.image[-1-i, self.numberofPixels-1-self.dy] = self.APDstep[-1] - self.APDstep[0]

# --stepScan ---
    def stepScan(self):
    # the step clock calls this function
        self.stepLine()

#        self.image[:, self.numberofPixels-1-(self.dy)] = self.cuentas
        self.img.setImage(self.image, autoLevels=self.autoLevels)


        if self.dy < self.numberofPixels-1:
            self.dy = self.dy + 1
        else:
            self.autoLevels = False
            if self.save:
                self.saveFrame()
                if self.CMcheck.isChecked():
                    self.CMmeasure()
                self.liveviewStop()
                self.mapa()
            else:
                if self.VideoCheck.isChecked():
                    self.saveFrame()  # para guardar siempre (Alan idea)
                print(ptime.time()-self.tic, "Tiempo imagen completa.")
                self.viewtimer.stop()
                if self.CMcheck.isChecked():
                    self.CMmeasure()
                if self.Continouscheck.isChecked():
                    self.liveviewStart()
                else:
                    self.MovetoStart()
                    self.done()


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
#        self.gox = gox


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

        if self.PSFMode.currentText() == 'XY normal psf':
            #print("escaneo x y normal S")
            p=0

        elif self.PSFMode.currentText() == 'XZ':
            #print("intercambio y por z S")
            self.allstepsz = self.allstepsy - startY + startZ  # -(sizeX/2)
            goy= np.ones(len(self.allstepsx)) * startY
            self.allstepsy = np.tile(goy,(self.numberofPixels,1))

        elif self.PSFMode.currentText() == 'YZ':
            #print("intercambio x por y S")
            self.allstepsz = self.allstepsy - startY + startZ  # -(sizeX/2)
            self.allstepsy = self.allstepsx - startX + startY
            gox= np.ones(len(self.allstepsy)) * startX
            self.allstepsx = np.tile(gox, (self.numberofPixels,1))

# %% ---Move----------------------------------------
    def move(self, axis, dist):
        """moves the position along the axis specified a distance dist."""
#        try
#            self.viewtimer.stop()

        self.PiezoOpenStep()  # cambiar a movimiento por puntos
#        t = self.moveTime
        N = int(abs(dist*200))  # self.moveSamples
        # read initial position for all channels
        texts = [getattr(self, ax + "Label").text()
                 for ax in activeChannels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]

    # Habia una version con rampas, y la borre. buscar en archivos viejos si se quiere
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
                               rampy[i] / convFactors['y']], auto_start=True)
#                               rampz[i] / convFactors['z']], auto_start=True)

        print("se mueve en", np.round(ptime.time() - toc, 4), "segs")

    # update position text
        self.xLabel.setText("{}".format(np.around(float(rampx[-1]), 2)))
        self.yLabel.setText("{}".format(np.around(float(rampy[-1]), 2)))
        self.zLabel.setText("{}".format(np.around(float(rampz[-1]), 2)))
        self.paramChanged()

        self.done()
#        self.channelsOpen()
#        if self.dy != 0:
#            if self.scanMode.currentText() == "step scan":
#                self.channelsOpenStep()
#            else:
##            if self.scanMode.currentText() == "ramp scan" or self.scanMode.currentText() == "otra frec ramp":
#                self.channelsOpenRamp()

    def xMoveUp(self):
        self.move('x', float(getattr(self, 'y' + "StepEdit").text()))

    def xMoveDown(self):
        self.move('x', -float(getattr(self, 'y' + "StepEdit").text()))

    def yMoveUp(self):
        self.move('y', float(getattr(self, 'y' + "StepEdit").text()))

    def yMoveDown(self):
        self.move('y', -float(getattr(self, 'y' + "StepEdit").text()))

    def zMoveUp(self):
        self.moveZ('z', float(getattr(self, 'z' + "StepEdit").text()))
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
            self.moveZ('z', -float(getattr(self, 'z' + "StepEdit").text()))
            self.zStepEdit.setStyleSheet("{ background-color: }")
        if self.initialPosition[2] == 0:  # para no ira z negativo
            self.zDownButton.setStyleSheet(
                "QPushButton { background-color: red; }"
                "QPushButton:pressed { background-color: blue; }")
            self.zDownButton.setEnabled(False)

    def moveZ(self, axis, dist):
        """moves the position along the Z axis a distance dist."""

        with nidaqmx.Task("Ztask") as Ztask:
#        self.Ztask = nidaqmx.Task('Ztask')
    # Following loop creates the voltage channels
            n=2
            Ztask.ao_channels.add_ao_voltage_chan(
                physical_channel='Dev1/ao{}'.format(n),
                name_to_assign_to_channel='chan_%s' % activeChannels[n],
                min_val=minVolt[activeChannels[n]],
                max_val=maxVolt[activeChannels[n]])

            N = abs(int(dist*2000))
        # read initial position for all channels
            toc = ptime.time()
            rampz = np.linspace(0, dist, N) + float(self.zLabel.text())
            for i in range(N):
                Ztask.write([rampz[i] / convFactors['z']], auto_start=True)
    
            print("se mueve en", np.round(ptime.time() - toc, 4), "segs")
        # update position text
            self.zLabel.setText("{}".format(np.around(float(rampz[-1]), 2)))

#        self.Ztask.stop()
#        self.Ztask.close()

        self.paramChanged()

# %% Go Cm y go to
    def goCM(self):
            self.zgotoLabel.setStyleSheet(" background-color: ")
            print("arranco en",float(self.xLabel.text()), float(self.yLabel.text()),
                  float(self.zLabel.text()))

            startX = float(self.xLabel.text())
            startY = float(self.yLabel.text())
            self.moveto((float(self.CMxValue.text()) + startX) - (self.scanRange/2),
                        (float(self.CMyValue.text()) + startY) - (self.scanRange/2),
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

#        self.paramChanged()

## ---moveto ---
    def moveto(self, x, y, z):
        """moves the position along the axis to a specified point."""
        self.PiezoOpenStep()  # se mueve de a puntos, no rampas.
        t = self.moveTime
        N = self.moveSamples

    # read initial position for all channels
        texts = [getattr(self, ax + "Label").text()
                 for ax in activeChannels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]

        if float(initPos[0]) != x or float(initPos[1]) != y or float(initPos[2]) != z:
            rampx = np.linspace(float(initPos[0]), x, N)
            rampy = np.linspace(float(initPos[1]), y, N)
            rampz = np.linspace(float(initPos[2]), z, N)

            tuc = ptime.time()
            for i in range(N):
                self.aotask.write([rampx[i] / convFactors['x'],
                                   rampy[i] / convFactors['y']], auto_start=True)
#                                   rampz[i] / convFactors['z']], auto_start=True)
#                time.sleep(t / N)

            print("se mueve todo en", np.round(ptime.time()-tuc, 4), "segs\n")

            self.xLabel.setText("{}".format(np.around(float(rampx[-1]), 2)))
            self.yLabel.setText("{}".format(np.around(float(rampy[-1]), 2)))
            self.zLabel.setText("{}".format(np.around(float(rampz[-1]), 2)))
            self.paramChanged()

            self.done()
#            self.channelsOpen()

        else:
            #print("¡YA ESTOY EN ESAS COORDENADAS!")
            p=0


# %% ---  Shutters zone ---------------------------------
    def shutter0(self):
        if self.shutter0button.isChecked():
            self.openShutter(shutters[0])
        else:
            self.closeShutter(shutters[0])
    def shutter1(self):
        if self.shutter1button.isChecked():
            self.openShutter(shutters[1])
        else:
            self.closeShutter(shutters[1])
    def shutter2(self):
        if self.shutter2button.isChecked():
            self.openShutter(shutters[2])
        else:
            self.closeShutter(shutters[2])

            
    def openShutter(self, p):
#        self.shuttersChannelsNidaq()
#        self.opendo()
        #print("abre shutter", p)
        for i in range(3):
            if p == shutters[i]:
                self.shuttersignal[i] = True
        self.shuttertask.write(self.shuttersignal, auto_start=True)
        #print(self.shuttersignal)
        self.checkShutters()

    def closeShutter(self, p):
#        self.shuttersChannelsNidaq()
#        self.closedo()
        #print("cierra shutter", p)
        for i in range(3):
            if p == shutters[i]:
                self.shuttersignal[i] = False
        self.shuttertask.write(self.shuttersignal, auto_start=True)
        #print(self.shuttersignal)
        self.checkShutters()

    def checkShutters(self):
        if self.shuttersignal[0]:
            self.shutter0button.setChecked(True)
        else:
            self.shutter0button.setChecked(False)
        if self.shuttersignal[1]:
            self.shutter1button.setChecked(True)
        else:
            self.shutter1button.setChecked(False)
        if self.shuttersignal[2]:
            self.shutter2button.setChecked(True)
        else:
            self.shutter2button.setChecked(False)

    def shuttersChannelsNidaq(self):
        if self.shuttering == False:
            self.shuttering = True
            self.shuttertask = nidaqmx.Task("shutter")
            self.shuttertask.do_channels.add_do_chan(
                lines="Dev1/port0/line0:2", name_to_assign_to_lines='shutters',
                line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
#        else:
#            #print("ya estaban abiertos los canales shutters")

# %%--- MovetoStart ---
    def MovetoStart(self):
        """ When called, it gets to the start point"""
        tic = ptime.time()
        if self.dy==0:
            print("is already in start")

        else:
            self.inStart = True
            #print("moving to start")
            self.done()

    #         Creates the voltage channels to move "slowly"
            with nidaqmx.Task("aotask") as aotask:
#            self.aotask = nidaqmx.Task('aotask')
                for n in range(len(AOchans)):
                    aotask.ao_channels.add_ao_voltage_chan(
                        physical_channel='Dev1/ao%s' % AOchans[n],
                        name_to_assign_to_channel='chan_%s' % activeChannels[n],
                        min_val=minVolt[activeChannels[n]],
                        max_val=maxVolt[activeChannels[n]])

                aotask.timing.cfg_samp_clk_timing(
                    rate=(self.moveRate),
                    sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                    samps_per_chan=self.moveSamples)

        #        tic = ptime.time()
                startX = float(self.initialPosition[0])
                startY = float(self.initialPosition[1])
#                startZ = float(self.initialPosition[2])
                if self.scanMode.currentText() == scanModes[1]:  # "step scan":
                    maximox = self.allstepsx[-1,self.dy]
                    maximoy = self.allstepsy[-1,self.dy]
#                    maximoz = self.allstepsz[-1,self.dy]
                else:
    #            if self.scanMode.currentText() == "ramp scan" or self.scanMode.currentText() == "otra frec ramp":
                    stops = ((len(self.onerampx))-1) * self.dy
                    maximox = self.totalrampx[stops]
                    maximoy = self.totalrampy[stops]
#                    maximoz = self.totalrampz[stops]

                volviendox = np.linspace(maximox, startX, self.moveSamples)
                volviendoy = np.linspace(maximoy, startY, self.moveSamples)
#                volviendoz = np.linspace(maximoz, startZ, self.moveSamples)

                aotask.write(np.array(
                    [volviendox / convFactors['x'],
                     volviendoy / convFactors['y']]), auto_start=True)
    #                 volviendoz / convFactors['z']]), auto_start=True)
#                aotask.wait_until_done()
        #        print(np.round(ptime.time() - tic, 5)*10**3, "MovetoStart (ms)")

#            self.aotask.stop()
#            self.aotask.close()

        self.dy = 0
        toc = ptime.time()
        print("\n tiempo movetoStart (ms)", (toc-tic)*10**3,"\n")

# %%--- ploting in live
    def plotLive(self):
        tic = ptime.time()
        texts = [getattr(self, ax + "Label").text() for ax in activeChannels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]
        x = np.linspace(0, self.scanRange, self.numberofPixels) + float(initPos[0])
        y = np.linspace(0, self.scanRange, self.numberofPixels) + float(initPos[1])
        X, Y = np.meshgrid(x, y)
        fig, ax = plt.subplots()
        p = ax.pcolor(X, Y, np.transpose(self.image), cmap=plt.cm.jet)
        cb = fig.colorbar(p)
        ax.set_xlabel('x [um]')
        ax.set_ylabel('y [um]')
        try:
            xc = int(np.floor(self.xcm))
            yc = int(np.floor(self.ycm))
            X2=np.transpose(X)
            Y2=np.transpose(Y)
            resol = 2
            for i in range(resol):
                for j in range(resol):
                    ax.text(X2[xc+i,yc+j],Y2[xc+i,yc+j],"☺",color='m')
            Normal = self.scanRange / self.numberofPixels  # Normalizo
            ax.set_title((self.xcm*Normal+float(initPos[0]),
                                         self.ycm*Normal+float(initPos[1])))
        except:
            pass
        plt.show()
        toc = ptime.time()
        print("\n tiempo Plotlive", toc-tic,"\n")

# %%--- SaveFrame ---
    def saveFrame(self):
        """ Config the path and name of the file to save, and save it"""
        if self.PSFMode.currentText() == 'XY normal psf':
            psfmode = "XY"
        elif self.PSFMode.currentText() == 'XZ':
            psfmode = "XZ"
        elif self.PSFMode.currentText() == 'YZ':
            psfmode = "YZ"
#        filepath = self.main.file_path
        timestr = time.strftime("%Y%m%d-%H%M%S")

        if self.detectMode .currentText() == detectModes[-2]:
            name = str(self.file_path + "/" + detectModes[0] + "-" + psfmode + "-" + timestr + ".tiff")  # nombre con la fecha -hora
            guardado = Image.fromarray(np.transpose((self.image)))  # f
            guardado.save(name)
            name = str(self.file_path + "/" + detectModes[1] + "-" + psfmode + "-" + timestr + ".tiff")  # nombre con la fecha -hora
            guardado = Image.fromarray(np.transpose(self.image2))  # np.flip(,1)
            guardado.save(name)

        else:
            name = str(self.file_path + "/" + self.detectMode .currentText() + "-" + psfmode + "-" + timestr + ".tiff")  # nombre con la fecha -hora
            guardado = Image.fromarray(np.transpose(self.image))  # f
            guardado.save(name)

        print("\n Image saved\n")

    def selectFolder(self):

        root = tk.Tk()
        root.withdraw()
        self.file_path = filedialog.askdirectory()
        #print(self.file_path,2)
        self.NameDirValue.setText(self.file_path)
        self.NameDirValue.setStyleSheet(" background-color: ")

    def openFolder(self):
        os.startfile(self.file_path)

# %% GaussMeasure 
    def GaussMeasure(self):
        tic = ptime.time()
        self.data = self.image
        params = fitgaussian(self.data)
        self.fit = gaussian(*params)
        self.params = params
        (height, x, y, width_x, width_y) = params

#        texts = [getattr(self, ax + "Label").text() for ax in self.activeChannels]
#        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]
#        xv = np.linspace(0, self.scanRange, self.numberofPixels) + float(initPos[0])
#        yv = np.linspace(0, self.scanRange, self.numberofPixels) + float(initPos[1])

        Normal = self.scanRange / self.numberofPixels  # Normalizo
        xx = x*Normal
        yy = y*Normal
        self.GaussxValue.setText(str(xx))
        self.GaussyValue.setText(str(yy))
        tac = ptime.time()
        print(np.round((tac-tic)*10**3,3), "(ms)Gauss fit\n")

# %% CMmeasure
    def CMmeasure(self):

        tic = ptime.time()

        Z = self.image

        xcm, ycm = ndimage.measurements.center_of_mass(Z)  # Los calculo y da lo mismo
        self.xcm = xcm
        self.ycm = ycm
#        xc = int(np.round(xcm,2))
#        yc = int(np.round(ycm,2))
        Normal = self.scanRange / self.numberofPixels
        self.CMxValue.setText(str(xcm*Normal))
        self.CMyValue.setText(str(ycm*Normal))
        tac = ptime.time()

        print(np.round((tac-tic)*10**3,3), "(ms) CM\n")

# %% arma los datos para modular.(mapa)

    def mapa(self):
        Z = self.image
        N = len(Z)
        lomas = np.max(Z)
        Npasos = 4
        paso = lomas/Npasos
        tec=ptime.time()
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
        print(np.round((ptime.time()-tec)*10**3, 4),"ms tarda mapa\n")
        self.img.setImage((np.array(mapa)), autoLevels=True)
#        self.img.setImage((np.flip(mapa,0)), autoLevels=False)

# %% Point scan ---+--- Hay que elegir APD
    def PointStart(self):
        if self.PointButton.isChecked():
            self.PointScan()
            print("midiendo")
        else:
            self.PointScanStop()
            print("fin")

    def PointScanStop(self):
        self.pointtimer.stop()
        self.pointtask.stop()
        self.pointtask.close()

    def PointScan(self):
        if self.detectMode .currentText() == detectModes[0]:
#        if self.APDred.isChecked():
            c = COchans[0]
        elif self.detectMode .currentText() == detectModes[1]:
#        elif self.APDgreen.isChecked():
            c = COchans[1]
        else:
            print("seleccionar algun apd")
        print(c)
        tiempo = 400 # ms  # refresca el numero cada este tiempo
        self.points = np.zeros(int((self.apdrate*(tiempo /10**3))))
        self.pointtask = nidaqmx.Task('pointtask')

        # Configure the counter channel to read the APD
        self.pointtask.ci_channels.add_ci_count_edges_chan(
                            counter='Dev1/ctr{}'.format(COchans[c]),
                            name_to_assign_to_channel=u'Line_counter',
                            initial_count=0)

        self.pointtimer = QtCore.QTimer()
        self.pointtimer.timeout.connect(self.updatePoint)
        self.pointtimer.start(tiempo)

    def updatePoint(self):
        N = len(self.points)
        self.points[:] = self.pointtask.read(N)
        m = np.mean(self.points)
#        #print("valor traza", m)
        self.PointLabel.setText("<strong>{0:.2e}".format(float(m)))

# %%  ROI cosas
    def ROImethod(self):
        self.NofPixels = self.numberofPixels
        if self.roi is None:

            ROIpos = (0.5 * self.NofPixels - 64, 0.5 * self.NofPixels - 64)
            self.roi = viewbox_tools.ROI(self.NofPixels, self.vb, ROIpos,
                                         handlePos=(1, 0),
                                         handleCenter=(0, 1),
                                         scaleSnap=True,
                                         translateSnap=True)

        else:
            self.vb.removeItem(self.roi)
            self.roi.hide()
            if self.ROIButton.isChecked():
                ROIpos = (0.5 * self.NofPixels - 64, 0.5 * self.NofPixels - 64)
                self.roi = viewbox_tools.ROI(self.NofPixels, self.vb, ROIpos,
                                             handlePos=(1, 0),
                                             handleCenter=(0, 1),
                                             scaleSnap=True,
                                             translateSnap=True)

    def selectROI(self):
        self.liveviewStop()
        self.NofPixels = self.numberofPixels
        self.pxSize = self.pixelSize

        array = self.roi.getArrayRegion(self.image, self.img)
        ROIpos = np.array(self.roi.pos())

        newPos_px = tools.ROIscanRelativePOS(ROIpos,
                                             self.NofPixels,
                                             np.shape(array)[1])
        #print(self.initialPosition)
        newPos_µm = newPos_px * self.pxSize + self.initialPosition[0:2]

        newPos_µm = np.around(newPos_µm, 2)

#        self.initialPosEdit.setText('{} {} {}'.format(newPos_µm[0],
#                                                      newPos_µm[1],
#                                                      self.initialPos[2]))

        print("estaba en", float(self.xLabel.text()),
              float(self.yLabel.text()), float(self.zLabel.text()))

        self.moveto(float(newPos_µm[0]),
                    float(newPos_µm[1]),
                    float(self.initialPosition[2]))

        print("ROI fue a", float(self.xLabel.text()),
              float(self.yLabel.text()), float(self.zLabel.text()), "/n")

#        self.xLabel.setText("{}".format((float(newPos_µm[0]))))
#        self.yLabel.setText("{}".format((float(newPos_µm[1]))))
#        self.zLabel.setText("{}".format((float(self.initialPosition[2]))))


        newRange_px = np.shape(array)[0]
        newRange_µm = self.pxSize * newRange_px
        newRange_µm = np.around(newRange_µm, 2)

        print("cambió el rango, de", self.scanRange)
        self.scanRangeEdit.setText('{}'.format(newRange_µm))
        print("hasta :", self.scanRange, "\n")
        self.paramChanged()

# %% Presets copiados del inspector
    def Presets(self):
        """ Elige convinaciones de parametros como los que usa el inspectora
        para algunos de sus barridos"""
        if self.presetsMode .currentText() == self.presetsModes[0]:
            self.scanRangeEdit.setText('10')
            self.pixelTimeEdit.setText('0.01')
            self.numberofPixelsEdit.setText('500')
            self.accelerationEdit.setText('120')
            self.vueltaEdit.setText('15')


        elif self.presetsMode .currentText() == self.presetsModes[1]:
            self.scanRangeEdit.setText('10')
            self.pixelTimeEdit.setText('0.2')
            self.numberofPixelsEdit.setText('128')
            self.accelerationEdit.setText('0.1')
            self.vueltaEdit.setText('1')

        elif self.presetsMode .currentText() == self.presetsModes[2]:
            self.scanRangeEdit.setText('5')
            self.pixelTimeEdit.setText('0.05')
            self.numberofPixelsEdit.setText('250')
            self.accelerationEdit.setText('12')
            self.vueltaEdit.setText('10')

        elif self.presetsMode .currentText() == self.presetsModes[3]:
            self.scanRangeEdit.setText('0.6')
            self.pixelTimeEdit.setText('0.2')
            self.numberofPixelsEdit.setText('30')
            self.accelerationEdit.setText('120')
            self.vueltaEdit.setText('100')

        elif self.presetsMode .currentText() == self.presetsModes[4]:
            self.scanRangeEdit.setText('3')
            self.pixelTimeEdit.setText('0.1')
            self.numberofPixelsEdit.setText('300')
            self.accelerationEdit.setText('120')
            self.vueltaEdit.setText('100')

#        self.paramChanged()
#        self.preseteado = True    creo que no lo voy a usar

# %% getInitPos  Posiciones reales, si agrego los cables que faltan
    def getInitPos(self):
        tic = ptime.time()
#        aitask = nidaqmx.Task("aitask")
#        aitask.ai_channels.add_ai_voltage_chan("Dev1/ai7:6")  # por comodidad de cables esta decreciente
#        aitask.wait_until_done()
#
#        data = aitask.read(number_of_samples_per_channel=5)
#        print("Lecturas de las ai 7y6", data[0][-1],data[1][-1])
#        aitask.stop()
#        aitask.close()

        with nidaqmx.Task("ai7") as task:
            task.ai_channels.add_ai_voltage_chan("Dev1/ai7:6")
            task.wait_until_done()
            data = task.read(number_of_samples_per_channel=5)
        print("Lecturas de las ai 7y6", data[0][-1],data[1][-1])
        self.realposX = data[0][-1] * convFactors['x']
        self.realposY = data[1][-1] * convFactors['y']
        print("Posiciones Actuales", self.realposX, self.realposY)
        valorX = find_nearest(self.totalrampx, self.realposX)
        valorY = find_nearest(self.totalrampy, self.realposY)
        self.indiceX = np.where(self.totalrampx == valorX)
        self.indiceY = np.where(self.totalrampy == valorY)
        print("En la rampa X:",self.totalrampx[self.indiceX][0])
        print("En la rampa Y:",self.totalrampy[self.indiceY][0])
#def find_nearest(array,value):

#    # update position text
#        self.xLabel.setText("{}".format(np.around(float(data[-1,0]), 2)))  # X
#        self.yLabel.setText("{}".format(np.around(float(data[-1,1]), 2)))  # Y
##        self.zLabel.setText("{}".format(np.around(float(data[-1,2]), 2)))  # Z
#        self.initialPosition = (float(self.xLabel.text()),
#                                float(self.yLabel.text()))#,
##                                float(self.zLabel.text()))
#        self.paramChanged()
        toc = ptime.time()
        print("\n tiempo getInitPos", toc-tic,"\n")
# %% Otras Funciones
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
    from scipy import optimize
    """Returns (height, x, y, width_x, width_y)
    the gaussian parameters of a 2D distribution found by a fit"""
    params = moments(data)
    errorfunction = lambda p: np.ravel(gaussian(*p)(*np.indices(data.shape)) -
                                 data)
    p, success = optimize.leastsq(errorfunction, params)
    return p

def find_nearest(array,value):
    idx = (np.abs(array-value)).argmin()
    return array[idx]
# %% FIN
app = QtGui.QApplication([])
win = ScanWidget(device)
#win = MainWindow()
win.show()

app.exec_()
