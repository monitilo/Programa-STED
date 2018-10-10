# %%
""" Programa inicial donde miraba como anda el liveScan
 sin usar la pc del STED. incluye positioner"""

#import subprocess
import sys
import os

import numpy as np
import time
#import scipy.ndimage as ndi
import matplotlib.pyplot as plt

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

#from pyqtgraph.dockarea import Dock, DockArea
import pyqtgraph.ptime as ptime
#
from PIL import Image

import re

import tkinter as tk
from tkinter import filedialog



from scipy import ndimage
from scipy import optimize

device = 9
convFactors = {'x': 25, 'y': 25, 'z': 1.683}  # la calibracion es 1 µm = 40 mV;
# la de z es 1 um = 0.59 V
apdrate = 10**5

def makeRamp(start, end, samples):
    return np.linspace(start, end, num=samples)


#import sys
#from PyQt5 import QtCore, QtWidgets
#from PyQt5.QtWidgets import QMainWindow, QWidget, QPushButton, QAction
#from PyQt5.QtCore import QSize
#from PyQt5.QtGui import QIcon

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
    """Returns (height, x, y, width_x, width_y)
    the gaussian parameters of a 2D distribution found by a fit"""
    params = moments(data)
    errorfunction = lambda p: np.ravel(gaussian(*p)(*np.indices(data.shape)) -
                                 data)
    p, success = optimize.leastsq(errorfunction, params)
    return p

# %% Main Window
class MainWindow(QtWidgets.QMainWindow):
    def newCall(self):
        self.a = 0
        print('New')

    def openCall(self):
        self.a = 1.5
        os.startfile(self.file_path)
        print('Open')

    def exitCall(self):
        self.a = -1.5
        print('Exit app (no hace nada)')

    def greenAPD(self):
        print('Green APD')

    def redAPD(self):
        print('red APD')

    def localDir(self):
        print('poner la carpeta donde trabajar')
        root = tk.Tk()
        root.withdraw()
        
        self.file_path = filedialog.askdirectory()
        print(self.file_path,"◄ dire")
        self.form_widget.NameDirValue.setText(self.file_path)
        self.form_widget.NameDirValue.setStyleSheet(" background-color: ")
#        self.form_widget.paramChanged()


    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.a = 0
        self.file_path = os.path.abspath("")
# ----- MENU
        self.setMinimumSize(QtCore.QSize(300, 100))
        self.setWindowTitle("AAAAAAAAAAABBBBBBBBBBBBB")

        # Create new action
#        newAction = QtWidgets.QAction(QtGui.QIcon('new.png'), '&New', self)
#        newAction.setShortcut('Ctrl+N')
#        newAction.setStatusTip('New document')
#        newAction.triggered.connect(self.newCall)

        # Create new action
        openAction = QtWidgets.QAction(QtGui.QIcon('open.png'), '&Open Dir', self)
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip('Open document')
        openAction.triggered.connect(self.openCall)

        # Create exit action
        exitAction = QtWidgets.QAction(QtGui.QIcon('exit.png'), '&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.exitCall)

        # Create de APD options Action
        greenAPDaction = QtWidgets.QAction(QtGui.QIcon('greenAPD.png'), '&Green', self) 
        greenAPDaction.setStatusTip('Uses the APD for canal green')
        greenAPDaction.triggered.connect(self.greenAPD)
        greenAPDaction.setShortcut('Ctrl+G')
        redAPDaction = QtWidgets.QAction(QtGui.QIcon('redAPD.png'), '&Red', self) 
        redAPDaction.setStatusTip('Uses the APD for canal red')
        redAPDaction.setShortcut('Ctrl+R')
        redAPDaction.triggered.connect(self.redAPD)

        # Create de file location action
        localDirAction = QtWidgets.QAction(QtGui.QIcon('Dir.png'), '&Select Dir', self) 
        localDirAction.setStatusTip('Select the work folder')
        localDirAction.setShortcut('Ctrl+D')
        localDirAction.triggered.connect(self.localDir)

        # Create menu bar and add action
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')
        fileMenu.addAction(localDirAction)
        fileMenu.addAction(openAction)
        fileMenu.addAction(exitAction)
        fileMenu2 = menuBar.addMenu('&APD')
        fileMenu2.addAction(greenAPDaction)
        fileMenu2.addAction(redAPDaction)
#        fileMenu3 = menuBar.addMenu('&Local Folder')
#        fileMenu3.addAction(localDiraction)
        fileMenu4 = menuBar.addMenu('&<--Selecciono la carpeta desde aca!')

        self.form_widget = ScanWidget(self, device)
        self.setCentralWidget(self.form_widget)
# %% Scan Widget
class ScanWidget(QtGui.QFrame):

    def keyPressEvent(self, e):

        if e.key() == QtCore.Qt.Key_Escape:
            print("tocaste Escape")
            self.close()
            self.liveviewStop()


        if e.key() == QtCore.Qt.Key_Enter:
            print("tocaste Enter")
            self.liveviewButton.setChecked()
            self.liveview()

    def __init__(self, main, device, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.main=main
        self.algo = device
# ---  Positioner metido adentro

        # Parameters for smooth moving (to no shake hard the piezo)
        self.moveTime = 0.1  # total time to move(s)
#        self.sampleRate = 10**3  # 10**5
        self.moveSamples = 100  # samples to move

        # Parameters for the ramp (driving signal for the different channels)
        self.rampTime = 0.1  # Time for each ramp in s
        self.sampleRate = 10**3  # 10**5
        self.nSamples = int(self.rampTime * self.sampleRate)

        # This boolean is set to False when tempesta is scanning to prevent
        # this positionner to access the analog output channels
#        self.isActive = True
        self.activeChannels = ["x", "y", "z"]
        self.AOchans = [0, 1, 2]     # Order corresponds to self.channelOrder

        # Axes control
        self.xLabel = QtGui.QLabel('1.0')
#            "<strong>x = {0:.2f} µm</strong>".format(self.x))
        self.xLabel.setTextFormat(QtCore.Qt.RichText)
        self.xname =  QtGui.QLabel("<strong>x =")
        self.xname.setTextFormat(QtCore.Qt.RichText)
        self.xUpButton = QtGui.QPushButton("(+x) ►")  # →
        self.xUpButton.pressed.connect(self.xMoveUp)
        self.xDownButton = QtGui.QPushButton("◄ (-x)")  # ←
        self.xDownButton.pressed.connect(self.xMoveDown)
        self.xStepEdit = QtGui.QLineEdit("1")  # estaban en 0.05<
        self.xStepUnit = QtGui.QLabel(" µm")

        self.yLabel = QtGui.QLabel('2.0')
#            "<strong>y = {0:.2f} µm</strong>".format(self.y))
        self.yLabel.setTextFormat(QtCore.Qt.RichText)
        self.yname =  QtGui.QLabel("<strong>y =")
        self.yname.setTextFormat(QtCore.Qt.RichText)
        self.yUpButton = QtGui.QPushButton("(+y) ▲")  # ↑
        self.yUpButton.pressed.connect(self.yMoveUp)
        self.yDownButton = QtGui.QPushButton("(-y) ▼")  # ↓
        self.yDownButton.pressed.connect(self.yMoveDown)
        self.yStepEdit = QtGui.QLineEdit("1")
        self.yStepUnit = QtGui.QLabel(" µm")

        self.zLabel = QtGui.QLabel('3.0')
#            "<strong>z = {0:.2f} µm</strong>".format(self.z))
        self.zLabel.setTextFormat(QtCore.Qt.RichText)
        self.zname =  QtGui.QLabel("<strong>z =")
        self.zname.setTextFormat(QtCore.Qt.RichText)
        self.zUpButton = QtGui.QPushButton("+z ▲")
        self.zUpButton.pressed.connect(self.zMoveUp)
        self.zDownButton = QtGui.QPushButton("-z ▼")
        self.zDownButton.pressed.connect(self.zMoveDown)
        self.zStepEdit = QtGui.QLineEdit("1")
        self.zStepUnit = QtGui.QLabel(" µm")

# ---- fin 1ra parte del positioner ----------
        self.step = 1
        imageWidget = pg.GraphicsLayoutWidget()
        self.vb = imageWidget.addViewBox(row=1, col=1)

        # LiveView Button

        self.liveviewButton = QtGui.QPushButton('confocal LIVEVIEW')
        self.liveviewButton.setCheckable(True)
        self.liveviewButton.clicked.connect(self.liveview)
        self.liveviewButton.setStyleSheet(
                "QPushButton { background-color: green; }"
                "QPushButton:pressed { background-color: blue; }")
        self.liveviewButton.setToolTip('This is a tooltip message.')

        # save image Button

        self.saveimageButton = QtGui.QPushButton('Scan and Save')
        self.saveimageButton.setCheckable(True)
        self.saveimageButton.clicked.connect(self.saveimage)
        self.saveimageButton.setStyleSheet(
                "QPushButton { background-color: gray; }"
                "QPushButton:pressed { background-color: blue; }")

#        self.NameDirButton = QtGui.QPushButton('Open')
#        self.NameDirButton.clicked.connect(self.openFolder)
        self.file_path = main.file_path

        # Defino el tipo de Scan que quiero

        self.scanMode = QtGui.QComboBox()
        self.scanModes = ['step scan', 'ramp scan', 'otro scan']
        self.scanMode.addItems(self.scanModes)
#        self.scanMode.currentIndexChanged.connect(self.paramChanged)

    # Presets simil inspector
        self.presetsMode = QtGui.QComboBox()
        self.presetsModes = ['Manual', '500x0.01', '128x0.1']
        self.presetsMode.addItems(self.presetsModes)
        self.presetsMode.activated.connect(self.Presets)

    # to run continuously
        self.Continouscheck = QtGui.QCheckBox('Continous')
        self.Continouscheck.setChecked(False)

        # no lo quiero cuadrado

#        self.squareRadio = QtGui.QRadioButton('Cuadrado')
#        self.squareRadio.clicked.connect(self.squareOrNot)
#        self.squareRadio.setChecked(True)

    # XZ PSF scan
        self.XYcheck = QtGui.QRadioButton('XZ psf scan')
        self.XYcheck.setChecked(True)

        self.XZcheck = QtGui.QRadioButton('XZ psf scan')
        self.XZcheck.setChecked(False)

        self.YZcheck = QtGui.QRadioButton('YZ psf scan')
        self.YZcheck.setChecked(False)

    # para que guarde todo (trazas de Alan)
        self.Alancheck = QtGui.QCheckBox('Alan continous save')
        self.Alancheck.setChecked(False)

    # Calcula el centro de la particula
        self.CMcheck = QtGui.QCheckBox('calcula CM')
        self.CMcheck.setChecked(False)
        self.CMcheck.clicked.connect(self.CMmeasure)

        self.Gausscheck = QtGui.QCheckBox('calcula centro gaussiano')
        self.Gausscheck.setChecked(False)
        self.Gausscheck.clicked.connect(self.GaussMeasure)
    # Para alternar entre pasos de a 1 y de a 2 (en el programa final se va)

        self.stepcheck = QtGui.QCheckBox('hacerlo de a 2')
        self.stepcheck.clicked.connect(self.steptype)
        # botones para shutters (por ahora no hacen nada)
        self.shuttersignal = [0, 0, 0]
        self.shutterredbutton = QtGui.QCheckBox('shutter 640')
#        self.shutterredbutton.setChecked(False)
        self.shutterredbutton.clicked.connect(self.shutterred)
        self.shuttergreenbutton = QtGui.QCheckBox('shutter 532')
#        self.shuttergreenbutton.setChecked(False)
        self.shuttergreenbutton.clicked.connect(self.shuttergreen)
        self.shutterotrobutton = QtGui.QCheckBox('shutter otro')
#        self.shutterotrobutton.setChecked(False)
        self.shutterotrobutton.clicked.connect(self.shutterotro)


#       This boolean is set to True when open the nidaq channels
        self.ischannelopen = False

        # Scanning parameters

#        self.initialPositionLabel = QtGui.QLabel('Initial Pos [x0 y0] (µm)')
#        self.initialPositionEdit = QtGui.QLineEdit('1 2 3')  # no lo uso mas
        self.scanRangeLabel = QtGui.QLabel('Scan range x (µm)')
        self.scanRangeEdit = QtGui.QLineEdit('4')
#        self.scanRangeyLabel = QtGui.QLabel('Scan range y (µm)')
#        self.scanRangeyEdit = QtGui.QLineEdit('10')
        pixelTimeLabel = QtGui.QLabel('Pixel time (ms)')
        self.pixelTimeEdit = QtGui.QLineEdit('0.5')
        numberofPixelsLabel = QtGui.QLabel('Number of pixels')
        self.numberofPixelsEdit = QtGui.QLineEdit('100')
        self.pixelSizeLabel = QtGui.QLabel('Pixel size (nm)')
        self.pixelSizeValue = QtGui.QLabel('')
        self.timeTotalLabel = QtGui.QLabel('tiempo total del escaneo (s)')
#        self.timeTotalValue = QtGui.QLabel('')

        self.onlyInt = QtGui.QIntValidator(0,5000)
        self.numberofPixelsEdit.setValidator(self.onlyInt)
        self.onlypos = QtGui.QDoubleValidator(0, 1000,10)
        self.pixelTimeEdit.setValidator(self.onlypos)
        self.scanRangeEdit.setValidator(self.onlypos)



#        label_save = QtGui.QLabel('Nombre del archivo (archivo.tiff)')
#        label_save.resize(label_save.sizeHint())
#        self.edit_save = QtGui.QLineEdit('imagenScan.tiff')
#        self.edit_save.resize(self.edit_save.sizeHint())

#        self.numberofPixelsEdit.textChanged.connect(self.paramChanged)
##        self.scanRangexEdit.textChanged.connect(self.squarex)
##        self.scanRangeyEdit.textChanged.connect(self.squarey)
#        self.scanRangeEdit.textChanged.connect(self.paramChanged)
##        self.scanRangeyEdit.textChanged.connect(self.paramChanged)
#        self.pixelTimeEdit.textChanged.connect(self.paramChanged)
##        self.initialPositionEdit.textChanged.connect(self.paramChanged)

#        initialPosition = np.array(
#                self.initialPositionEdit.text().split(' '))

#        self.xLabel.setText("{}".format(
#                np.around(float(initialPosition[0]), 2)))
#        self.yLabel.setText("{}".format(
#                np.around(float(initialPosition[1]), 2)))
#        self.zLabel.setText("{}".format(
#                np.around(float(initialPosition[2]), 2)))
        self.NameDirValue = QtGui.QLabel('')
        self.NameDirValue.setText(self.file_path)
        self.NameDirValue.setStyleSheet(" background-color: red; ")

        self.CMxLabel = QtGui.QLabel('CM X')
        self.CMxValue = QtGui.QLabel('NaN')
        self.CMyLabel = QtGui.QLabel('CM Y')
        self.CMyValue = QtGui.QLabel('NaN')
        self.a = QtGui.QLineEdit('-1.5')
        self.b = QtGui.QLineEdit('-1.5')
#        self.a.textChanged.connect(self.paramChanged)
#        self.b.textChanged.connect(self.paramChanged)

        self.GaussxLabel = QtGui.QLabel('Gauss fit X')
        self.GaussxValue = QtGui.QLabel('NaN G')
        self.GaussyLabel = QtGui.QLabel('Gauss fit Y')
        self.GaussyValue = QtGui.QLabel('NaN G')


        self.plotLivebutton = QtGui.QPushButton('Plot this image')
        self.plotLivebutton.setChecked(False)
        self.plotLivebutton.clicked.connect(self.plotLive)
#        self.plotLivebutton.clicked.connect(self.otroPlot)


        self.paramChanged()

        self.paramWidget = QtGui.QWidget()

        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        grid.addWidget(imageWidget, 2, 0)
        grid.addWidget(self.paramWidget, 2, 1)



        subgrid = QtGui.QGridLayout()
        self.paramWidget.setLayout(subgrid)
#        subgrid.addWidget(self.initialPositionLabel, 0, 1)
#        subgrid.addWidget(self.initialPositionEdit, 1, 1)
        subgrid.addWidget(self.shutterredbutton, 1, 1)
        subgrid.addWidget(self.shuttergreenbutton, 2, 1)
        subgrid.addWidget(self.shutterotrobutton, 3, 1)
        subgrid.addWidget(self.scanRangeLabel, 4, 1)
        subgrid.addWidget(self.scanRangeEdit, 5, 1)
#        subgrid.addWidget(self.scanRangeyLabel, 3, 2)
#        subgrid.addWidget(self.scanRangeyEdit, 4, 2)
        subgrid.addWidget(pixelTimeLabel, 6, 1)
        subgrid.addWidget(self.pixelTimeEdit, 7, 1)
        subgrid.addWidget(numberofPixelsLabel, 8, 1)
        subgrid.addWidget(self.numberofPixelsEdit, 9, 1)
        subgrid.addWidget(self.pixelSizeLabel, 10, 1)
        subgrid.addWidget(self.pixelSizeValue, 11, 1)
        subgrid.addWidget(self.scanMode, 13, 1)

        subgrid.addWidget(self.liveviewButton, 14, 1, 2, 1)
        subgrid.addWidget(self.Alancheck, 16, 1)
        subgrid.addWidget(self.timeTotalLabel, 17, 1)
#        subgrid.addWidget(self.timeTotalValue, 15, 1)
        subgrid.addWidget(self.saveimageButton, 18, 1)

#        subgrid.addWidget(self.NameDirButton, 18, 2,2,1)

        subgrid.addWidget(self.stepcheck, 12, 1)
#        subgrid.addWidget(self.squareRadio, 12, 2)
        subgrid.addWidget(self.presetsMode, 15, 3)

        subgrid.addWidget(self.Continouscheck,  11, 2)

        group1 = QtGui.QButtonGroup(self.paramWidget)
        group1.addButton(self.XYcheck)
        group1.addButton(self.XZcheck)
        group1.addButton(self.YZcheck)
#        subgrid.addWidget(self.XYcheck)
#        subgrid.addWidget(self.XZcheck)
#        subgrid.addWidget(self.YZcheck)
        subgrid.addWidget(self.XYcheck, 15, 2)
        subgrid.addWidget(self.XZcheck, 16, 2)
        subgrid.addWidget(self.YZcheck, 17, 2)
#        subgrid.addWidget(label_save, 16, 0, 1, 2)
#        subgrid.addWidget(self.edit_save, 17, 0, 1, 2)

        self.aLabel = QtGui.QLabel('a')
        self.bLabel = QtGui.QLabel('b')
        subgrid.addWidget(self.aLabel, 1, 2)
        subgrid.addWidget(self.a, 2, 2)
        subgrid.addWidget(self.bLabel, 3, 2)
        subgrid.addWidget(self.b, 4, 2)

#        self.detectMode = QtGui.QComboBox()
#        self.detectModes = ['APD red', 'APD green', 'PMT']
#        self.detectMode.addItems(self.detectModes)
#        self.detectMode.activated.connect(self.paramChanged)
#        self.detectMode.currentIndexChanged.connect(self.paramChanged)

        group2 = QtGui.QButtonGroup(self.paramWidget)
        self.APDred=QtGui.QRadioButton("APD red")
        self.APDgreen=QtGui.QRadioButton("APD green")
        self.APDred.setChecked(True)
        self.APDgreen.setChecked(False)
        group2.addButton(self.APDred)
        group2.addButton(self.APDgreen)
#        subgrid.addWidget(self.detectMode, 0, 1)
        subgrid.addWidget(self.APDred, 0, 1)
        subgrid.addWidget(self.APDgreen, 0, 2)
        subgrid.addWidget(self.plotLivebutton, 6, 2)

        subgrid.addWidget(self.CMcheck, 8, 2)
        subgrid.addWidget(self.Gausscheck, 8, 3)

# --- POSITIONERRRRR-------------------------------

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
        self.gotoButton = QtGui.QPushButton("♥ G0 To ♦")
        self.gotoButton.pressed.connect(self.goto)
        layout2.addWidget(self.gotoButton, 1, 9, 2, 2)
        layout2.addWidget(self.xgotoLabel, 1, 8)
        layout2.addWidget(self.ygotoLabel, 2, 8)
        layout2.addWidget(self.zgotoLabel, 3, 8)

        layout2.addWidget(self.CMxLabel, 4, 8)
        layout2.addWidget(self.CMxValue, 5, 8)
        layout2.addWidget(self.CMyLabel, 4, 9)
        layout2.addWidget(self.CMyValue, 5, 9)
        self.goCMButton = QtGui.QPushButton("♠ Go CM ♣")
        self.goCMButton.pressed.connect(self.goCM)
        layout2.addWidget(self.goCMButton, 2, 9, 2, 2)

        self.xgotoLabel.setValidator(self.onlypos)
        self.ygotoLabel.setValidator(self.onlypos)
        self.zgotoLabel.setValidator(self.onlypos)


        layout2.addWidget(self.GaussxLabel, 4, 10)
        layout2.addWidget(self.GaussxValue, 5, 10)
        layout2.addWidget(self.GaussyLabel, 4, 11)
        layout2.addWidget(self.GaussyValue, 5, 11)


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

        # no se como hacerla andar con docks
#        dockArea = DockArea()
#        scanDock = Dock('Scan', size=(1, 1))
#        scanDock.addWidget(self.paramWidget)
#        dockArea.addDock(scanDock)
#        posDock = Dock('positioner', size=(1, 1))
#        posDock.addWidget(self.positioner)
#        dockArea.addDock(posDock, 'above', scanDock)
#        layout.addWidget(dockArea, 2, 3)

#--- fin POSITIONEERRRRRR---------------------------

        self.paramWidget.setFixedHeight(400)

        self.vb.setMouseMode(pg.ViewBox.PanMode)
        self.img = pg.ImageItem()
        self.img.translate(-0.5, -0.5)
        self.vb.addItem(self.img)
        self.vb.setAspectLocked(True)
        imageWidget.setAspectLocked(True)
        self.hist = pg.HistogramLUTItem(image=self.img)
        self.hist.gradient.loadPreset('thermal')  # thermal
# 'thermal', 'flame', 'yellowy', 'bipolar', 'spectrum',
# 'cyclic', 'greyclip', 'grey'

        self.hist.vb.setLimits(yMin=0, yMax=66000)
#        self.cubehelixCM = pg.ColorMap(np.arange(0, 1, 1/256),
#                                       guitools.cubehelix().astype(int))
#        self.hist.gradient.setColorMap(self.cubehelixCM)
        for tick in self.hist.gradient.ticks:
            tick.hide()
        imageWidget.addItem(self.hist, row=1, col=2)
#        self.ROI = guitools.ROI((0, 0), self.vb, (0, 0), handlePos=(1, 0),
#                               handleCenter=(0, 1), color='y', scaleSnap=True,
#                               translateSnap=True)

        self.viewtimer = QtCore.QTimer()
        self.viewtimer.timeout.connect(self.updateView)
        """
        def donothing():
           filewin = tk.Toplevel(root)
           button = tk.Button(filewin, text="Do nothing button")
           button.pack()
#        # Actions in menubar
        root = tk.Tk()
        menubar = tk.Menu(root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New", command=donothing)
        filemenu.add_command(label="Open", command=donothing)
        filemenu.add_command(label="Save", command=donothing)
        filemenu.add_command(label="Save as...", command=donothing)
        filemenu.add_command(label="Close", command=donothing)

        filemenu.add_separator()

        filemenu.add_command(label="Exit", command=root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        editmenu = tk.Menu(menubar, tearoff=0)
        editmenu.add_command(label="Undo", command=donothing)

        root.config(menu=menubar)
        root.config(layout)
        root.mainloop()
#        """
##        menubar = self.menuBar()
#        fileMenu = menubar.addMenu('&File')
#        fileMenu.addAction(self.savePresetAction)
#        fileMenu.addSeparator()


        self.liveviewAction = QtGui.QAction(self)
        self.liveviewAction.setShortcut('Ctrl+a')
        QtGui.QShortcut(
            QtGui.QKeySequence('Ctrl+a'), self, self.liveviewKey)
#        self.liveviewAction.triggered.connect(self.liveviewKey)
        self.liveviewAction.setEnabled(False)

# %%--- paramChanged / PARAMCHANGEDinitialize
    def paramChangedInitialize(self):
        a = [self.scanRange, self.numberofPixels, self.pixelTime,
             self.initialPosition, self.scanModeSet]
        b = [float(self.scanRangeEdit.text()), int(self.numberofPixelsEdit.text()),
             float(self.pixelTimeEdit.text()) / 10**3, (float(self.xLabel.text()),
                  float(self.yLabel.text()), float(self.zLabel.text())),
                  self.scanMode.currentText()]
        print("\n",a)
        print(b,"\n")
        if a == b:
            print("\n no cambió ningun parametro\n")
        else:
            print("\n pasaron cosas\n")
            self.paramChanged()

    def paramChanged(self):
#        if self.detectMode.currentText() == "APD red":
#            self.COchan = 0
#        elif self.detectMode.currentText() == "APD green":
#            self.COchan = 1
#        if self.APDred.isChecked():
#            self.COchan = 0
#        elif self.APDgreen.isChecked():
#            self.COchan = 1

        self.scanModeSet = self.scanMode.currentText()
#        self.PSFModeSet = self.PSFMode.currentText()

        self.scanRange = float(self.scanRangeEdit.text())
#        self.scanRangey = self.scanRangex  # float(self.scanRangeyEdit.text())

        self.numberofPixels = int(self.numberofPixelsEdit.text())
        self.pixelTime = float(self.pixelTimeEdit.text()) / 10**3

        self.Napd = int(np.round(apdrate * self.pixelTime))

        print(self.Napd, "Napd")
        self.initialPosition = (float(self.xLabel.text()), float(self.yLabel.text()),
              float(self.zLabel.text()))

        print(self.initialPosition)

        self.pixelSize = self.scanRange/self.numberofPixels

        self.pixelSizeValue.setText('<strong>{0:.2e}'.format(np.around(
                        1000 * self.pixelSize, 2)))

#        self.linetime = (1/1000)*float(
#                self.pixelTimeEdit.text())*int(self.numberofPixelsEdit.text())
        self.linetime = self.pixelTime * self.numberofPixels

        print(self.linetime, "linetime")

        self.timeTotalLabel.setText("Tiempo total (s) = " +'{}'.format(np.around(
                        2 * self.numberofPixels * self.linetime, 2)))

        size = (self.numberofPixels, self.numberofPixels)

        if self.scanMode.currentText() == "step scan":
            self.barridos()
        if self.scanMode.currentText() == "ramp scan":
            self.rampas()

#        self.inputImage = 1 * np.random.normal(size=size)
        self.blankImage = np.zeros(size)
        self.image = self.blankImage
        self.i = 0

# %% cosas para el save image
    def saveimage(self):
        """ la idea es que escanee la zona deseada (desde cero)
y guarde la imagen"""
        if self.saveimageButton.isChecked():
            self.save = True
            self.liveviewButton.setChecked(False)
#            self.channelsOpen()
            self.MovetoStart()
            self.saveimageButton.setText('Abort')
            self.guarda = np.zeros((self.numberofPixels, self.numberofPixels))
            self.liveviewStart()

        else:
            self.save = False
            print("Abort")
            self.saveimageButton.setText('reintentar')
            self.liveviewStop()

    def steptype(self):
        if self.stepcheck.isChecked():
            self.step = 2
            print("step es 2", self.step==2)
        else:
            self.step = 1
            print("step es 1", self.step==1)
        self.paramChanged()

# %% Liveview
# This is the function triggered by pressing the liveview button
    def liveview(self):
        """ Image live view when not recording"""
        if self.liveviewButton.isChecked():
            self.save = False
            self.paramChangedInitialize()
            self.openShutter("red")
            self.liveviewStart()

        else:
            self.liveviewStop()

    def liveviewStart(self):
        if self.scanMode.currentText() in ["step scan", "ramp scan"]:
            #chanelopen step, channelopen rampa
            self.viewtimer.start(self.linetime)
        else:
            print("elegri step o ramp scan")
            self.liveviewButton.setChecked(False)
#        if self.detectMode.currentText() == "PMT":
#            # channelopen PMT
#            print("PMT")

    def liveviewStop(self):
        if self.save:
            print("listo el pollo")
            self.saveimageButton.setChecked(False)
            self.saveimageButton.setText('Otro Scan and Stop')
            self.save = False

        self.closeShutter("red")
        self.liveviewButton.setChecked(False)
        self.viewtimer.stop()
#        self.done()


# %%---updateView -----------------
    def updateView(self):
        if self.scanMode.currentText() == "step scan":
            self.linea()
        if self.scanMode.currentText() == "ramp scan":
            self.linearampa()
        if self.scanMode.currentText() not in ["step scan", "ramp scan"]:
            print("NO, QUE TOCASTE, ESE NO ANDAAAAAA\n AAAAAAAHH!!!")
            time.sleep(0.1)


        if self.XZcheck.isChecked():
            print("intercambio y por z")  # no sirve si y,z iniciales no son iguales 

        if self.step == 1:
            self.lineData = self.cuentas # self.inputImage[:, self.dy] 
            self.image[:, -1-self.i] = self.lineData  # f
        else:
            cuentas2 = np.split(self.cuentas, 2)
            self.lineData = cuentas2[0] # self.inputImage[:, self.dy] 
            lineData2 = cuentas2[1]

    #        self.lineData = self.inputImage[:, self.i]  # + 2.5*self.i
    #        lineData2 = self.inputImage[:, self.i + 1]
            self.image[:, self.numberofPixels-1-self.i] = self.lineData  # f
            self.image[:, self.numberofPixels-2-self.i] = lineData2  # f

#        self.image[25, self.i] = 333
#        self.image[9, -self.i] = 333

        self.img.setImage(self.image, autoLevels=False)

        if self.save:
            if self.i < self.numberofPixels-self.step:
#                self.guarda[:, self.i] = self.inputImage[:, self.i] 
                # no es necesario crear guarda. self.image es lo mismo
                self.i = self.i + self.step
            else:
#                print(self.i,"i")
                self.guardarimagen()
                if self.CMcheck.isChecked():
                  self.CMmeasure()

                self.saveimageButton.setText('Fin')  # ni se ve
                self.liveviewStop()
                self.MovetoStart()

        else:
            if self.i < self.numberofPixels-self.step:
                self.i = self.i + self.step
            else:
                print(self.i==self.numberofPixels-1,"i")
#                self.i = 0
                if self.Alancheck.isChecked():
                    self.guardarimagen()  # para guardar siempre (Alan idea)
                if self.CMcheck.isChecked():
                    self.CMmeasure()
                if self.Gausscheck.isChecked():
                    self.GaussMeasure()
                self.viewtimer.stop()
                self.MovetoStart()
                if self.Continouscheck.isChecked():
                    self.liveviewStart()
                else:
                    self.liveviewStop()


# %% Barridos
    def barridos(self):
        N=self.numberofPixels
        a = float(self.a.text())  # self.main.a  # 
        b = float(self.b.text())
        r = self.scanRange/2
        X = np.linspace(-r, r, N)
        Y = np.linspace(-r, r, N)
        X, Y = np.meshgrid(X, Y)
        R = np.sqrt((X-a)**2 + (Y-b)**2)
        Z = np.cos(R)
        for i in range(N):
            for j in range(N):
                if Z[i,j]<0:
                    Z[i,j]=0.1
        self.Z = Z
        print("barridos")

    def linea(self):
        Z=self.Z
        if self.step == 1:
            self.cuentas = Z[self.i,:] * abs(np.random.normal(size=(1, self.numberofPixels))[0])
            for i in range(self.numberofPixels):
                borrar = 2
#            time.sleep(self.pixelTime*self.numberofPixels)
    #        print("linea")

        else:# para hacerlo de a lineas y que no sea de 2 en 2:
            self.cuentas = np.zeros((2 * self.numberofPixels))
            self.cuentas = np.concatenate((Z[self.i,:],Z[self.i+1,:]))  # np.random.normal(size=(1, 2*self.numberofPixels))[0]
            for i in range(self.numberofPixels * 2):
                borrar = 2
#            time.sleep(self.pixelTime*self.numberofPixels*2)
    #        print("linea")

# %% MovetoStart
    def MovetoStart(self):
#        self.inputImage = 1 * np.random.normal(
#                    size=(self.numberofPixels, self.numberofPixels))
        t = self.moveTime
        N = self.moveSamples
        tic = ptime.time()
        startY = float(self.initialPosition[1])
        maximoy = startY + ((self.i+1) * self.pixelSize)
        volviendoy = np.linspace(maximoy, startY, N)
        volviendox = np.ones(len(volviendoy)) * float(self.initialPosition[0])
        volviendoz = np.ones(len(volviendoy)) * float(self.initialPosition[2])
        for i in range(len(volviendoy)):
            borrar = volviendoy[i] + volviendox[i] + volviendoz[i]
#            self.aotask.write(
#                 [volviendox[i] / convFactors['x'],
#                  volviendoy[i] / convFactors['y'],
#                  volviendoz[i] / convFactors['z']], auto_start=True)
#            time.sleep(t / N)
        print(t, "vs" , np.round(ptime.time() - tic, 2))
        self.i = 0
        self.Z = self.Z #+ np.random.choice([1,-1])*0.01

# %%--- Guardar imagen
    def guardarimagen(self):
        print("\n Guardo la imagen\n")
        if self.XYcheck.isChecked():
            scanmode = "XY"
        if self.XZcheck.isChecked():
            scanmode = "XZ"
        if self.YZcheck.isChecked():
            scanmode = "YZ"
#        ####name = str(self.edit_save.text()) # solo si quiero elegir el nombre ( pero no quiero)
        filepath = self.main.file_path
#        filepath = "C:/Users/Santiago/Desktop/Germán Tesis de lic/Winpython (3.5.2 para tormenta)/WinPython-64bit-3.5.2.2/notebooks/Guardando tiff/"
        timestr = time.strftime("%Y%m%d-%H%M%S")
        name = str(filepath + "/image-" + scanmode + "-" + timestr + ".tiff")  # nombre con la fecha -hora
        guardado = Image.fromarray(np.transpose(np.flip(self.image, 1)))
        guardado.save(name)

#        self.folderEdit = QtGui.QLineEdit(self.initialDir)
#        openFolderButton = QtGui.QPushButton('Open')
#        openFolderButton.clicked.connect(self.openFolder)
#        self.specifyfile = QtGui.QCheckBox('Specify file name')
#        self.specifyfile.clicked.connect(self.specFile)
#        self.filenameEdit = QtGui.QLineEdit('Current_time')
#        self.formatBox = QtGui.QComboBox()
#        self.formatBox.addItem('tiff')
#        self.formatBox.addItem('hdf5')
# --------------------------------------------------------------------------

# %%---Move----------------------------------------

    def move(self, axis, dist):
        """moves the position along the axis specified a distance dist."""
        t = self.moveTime
        N = self.moveSamples
        # read initial position for all channels
        texts = [getattr(self, ax + "Label").text()
                 for ax in self.activeChannels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]
        initPos = np.array(initPos, dtype=float)[:, np.newaxis]
        fullPos = np.repeat(initPos, self.nSamples, axis=1)

        # make position ramp for moving axis
        ramp = makeRamp(0, dist, self.nSamples)
        fullPos[self.activeChannels.index(axis)] += ramp

#        factors = np.array([convFactors['x'], convFactors['y'],
#                           convFactors['z']])[:, np.newaxis]
#        fullSignal = fullPos/factors
        toc = ptime.time()
        for i in range(self.nSamples):
#            self.aotask.write(fullSignal, auto_start=True)
#            time.sleep(t / N)
            borrar = 1+1

        print("se mueve en", np.round(ptime.time() - toc, 3), "segs")

        # update position text
        newPos = fullPos[self.activeChannels.index(axis)][-1]
#        newText = "<strong>" + axis + " = {0:.2f} µm</strong>".format(newPos)
        newText = "{}".format(newPos)
        getattr(self, axis + "Label").setText(newText)
        self.paramChanged()

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
        if self.initialPosition[2]<float(getattr(self, 'z' + "StepEdit").text()):
            print("OJO!, te vas a Z's negativos")
            self.zStepEdit.setStyleSheet(" background-color: red; ")
#            setStyleSheet("color: rgb(255, 0, 255);")
        else:
            self.move('z', -float(getattr(self, 'z' + "StepEdit").text()))
            self.zStepEdit.setStyleSheet(" background-color: ")
        if self.initialPosition[2] == 0:  # para no ira z negativo
            self.zDownButton.setStyleSheet(
                "QPushButton { background-color: red; }"
                "QPushButton:pressed { background-color: blue; }")
            self.zDownButton.setEnabled(False)

# ---go CM goto
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

    def goto(self):

        if float(self.zgotoLabel.text()) < 0:
            print("Z no puede ser negativo!!!")
            self.zgotoLabel.setStyleSheet(" background-color: red")
            time.sleep(1)

        else:
            self.zgotoLabel.setStyleSheet(" background-color: ")
            print("arranco en",float(self.xLabel.text()), float(self.yLabel.text()),
                  float(self.zLabel.text()))

            self.moveto(float(self.xgotoLabel.text()),
                        float(self.ygotoLabel.text()),
                        float(self.zgotoLabel.text()))

            print("termino en", float(self.xLabel.text()), float(self.yLabel.text()),
                  float(self.zLabel.text()))

            if float(self.zLabel.text()) == 0:  # para no ira z negativo
                self.zDownButton.setStyleSheet(
                    "QPushButton { background-color: red; }"
                    "QPushButton:pressed { background-color: blue; }")
                self.zDownButton.setEnabled(False)
            else:
                self.zDownButton.setStyleSheet(
                    "QPushButton { background-color: }")
                self.zDownButton.setEnabled(True)

            self.paramChanged()
# --- moveto
    def moveto(self, x, y, z):
        """moves the position along the axis to a specified point."""
        t = self.moveTime * 3
        N = self.moveSamples * 3
        # read initial position for all channels
        texts = [getattr(self, ax + "Label").text()
                 for ax in self.activeChannels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]

        rampx = makeRamp(float(initPos[0]), x, self.nSamples)# / convFactors['x']
        rampy = makeRamp(float(initPos[1]), y, self.nSamples)# / convFactors['y']
        rampz = makeRamp(float(initPos[2]), z, self.nSamples)# / convFactors['z']
#        ramp = np.array((rampx, rampy, rampz))

        tuc = ptime.time()
        for i in range(self.nSamples):
            borrar = rampx[i] + rampy[i] + rampz[i]
#            self.aotask.write([rampx[i] / convFactors['x'],
#                               rampy[i] / convFactors['y'],
#                               rampz[i] / convFactors['z']], auto_start=True)
#            time.sleep(t / N)

        print("se mueve todo en", np.round(ptime.time()-tuc, 3),"segs")

        self.xLabel.setText("{}".format(np.around(float(rampx[-1]), 2)))
        self.yLabel.setText("{}".format(np.around(float(rampy[-1]), 2)))
        self.zLabel.setText("{}".format(np.around(float(rampz[-1]), 2)))

# %%--- Shutter time --------------------------

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
        print("abre shutter", p)
        shutters = ["red", "green", "otro"]
        for i in range(3):
            if p == shutters[i]:
                self.shuttersignal[i] = 5
#        self.dotask.write(self.shuttersignal, auto_start=True)
        print(self.shuttersignal)
        self.checkShutters()

    def closeShutter(self, p):
        print("cierra shutter", p)
        shutters = ["red", "green", "otro"]
        for i in range(3):
            if p == shutters[i]:
                self.shuttersignal[i] = 0
#        self.dotask.write(self.shuttersignal, auto_start=True)
        print(self.shuttersignal)
        self.checkShutters()

    def checkShutters(self):
        if self.shuttersignal[0]:
            self.shutterredbutton.setChecked(True)
        else:
            self.shutterredbutton.setChecked(False)
        if self.shuttersignal[1]:
            self.shuttergreenbutton.setChecked(True)
        else:
            self.shuttergreenbutton.setChecked(False)
        if self.shuttersignal[2]:
            self.shutterotrobutton.setChecked(True)
        else:
            self.shutterotrobutton.setChecked(False)
#        if self.shuttergreen.isChecked():
#            print("shutter verde")
#
#        if self.shutterotro.isChecked():
#            print("shutter otro")
# Es una idea de lo que tendria que hacer la funcion

# %% rampas 
    def rampas(self):
        N=self.numberofPixels
        a = float(self.a.text())
        b = float(self.b.text())
        r = self.scanRange/2
        X = np.linspace(-r, r, N)
        Y = np.linspace(-r, r, N)
        X, Y = np.meshgrid(X, Y)
        R = np.sqrt((X-a)**2 + (Y-b)**2)
        Z = np.cos(R)
        for i in range(N):
            for j in range(N):
                if Z[i,j]<0:
                    Z[i,j]=0
        self.Z = Z
        print("rampsa")

    def linearampa(self):

        Z=self.Z
        if self.step==1:
            self.cuentas = np.zeros((self.numberofPixels))
            self.cuentas = Z[self.i,:]  # np.random.normal(size=(1, self.numberofPixels))[0]
            for i in range(self.numberofPixels):
                borrar = 2
#            time.sleep(self.pixelTime*self.numberofPixels)
    #        print("linearampa")
    
        else:#para hacerlo de a lineas y que no sea de 2 en 2:

            self.cuentas = np.concatenate((Z[self.i,:],Z[self.i+1,:])) #np.random.normal(size=(1, 2*self.numberofPixels))[0]
            for i in range(2*self.numberofPixels):
                borrar = 2
#            time.sleep(self.pixelTime*2*self.numberofPixels)


#    def squareOrNot(self):
#        if self.squareRadio.isChecked():
#            self.square = True
#            print("Escaneo cuadrado (x = y)")
#        else:
#            self.square = False
#            print("Escaneo rectangular")
#
#    def squarex(self):
#        if self.square:
#            print("valores iguales, cuadrado")
#            self.scanRangeyEdit = QtGui.QLineEdit(self.scanRangexEdit.text())
#            self.scanRangexEdit.textChanged.connect(self.paramChanged)
#        else:
#            print("rectangulo")
#            self.scanRangexEdit.textChanged.connect(self.paramChanged)
#            self.scanRangeyEdit.textChanged.connect(self.paramChanged)
#
#    def squarey(self):
#        if self.squareOrNot:
#            self.scanRangexEdit = QtGui.QLineEdit(self.scanRangeyEdit.text())
#            self.scanRangeyEdit.textChanged.connect(self.paramChanged)
#        else:
#            self.scanRangexEdit.textChanged.connect(self.paramChanged)
#            self.scanRangeyEdit.textChanged.connect(self.paramChanged)

# - - - ----------------------------------------

#class InterfazGUI(QtGui.QMainWindow):
#
#    def __init__(self, *args, **kwargs):
#        super().__init__(*args, **kwargs)
#
#        # Dock widget
#        dockArea = DockArea()
#    
#        scanDock = Dock('Scan', size=(1, 1))
#        scanWidget = ScanWidget()
#        scanDock.addWidget(scanWidget)
#        dockArea.addDock(scanDock)
#    
#        piezoDock = Dock('Piezo positioner', size=(1, 1))
#        piezoWidget = Positionner(scanWidget)
#        piezoDock.addWidget(piezoWidget)
#        dockArea.addDock(scanDock, 'below', scanDock)
#    
#        self.setWindowTitle('ASDASDASDW')
#        self.cwidget = QtGui.QWidget()
#        self.setCentralWidget(self.cwidget)
#        layout = QtGui.QGridLayout()
#        self.cwidget.setLayout(layout)
#        layout.addWidget(dockArea, 0, 0, 4, 1)


# %%--- ploting in live
    def plotLive(self):
        texts = [getattr(self, ax + "Label").text() for ax in self.activeChannels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]
        xv = np.linspace(0, self.scanRange, self.numberofPixels) + float(initPos[0])
        yv = np.linspace(0, self.scanRange, self.numberofPixels) + float(initPos[1])
        X, Y = np.meshgrid(xv, yv)
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
        try:

            (height, x, y, width_x, width_y) = self.params
            resol = 2
            for i in range(resol):
                for j in range(resol):
                    ax.text(xv[int(x)+i],yv[int(y)+j],"◘",color='m')

            plt.text(0.95, 0.05, """
            x : %.1f
            y : %.1f """ %(xv[int(x)], yv[int(y)]),
                    fontsize=16, horizontalalignment='right',
                    verticalalignment='bottom', transform=ax.transAxes)

        except:
            pass
        plt.show()

    def otroPlot(self):
        texts = [getattr(self, ax + "Label").text() for ax in self.activeChannels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]
        xv = np.linspace(0, self.scanRange, self.numberofPixels) + float(initPos[0])
        yv = np.linspace(0, self.scanRange, self.numberofPixels) + float(initPos[1])
        X, Y = np.meshgrid(xv, yv)
        try:
            plt.matshow(self.data, cmap=plt.cm.gist_earth_r)
            plt.colorbar()
    
            plt.contour(self.fit(*np.indices(self.data.shape)), cmap=plt.cm.copper)
            ax = plt.gca()
            (height, x, y, width_x, width_y) = self.params

            plt.text(0.95, 0.05, """
            x : %.1f
            y : %.1f
            width_x : %.1f
            width_y : %.1f""" %(xv[int(x)], yv[int(y)], width_x, width_y),
                    fontsize=16, horizontalalignment='right',
                    verticalalignment='bottom', transform=ax.transAxes)
            print("x",xv[int(x)])
        except:
            pass

    def liveviewKey(self):
        '''Triggered by the liveview shortcut.'''
        
        if self.liveviewButton.isChecked():
            self.liveviewStop()
            self.liveviewButton.setChecked(False)
        
        else:
            self.liveviewButton.setChecked(True)
            self.liveview()
#            self.liveviewStart()

## %% selectfolder
#    def openFolder(self):
#    # Quedo obsoleto con la barra de herramientas.
#        print("tengoq ue sacarlo, no sirve mas")
#        root = tk.Tk()
#        root.withdraw()
#        
#        self.file_path = filedialog.askdirectory()
#        print(self.file_path,2)
#        self.NameDirValue.setText(self.file_path)
#        try:
#            if sys.platform == 'darwin':
#                subprocess.check_call(['open', '', self.folderEdit.text()])
#            elif sys.platform == 'linux':
#                subprocess.check_call(
#                    ['gnome-open', '', self.folderEdit.text()])
#            elif sys.platform == 'win32':
#                os.startfile(self.folderEdit.text())
#
#        except FileNotFoundError:
#            if sys.platform == 'darwin':
#                subprocess.check_call(['open', '', self.dataDir])
#            elif sys.platform == 'linux':
#                subprocess.check_call(['gnome-open', '', self.dataDir])
#            elif sys.platform == 'win32':
#                os.startfile(self.dataDir)

# %% GaussMeasure 
    def GaussMeasure(self):
        tic = ptime.time()
        self.data = self.image
        params = fitgaussian(self.data)
        self.fit = gaussian(*params)
        self.params = params
        (height, x, y, width_x, width_y) = params

        tac = ptime.time()
        print(np.round((tac-tic)*10**3,3), "(ms)solo Gauss\n")
#        texts = [getattr(self, ax + "Label").text() for ax in self.activeChannels]
#        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]
#        xv = np.linspace(0, self.scanRange, self.numberofPixels) + float(initPos[0])
#        yv = np.linspace(0, self.scanRange, self.numberofPixels) + float(initPos[1])

        Normal = self.scanRange / self.numberofPixels  # Normalizo
        xx = x*Normal
        yy = y*Normal
        self.GaussxValue.setText(str(xx))
        self.GaussyValue.setText(str(yy))

# %%--- CM measure
    def CMmeasure(self):

        self.viewtimer.stop()

        I = self.image
        N = len(I)  # numberfoPixels

        xcm, ycm = ndimage.measurements.center_of_mass(I)  # Los calculo y da lo mismo
        print("Xcm=", xcm,"\nYcm=", ycm)
        self.xcm = xcm
        self.ycm = ycm


        Normal = self.scanRange / self.numberofPixels  # Normalizo
        self.CMxValue.setText(str(xcm*Normal))
        self.CMyValue.setText(str(ycm*Normal))



# %% Presets copiados del inspector
    def Presets(self):
        if self.presetsMode .currentText() == self.presetsModes[0]:
            self.scanRangeEdit.setText('5')
            self.pixelTimeEdit.setText('0.01')
            self.numberofPixels.setText('100')


        elif self.presetsMode .currentText() == self.presetsModes[1]:
            self.scanRangeEdit.setText('100')
            self.pixelTimeEdit.setText('0.2')
            self.numberofPixels.setText('128')


        elif self.presetsMode .currentText() == self.presetsModes[2]:
            self.scanRangeEdit.setText('50')
            self.pixelTimeEdit.setText('0.05')
            self.numberofPixels.setText('250')

        else:
            print("nunca tiene que entrar aca")

        self.paramChanged()
#        self.preseteado = True    creo que no lo voy a usar

#%%  FIN

if __name__ == '__main__':

    app = QtGui.QApplication([])
#    win = ScanWidget()
    win = MainWindow()
    win.show()

#    app.exec_()
    sys.exit(app.exec_() )
