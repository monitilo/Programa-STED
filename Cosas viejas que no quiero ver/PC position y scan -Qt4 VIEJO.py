
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
from pyqtgraph.Qt import QtCore, QtGui#, QtWidgets

#from pyqtgraph.dockarea import Dock, DockArea
import pyqtgraph.ptime as ptime
#
from PIL import Image

import re

import tkinter as tk
from tkinter import filedialog

import tools
import viewbox_tools

device = 9
convFactors = {'x': 25, 'y': 25, 'z': 1.683}  # la calibracion es 1 µm = 40 mV;
# la de z es 1 um = 0.59 V
apdrate = 10**5


def makeRamp(start, end, samples):
    return np.linspace(start, end, num=samples)

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

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

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

# ---- fin parte del positioner ----------
        self.step = 1
        imageWidget = pg.GraphicsLayoutWidget()
        self.vb = imageWidget.addViewBox(row=1, col=1)

        # LiveView Button

        self.liveviewButton = QtGui.QPushButton('confocal LIVEVIEW')
        self.liveviewButton.setCheckable(True)
        self.liveviewButton.clicked.connect(self.liveview)

        self.liveviewButton.setToolTip('This is a tooltip message.')

        # save image Button

        self.saveimageButton = QtGui.QPushButton('Scan and Save')
        self.saveimageButton.setCheckable(True)
        self.saveimageButton.clicked.connect(self.saveimage)
        self.saveimageButton.setStyleSheet(
                "QPushButton { background-color: gray; }"
                "QPushButton:pressed { background-color: blue; }")

        self.NameDirButton = QtGui.QPushButton('select Dir')
        self.NameDirButton.clicked.connect(self.selectFolder)
        self.file_path = os.path.abspath("")
        self.OpenButton = QtGui.QPushButton('open dir')
        self.OpenButton.clicked.connect(self.openFolder)
        # Defino el tipo de Scan que quiero

        self.scanMode = QtGui.QComboBox()
        self.scanModes = ['step scan', 'ramp scan', 'otro scan']
        self.scanMode.addItems(self.scanModes)
#        self.scanMode.currentIndexChanged.connect(self.paramChanged)
        self.scanMode.activated.connect(self.paramChanged)  # funcionan las dos

#        self.detectMode = QtGui.QComboBox()
#        self.detectModes = ['APD red', 'APD green', 'PMT']
#        self.detectMode.addItems(self.detectModes)

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

        self.CMcheck = QtGui.QCheckBox('calcula CM')
        self.CMcheck.setChecked(False)
        self.CMcheck.clicked.connect(self.CMmeasure)
    # Para alternar entre pasos de a 1 y de a 2 (en el programa final se va)

        self.stepcheck = QtGui.QCheckBox('hacerlo de a 2')
        self.stepcheck.clicked.connect(self.steptype)
        # botones para shutters (por ahora no hacen nada)

        self.shutterredbutton = QtGui.QCheckBox('shutter 640')
#        self.shutterredbutton.setChecked(False)
        self.shutterredbutton.clicked.connect(self.shutterred)
        self.shuttergreenbutton = QtGui.QCheckBox('shutter 532')
#        self.shuttergreenbutton.setChecked(False)
        self.shuttergreenbutton.clicked.connect(self.shuttergreen)
        self.shutterotrobutton = QtGui.QCheckBox('shutter otro')
#        self.shutterotrobutton.setChecked(False)
        self.shutterotrobutton.clicked.connect(self.shutterotro)
        self.shuttersignal = [0, 0, 0]

#       This boolean is set to True when open the nidaq channels
        self.ischannelopen = False

    # ROI buttons
        self.roi = None
        self.ROIButton = QtGui.QPushButton('ROI')
        self.ROIButton.setCheckable(True)
        self.ROIButton.clicked.connect(self.ROImethod)

        self.selectROIButton = QtGui.QPushButton('select ROI')
        self.selectROIButton.clicked.connect(self.selectROI)

        self.roiline = None
        self.ROIlineButton = QtGui.QPushButton('lineROIline')
        self.ROIlineButton.setCheckable(True)
        self.ROIlineButton.clicked.connect(self.ROIlinear)
        self.selectlineROIButton = QtGui.QPushButton('select line ROI')
        self.selectlineROIButton.clicked.connect(self.selectLineROI)
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

        self.algo = QtGui.QLineEdit('4')


        self.onlyInt = QtGui.QIntValidator(0,5000)
        self.numberofPixelsEdit.setValidator(self.onlyInt)
        self.onlypos = QtGui.QDoubleValidator(0, 1000,10)
        self.pixelTimeEdit.setValidator(self.onlypos)
        self.scanRangeEdit.setValidator(self.onlypos)

#        label_save = QtGui.QLabel('Nombre del archivo (archivo.tiff)')
#        label_save.resize(label_save.sizeHint())
#        self.edit_save = QtGui.QLineEdit('imagenScan.tiff')
#        self.edit_save.resize(self.edit_save.sizeHint())

        self.numberofPixelsEdit.textChanged.connect(self.paramChanged)
#        self.scanRangexEdit.textChanged.connect(self.squarex)
#        self.scanRangeyEdit.textChanged.connect(self.squarey)
        self.scanRangeEdit.textChanged.connect(self.paramChanged)
#        self.scanRangeyEdit.textChanged.connect(self.paramChanged)
        self.pixelTimeEdit.textChanged.connect(self.paramChanged)
#        self.initialPositionEdit.textChanged.connect(self.paramChanged)

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
        self.a.textChanged.connect(self.paramChanged)
        self.b.textChanged.connect(self.paramChanged)

        self.plotLivebutton = QtGui.QPushButton('Plot this image')
        self.plotLivebutton.setChecked(False)
        self.plotLivebutton.clicked.connect(self.plotLive)

        self.paramChanged()

        self.paramWidget = QtGui.QWidget()

        grid = QtGui.QGridLayout()
#        self.setLayout(grid)
#        grid.addWidget(imageWidget, 2, 0)
#        grid.addWidget(self.paramWidget, 2, 1)



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

        subgrid.addWidget(self.NameDirButton, 18, 2,2,1)
        subgrid.addWidget(self.OpenButton, 19, 2,1,1)

        subgrid.addWidget(self.stepcheck, 12, 1)
#        subgrid.addWidget(self.squareRadio, 12, 2)

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
        
        group2 = QtGui.QButtonGroup(self.paramWidget)
        self.APDred=QtGui.QRadioButton("APD red")
        self.APDgreen=QtGui.QRadioButton("APD green")
        self.APDred.setChecked(True)
        self.APDgreen.setChecked(False)
        group2.addButton(self.APDred)
        group2.addButton(self.APDgreen)
        subgrid.addWidget(self.APDred, 0, 1)
        subgrid.addWidget(self.APDgreen, 0, 2)
        subgrid.addWidget(self.plotLivebutton, 6, 2)

        subgrid.addWidget(self.CMcheck, 8, 2)

        subgrid.addWidget(self.ROIButton, 2, 3)
        subgrid.addWidget(self.selectROIButton, 3, 3)

        subgrid.addWidget(self.ROIlineButton, 4, 3)
        subgrid.addWidget(self.selectlineROIButton, 5, 3)
# --- POSITIONERRRRR-------------------------------

        self.positioner = QtGui.QWidget()
#        grid.addWidget(self.positioner, 1, 0)
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
#        grid.addWidget(self.gotoWidget, 1, 1)
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



##    # Nueva interface mas comoda!
#        hbox = QtGui.QHBoxLayout(self)
#        ViewBox=QtGui.QFrame()
#        ViewBox.setFrameShape(QtGui.QFrame.StyledPanel)
#        ViewBox.setLayout(grid)  # viewbox
#
#        gotowidget = QtGui.QFrame()
#        gotowidget.setFrameShape(QtGui.QFrame.StyledPanel)
#        gotowidget.setLayout(layout2)  # gotoWidget
#
#        positionermenu=QtGui.QFrame()
#        positionermenu.setFrameShape(QtGui.QFrame.StyledPanel)
#        positionermenu.setLayout(layout)  # positioner
#
#        menuwidg=QtGui.QFrame()
#        menuwidg.setFrameShape(QtGui.QFrame.StyledPanel)
#        menuwidg.setLayout(subgrid)  # menu con cosas izquierda
#
#
#        splitter1 = QtGui.QSplitter(QtCore.Qt.Horizontal)
#        splitter1.addWidget(positionermenu)
#        splitter1.addWidget(gotowidget)
#        splitter1.setSizes([10, 10])
#
#        splitter15 = QtGui.QSplitter(QtCore.Qt.Vertical)
#        splitter15.addWidget(ViewBox)
#        splitter15.addWidget(splitter1)
#        splitter15.setSizes([10**6, 1])
#
#        splitter2 = QtGui.QSplitter(QtCore.Qt.Horizontal)
#        splitter2.addWidget(splitter15)
#        splitter2.addWidget(menuwidg)
#        splitter2.setSizes([10**6, 1])
#
##        hbox.addWidget(splitter2)
#        hbox.addWidget(splitter2)
#
#        self.setLayout(hbox)
        #no se como hacerla andar con docks


#        win = QtGui.QMainWindow()
        hbox = QtGui.QHBoxLayout(self)
        from pyqtgraph.dockarea import DockArea, Dock
        dockArea = DockArea()

        viewDock = Dock('viewbox', size=(100, 100))
        viewDock.addWidget(imageWidget)
        dockArea.addDock(viewDock,'left')

        scanDock = Dock('Scan parameters', size=(10, 10))
        scanDock.addWidget(self.paramWidget)
        dockArea.addDock(scanDock,'right')

        posDock = Dock('positioner', size=(1, 1))
        posDock.addWidget(self.positioner)
        dockArea.addDock(posDock, 'bottom', viewDock)

        gotoDock = Dock('goto', size=(1, 1))
        gotoDock.addWidget(self.gotoWidget)
        dockArea.addDock(gotoDock, 'above', posDock)

        hbox.addWidget(dockArea)
        self.setLayout(hbox)

        self.setWindowTitle('Programa genial dockeado')

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
#                                       viewbox_tools.cubehelix().astype(int))
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

# %% paramChanged
    def paramChanged(self):

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

        self.pixelSizeValue.setText('{}'.format(np.around(
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
            self.movetoStart()
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
            self.openShutter("red")
            self.liveviewStart()

        else:
            self.liveviewStop()

    def liveviewStart(self):
        if self.scanMode.currentText() in ["step scan", "ramp scan"]:
            #chanelopen step, channelopen rampa
            self.time = ptime.time()
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


# ---updateView -----------------
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
                self.guardarimagen()
                if self.CMcheck.isChecked():
                  self.CMmeasure()

                self.saveimageButton.setText('Fin')  # ni se ve
                self.liveviewStop()
                self.movetoStart()

        else:
            if self.i < self.numberofPixels-self.step:
                self.i = self.i + self.step
            else:
#                self.i = 0
                time = (ptime.time()-self.tic)
                self.algo.setText("a{}".format(time))
                if self.Alancheck.isChecked():
                    self.guardarimagen()  # para guardar siempre (Alan idea)
                if self.CMcheck.isChecked():
                  self.CMmeasure()
                self.movetoStart()
                self.viewtimer.start(self.linetime)

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
                    Z[i,j]=0
        self.Z = Z
        print("barridos")

    def linea(self):
        Z=self.Z
        if self.step == 1:
            self.cuentas = Z[self.i,:]  # np.random.normal(size=(1, self.numberofPixels))[0]
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
    def movetoStart(self):
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
        self.Z = self.Z# + np.random.choice([1,-1])*0.01

# %%--- Guardar imagen SAVE
    def guardarimagen(self):
        print("\n Guardo la imagen\n")
        if self.XYcheck.isChecked():
            scanmode = "XY"
        if self.XZcheck.isChecked():
            scanmode = "XZ"
        if self.YZcheck.isChecked():
            scanmode = "YZ"
#        filepath = self.main.file_path
        timestr = time.strftime("%Y%m%d-%H%M%S")
        name = str(self.file_path + "/image-" + scanmode + "-" + timestr + ".tiff")  # nombre con la fecha -hora
        guardado = Image.fromarray(np.transpose(np.flip(self.image, 1)))
        guardado.save(name)
#        ####name = str(self.edit_save.text()) # solo si quiero elegir el nombre ( pero no quiero)
#        filepath = self.main.file_path
#        filepath = "C:/Users/Santiago/Desktop/Germán Tesis de lic/Winpython (3.5.2 para tormenta)/WinPython-64bit-3.5.2.2/notebooks/Guardando tiff/"

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

# ---goCM goto
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

# %% rampas y eso ---
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
            self.cuentas = Z[self.i,:]  * abs(np.random.normal(size=(1, self.numberofPixels))[0])
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

    def liveviewKey(self):
        '''Triggered by the liveview shortcut.'''
        
        if self.liveviewButton.isChecked():
            self.liveviewStop()
            self.liveviewButton.setChecked(False)
        
        else:
            self.liveviewButton.setChecked(True)
            self.liveviewStart()
# %% buttos to open and select folder
    def selectFolder(self):

        root = tk.Tk()
        root.withdraw()
        
        self.file_path = filedialog.askdirectory()
        print(self.file_path,2)
        self.NameDirValue.setText(self.file_path)

    def openFolder(self):
        os.startfile(self.file_path)

# %%--- CM measure
    def CMmeasure(self):

        from scipy import ndimage
        I = self.image
        N = len(I)
#        xcm = 0
#        ycm = 0
#        for i in range(N):
#            for j in range(N):
##                if Z[i,j]<0:
##                    Z[i,j]=0
#                xcm = xcm + (Z[i,j]*i)
#                ycm = ycm + (Z[i,j]*j)
#        M = np.sum(Z)
#        xcm = xcm/M
#        ycm = ycm/M
        xcm, ycm = ndimage.measurements.center_of_mass(I)  # Los calculo y da lo mismo
        print("Xcm=", xcm,"\nYcm=", ycm)
        self.xcm = xcm
        self.ycm = ycm
#        xc = int(np.round(xcm,2))
#        yc = int(np.round(ycm,2))
        Normal = self.scanRange / self.numberofPixels
        self.CMxValue.setText(str(xcm*Normal))
        self.CMyValue.setText(str(ycm*Normal))

#        resol = 2
#        for i in range(resol):
#            for j in range(resol):
#                ax.text(X[xc+i,yc+j],Y[xc+i,yc+j],"☻",color='w')
        lomas = np.max(I)
        Npasos = 4
        paso = lomas/Npasos
        tec=time.time()
        SZ = I.ravel()
        mapa = np.zeros((N,N))
        Smapa = mapa.ravel()
        for i in range(len(SZ)):
            if SZ[i] > paso:
                Smapa[i] = 0.33
            if SZ[i] > paso*2:
                Smapa[i] = 0.66
            if SZ[i] > paso*3:
                Smapa[i] = 0.99
        mapa = np.array(np.split(Smapa,N))
        print(np.round(time.time()-tec,4),"s tarda con 1 for\n")
        self.img.setImage(mapa, autoLevels=False)

        # %%  ROI cosas
    def ROIlinear(self):
        def updatelineal():
            array = self.linearROI.getArrayRegion(self.image, self.img)
            self.curve.setData(array)

        if self.ROIlineButton.isChecked():

            self.linearROI = pg.LineSegmentROI([[10, 64], [120,64]], pen='m')
            self.vb.addItem(self.linearROI)
            self.linearROI.sigRegionChanged.connect(updatelineal)
            self.p6 = self.imageWidget.addPlot(row=2,col=1,title="Updating plot")
            self.curve = self.p6.plot(open='y')
        else:
            self.vb.removeItem(self.linearROI)
            self.linearROI.hide()
            self.imageWidget.removeItem(self.p6)

    def selectLineROI(self):
        array = self.linearROI.getArrayRegion(self.image, self.img)
        plt.plot(array)
        plt.show()

# %%  ROI cosas
#    def ROIlinear(self):
#        self.NofPixels = self.numberofPixels
#
#        if self.ROIlineButton.isChecked():
#            print("entra")
#
#            self.linearROI = pg.LineSegmentROI((0,50))
#            self.vb.addItem(self.linearROI)
##            self.roi = viewbox_tools.cropROI(ROIpos, self.vb)
#            print("termina")
#        else:
#            self.vb.removeItem(self.linearROI)
#            self.linearROI.hide()
#
#    def selectLineROI(self):
#        self.NofPixels = self.numberofPixels
#        self.pxSize = self.pixelSize
#        self.liveviewStop()
#
#        print("Estoy en", float(self.xLabel.text()), float(self.yLabel.text()),
#              float(self.zLabel.text()))
#
#        array = self.linearROI.getArrayRegion(self.image, self.img)
#        ROIpos = np.array(self.linearROI.pos())
#        print(ROIpos)
#        print(array)
#        newPos_px = tools.ROIscanRelativePOS(ROIpos,
#                                             self.NofPixels,
#                                             np.shape(array)[0])
#        print(newPos_px)
##        print(self.initialPosition)
#        newPos_µm = newPos_px * self.pxSize + self.initialPosition[0:2]
##
#        newPos_µm = np.around(newPos_µm, 2)
#        print(newPos_µm)
#        newRange_px = np.shape(array)[0]
#        newRange_µm = self.pxSize * newRange_px
#        newRange_µm = np.around(newRange_µm, 2)
#        print(newRange_px, newRange_µm)
#        plt.plot(array)
#        plt.show()
#        #-- Generate some data...
##        x, y = np.mgrid[-5:5:0.1, -5:5:0.1]
##        z = np.sqrt(x**2 + y**2) + np.sin(x**2 + y**2)
##        
##        #-- Extract the line...
##        # Make a line with "num" points...
##        x0, y0 = array[0] # These are in _pixel_ coordinates!!
##        x1, y1 = 60, 75
##        length = int(np.hypot(x1-x0, y1-y0))
##        x, y = np.linspace(x0, x1, length), np.linspace(y0, y1, length)
##        
##        # Extract the values along the line
##        zi = self.image[x.astype(np.int), y.astype(np.int)]
##        
##        #-- Plot...
##        fig, axes = plt.subplots(nrows=2)
##        axes[0].imshow(z)
##        axes[0].plot([x0, x1], [y0, y1], 'ro-')
##        axes[0].axis('image')
##        
##        axes[1].plot(zi)
##        
##        plt.show()

#import pyqtgraph.examples
#pyqtgraph.examples.run()

# %% Lucho's ROI
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
        self.NofPixels = self.numberofPixels
        self.pxSize = self.pixelSize
        self.liveviewStop()

        print("Estoy en", float(self.xLabel.text()), float(self.yLabel.text()),
              float(self.zLabel.text()))

        array = self.roi.getArrayRegion(self.image, self.img)
        ROIpos = np.array(self.roi.pos())

        newPos_px = tools.ROIscanRelativePOS(ROIpos,
                                             self.NofPixels,
                                             np.shape(array)[1])
        print(self.initialPosition)
        newPos_µm = newPos_px * self.pxSize + self.initialPosition[0:2]

        newPos_µm = np.around(newPos_µm, 2)

#        self.initialPosEdit.setText('{} {} {}'.format(newPos_µm[0],
#                                                      newPos_µm[1],
#                                                      self.initialPos[2]))

        self.xLabel.setText("{}".format((float(newPos_µm[0]))))
        self.yLabel.setText("{}".format((float(newPos_µm[1]))))
        self.zLabel.setText("{}".format((float(self.initialPosition[2]))))

        print("Roi va a", float(self.xLabel.text()), float(self.yLabel.text()),
              float(self.zLabel.text()))
        newRange_px = np.shape(array)[0]
        newRange_µm = self.pxSize * newRange_px
        newRange_µm = np.around(newRange_µm, 2)

        self.scanRangeEdit.setText('{}'.format(newRange_µm))


        self.paramChanged()
#        self.ROIButton.setChecked(False)

#        self.roi.hide()

if __name__ == '__main__':

    app = QtGui.QApplication([])
#    win = ScanWidget()
    win = ScanWidget()
    win.show()

#    app.exec_()
    sys.exit(app.exec_() )
