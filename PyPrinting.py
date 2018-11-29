# import scipy.ndimage as ndi

import os
import tkinter as tk
from tkinter import filedialog

import numpy as np
import time

import matplotlib.pyplot as plt

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.ptime as ptime
from pyqtgraph.dockarea import Dock, DockArea

from PIL import Image
from scipy import ndimage

import re

import tools
import viewbox_tools

import nidaqmx

device = nidaqmx.system.System.local().devices['Dev1']

convFactors = {'x': 25, 'y': 25, 'z': 1.683}  # TODO: CAMBIAR!!!!!
# la calibracion es 1 µm = 40 mV en x,y (galvos);
# en z, 0.17 µm = 0.1 V  ==> 1 µm = 0.58 V
# 1.68 um = 1 V ==> 1 um = 0.59V  # asi que promedie, y lo puse a ojo.
minVolt = {'x': -10, 'y': -10, 'z': 0}
maxVolt = {'x': 10, 'y': 10, 'z': 10}
resolucionDAQ = 0.0003 * 2 * convFactors['x']
# V => µm; uso el doble para no errarle
activeChannels = ["x", "y", "z"]
AOchans = [0, 1]  # , 2]  # x,y,z
detectModes = ['APD red', 'APD yellow', 'both APDs', 'PMT']
# detectModes[1:n] son los apd's; detectMode[-1] es el PMT y [-2] otros.
COchans = [0, 1]  # apd rojo y verde
PMTchan = 1
scanModes = ['ramp scan', 'step scan', 'full frec ramp', "slalom"]

shutters = ["red", "STED", "yellow"]  # digitals out channesl [0, 1, 2]

apdrate = 10**5


# %% Main Window
class MainWindow(QtGui.QMainWindow):
    def closeEvent(self, event):
        reply = QtGui.QMessageBox.question(self, 'Quit', 'Are u Sure to Quit?',
                                           QtGui.QMessageBox.No |
                                           QtGui.QMessageBox.Yes)
        if reply == QtGui.QMessageBox.Yes:
            print("YES")
            event.accept()
            self.close()
            self.liveviewStop()
        else:
            event.ignore()
            print("NOOOO")

    def newCall(self):
        print('New')

    def openCall(self):
        os.startfile(self.file_path)
        print('Open: ', self.file_path)

    def exitCall(self):
        self.a = -1.5
        print('Exit app (no hace nada)')

    def localDir(self):
        print('poner la carpeta donde trabajar')
        root = tk.Tk()
        root.withdraw()

        self.file_path = filedialog.askdirectory()
        print(self.file_path, "◄ dire")
        self.form_widget.NameDirValue.setText(self.file_path)
        self.form_widget.NameDirValue.setStyleSheet(" background-color: ")
#        self.form_widget.paramChanged()

    def create_daily_directory(self):
        root = tk.Tk()
        root.withdraw()

        self.file_path = filedialog.askdirectory()

        timestr = time.strftime("%Y-%m-%d")  # -%H%M%S")

        newpath = self.file_path + "/" + timestr
        if not os.path.exists(newpath):
            os.makedirs(newpath)
        else:
            print("Ya existe esa carpeta")
        self.file_path = newpath
        self.form_widget.NameDirValue.setText(self.file_path)
        self.form_widget.NameDirValue.setStyleSheet(" background-color: ; ")

    def save_docks(self):
        self.form_widget.state = self.form_widget.dockArea.saveState()

    def load_docks(self):
        self.form_widget.dockArea.restoreState(self.form_widget.state)

    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.a = 0
        self.file_path = os.path.abspath("")
        self.setMinimumSize(QtCore.QSize(500, 500))
        self.setWindowTitle("PyPrintingPy")

    # Create new action
        openAction = QtGui.QAction(QtGui.QIcon('open.png'), '&Open Dir', self)
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip('Open document')
        openAction.triggered.connect(self.openCall)

    # Create exit action
        exitAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.exitCall)

    # Create de file location action
        localDirAction = QtGui.QAction(QtGui.QIcon('Dir.png'),
                                       '&Select Dir', self)
        localDirAction.setStatusTip('Select the work folder')
        localDirAction.setShortcut('Ctrl+S')
        localDirAction.triggered.connect(self.localDir)

    # Create de create daily directory action
        dailyAction = QtGui.QAction(QtGui.QIcon('algo.png'),
                                    '&Create daily Dir', self)
        dailyAction.setStatusTip('Create the work folder')
        dailyAction.setShortcut('Ctrl+D')
        dailyAction.triggered.connect(self.create_daily_directory)

    # Create de create daily directory action
        save_docks_Action = QtGui.QAction(QtGui.QIcon('algo.png'),
                                          '&Save Docks', self)
        save_docks_Action.setStatusTip('Saves the Actual Docks configuration')
        save_docks_Action.setShortcut('Ctrl+p')
        save_docks_Action.triggered.connect(self.save_docks)

    # Create de create daily directory action
        load_docks_Action = QtGui.QAction(QtGui.QIcon('algo.png'),
                                          '&Load Docks', self)
        load_docks_Action.setStatusTip('Load a previous Docks configuration')
        load_docks_Action.setShortcut('Ctrl+l')
        load_docks_Action.triggered.connect(self.load_docks)

    # Create menu bar and add action
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')
        fileMenu.addAction(localDirAction)
        fileMenu.addAction(openAction)
        fileMenu.addAction(dailyAction)
        fileMenu.addAction(exitAction)

        fileMenu2 = menuBar.addMenu('&APD')
        fileMenu2.addAction(save_docks_Action)
        fileMenu2.addAction(load_docks_Action)
#        fileMenu3 = menuBar.addMenu('&Local Folder')
#        fileMenu3.addAction(localDiraction)
        fileMenu4 = menuBar.addMenu('&<--Selecciono la carpeta desde aca!')

        self.form_widget = ScanWidget(self, device)
        self.setCentralWidget(self.form_widget)
        self.setGeometry(10, 40, 900, 600)  # (PosX, PosY, SizeX, SizeY)
        self.save_docks()

        
# %% ScanWidget
class ScanWidget(QtGui.QFrame):
    def imageplot(self):
        if self.imagecheck.isChecked():
            self.img.setImage(self.image2, autoLevels=self.autoLevels)
            self.imagecheck.setStyleSheet(" color: green; ")
            self.hist.gradient.loadPreset('flame')
        else:
            self.img.setImage(self.image, autoLevels=self.autoLevels)
            self.imagecheck.setStyleSheet(" color: red; ")
            self.hist.gradient.loadPreset('thermal')

    def graphplot(self):
        # if self.dy==0:
            # self.paramChanged()
        # self.getInitPos()
        self.paramChangedInitialize()

#        if self.graphcheck.isChecked():
#            if self.imagecheck.isChecked():
#                self.img.setImage(self.backimage2, autoLevels=self.autoLevels)
#            else:
#                self.img.setImage(self.backimage, autoLevels=self.autoLevels)
#        else:
#            self.img.setImage(self.image, autoLevels=self.autoLevels)

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

        plt.plot(verxi, '*-m')
        plt.plot(self.onerampx, 'b.-')
        plt.plot(verxchange, '.-g')
        plt.plot(verxback, '.-c')
        plt.plot(verxstops, '*-y')
        plt.plot(self.onerampy[0, :], 'k')
#        plt.plot(self.onerampy[1,:],'k')
        plt.show()

    def __init__(self, main, device, *args, **kwargs):  # agregue device

        super().__init__(*args, **kwargs)

        self.main = main
        self.nidaq = device  # esto tiene que ir

        imageWidget = pg.GraphicsLayoutWidget()
        self.vb = imageWidget.addViewBox(row=1, col=1)

    # Parameters for smooth moving (to no go hard on the piezo (or galvos))
        self.moveTime = 10 / 10**3  # total time to move (s ==>ms)
        self.moveSamples = 1000  # samples to move
        self.moveRate = self.moveSamples / self.moveTime  # 10**5

    # LiveView Button
        self.liveviewButton = QtGui.QPushButton('confocal LIVEVIEW')
        self.liveviewButton.setCheckable(True)
        self.liveviewButton.clicked.connect(self.liveview)
        self.liveviewButton.setStyleSheet(
                "QPushButton { background-color: green; }"
                "QPushButton:pressed { background-color: blue; }")
        self.liveviewButton.setToolTip('The magic begins')

        self.PSFMode = QtGui.QComboBox()
        self.PSFModes = ['XY normal psf', 'XZ', 'YZ']
        self.PSFMode.addItems(self.PSFModes)
        self.PSFMode.activated.connect(self.PSFYZ)
        self.PSFMode.setToolTip('Change the scan axes')

    # Presets for shutters
        self.presetsMode = QtGui.QComboBox()
        self.presetsModes = ['Red', 'Yellow', 'STED', 'STED + Yell',
                             'STED + Red', 'nada']
        self.presetsMode.addItems(self.presetsModes)
        self.presetsMode.setToolTip('Select the shutters to\
                                    open during the scan')

    # To save all images until stops
        self.VideoCheck = QtGui.QCheckBox('"video" save')
        self.VideoCheck.setChecked(False)
        self.VideoCheck.setToolTip('Save every finished image')

    # to run continuously
        self.Continouscheck = QtGui.QCheckBox('Continous')
        self.Continouscheck.setChecked(False)
        self.Continouscheck.setToolTip('Start again, and again, and again...')

    # to Calculate the mass center
        self.CMcheck = QtGui.QCheckBox('calcula CM')
#        self.CMcheck.setChecked(False)
        self.CMcheck.setCheckable(False)
        self.CMcheck.clicked.connect(self.CMmeasure)
        self.CMcheck.setToolTip('makes a basic measurement of\
                                the center of mass')

    # 2D Gaussian fit to estimate the center of a NP
        self.Gausscheck = QtGui.QCheckBox('Gauss fit')
#        self.Gausscheck.setChecked(False)
        self.Gausscheck.setCheckable(False)
        self.Gausscheck.clicked.connect(self.GaussFit)
        self.Gausscheck.setToolTip('makes 2D Gaussian fit of the image,\
                                   and give the center')

    # save image Button
        self.saveimageButton = QtGui.QPushButton('Save Frame')
        self.saveimageButton.setCheckable(False)
        self.saveimageButton.clicked.connect(self.saveFrame)
        self.saveimageButton.setStyleSheet(
                "QPushButton { background-color:  rgb(200, 200, 10); }"
                "QPushButton:pressed { background-color: blue; }")

        label_save = QtGui.QLabel('Tiff File Name')
        label_save.resize(label_save.sizeHint())
        self.edit_save = QtGui.QLineEdit('Test Image')
        self.edit_save.resize(self.edit_save.sizeHint())
        self.edit_save.setToolTip('Selec a name to save the image.\
              The name automatically changes to not replace the previous one')

        self.edit_Name = str(self.edit_save.text())
        self.edit_save.textEdited.connect(self.save_name_update)
        self.save_name_update()

#        self.NameDirButton = QtGui.QPushButton('Select Dir')
#        self.NameDirButton.clicked.connect(self.selectFolder)
#        filepath = main.file_path  # os.path.abspath("")
        self.file_path = os.path.abspath("")
        self.NameDirValue = QtGui.QLabel('')
        self.NameDirValue.setText(self.file_path)
        self.NameDirValue.setStyleSheet(" background-color: red; ")

#        self.OpenButton = QtGui.QPushButton('open dir')
#        self.OpenButton.clicked.connect(self.openFolder)
#        self.NameDirButton.setToolTip('Select the folder where it saves')
#        self.OpenButton.setToolTip('Open the folder where it saves')
#        self.create_day_Button = QtGui.QPushButton('Create daily dir')
#        self.create_day_Button.clicked.connect(self.create_daily_directory)
#        self.create_day_Button.setToolTip('Create a year-mon-day name folder')

    # Select the wanted scan mode
        self.scanMode = QtGui.QComboBox()
#        self.scanModes = ['ramp scan', 'step scan'...] se fue arriba
        self.scanMode.addItems(scanModes)
        self.scanMode.setToolTip('Selec the scan type.\
        With a voltage ramps or step by step')

    # Plot ramps scan button
        self.graphcheck = QtGui.QCheckBox('Scan Plot')
        self.graphcheck.clicked.connect(self.graphplot)
        self.step = False
        self.graphcheck.setToolTip('plot the voltage ramps (developer only)')

    # Plot ramps scan button
        self.imagecheck = QtGui.QCheckBox('Image change')
        self.imagecheck.clicked.connect(self.imageplot)
        self.imagecheck.setStyleSheet(" color: red; ")
        self.imagecheck.setToolTip('Switch between the images of each apd')

    # useful Booleans
        self.channelramp = False  # canales
        self.PMTon = False
        self.APDson = False
        self.triggerAPD = False  # separo los canales en partes
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

        self.GaussPlot = False
        self.CMplot = False

        self.shuttersChannelsNidaq()  # los prendo al principio y me olvido

    # autoLevel image
        self.autoLevelscheck = QtGui.QCheckBox('Auto escale (or not)')
        self.autoLevelscheck.setChecked(True)
        self.autoLevelscheck.clicked.connect(self.autoLevelset)
        self.autoLevelscheck.setToolTip('Switch between automatic \
                                        colorbar normalization, or manually')

    # Shutters buttons
        self.shutter0button = QtGui.QCheckBox('shutter Red')
        self.shutter0button.clicked.connect(self.shutter0)
        self.shutter1button = QtGui.QCheckBox('shutter STED')
        self.shutter1button.clicked.connect(self.shutter1)
        self.shutter2button = QtGui.QCheckBox('shutter Yellow')
        self.shutter2button.clicked.connect(self.shutter2)

        self.shutter0button.setToolTip('Open/close Red Shutter')
        self.shutter1button.setToolTip('Open/close STED Shutter')
        self.shutter2button.setToolTip('Open/close Yellow Shutter')

    # ploting image with matplotlib (slow). if Npix>500 is very slow
        self.plotLivebutton = QtGui.QPushButton('Plot this frame')
        self.plotLivebutton.setChecked(False)
        self.plotLivebutton.clicked.connect(self.plotLive)
        self.plotLivebutton.setToolTip('Plot this image with matplotlive')

    # Select the detector
        self.detectMode = QtGui.QComboBox()
#        self.detectModes = ['APD red', ...] ahora esta al principio
        self.detectMode.addItems(detectModes)
        self.detectMode.setCurrentIndex(2)
        self.detectMode.setToolTip('Select the detect instrument (APD or PMT)')

    # ROI buttons
        self.roi = None
        self.ROIButton = QtGui.QPushButton('ROI')
        self.ROIButton.setCheckable(True)
        self.ROIButton.clicked.connect(self.ROImethod)
        self.ROIButton.setToolTip('Create/erase a ROI box in the liveview')

        self.selectROIButton = QtGui.QPushButton('select ROI')
        self.selectROIButton.clicked.connect(self.selectROI)
        self.selectROIButton.setToolTip('go to the ROI selected coordenates')

    # ROI Histogram
        self.histogramROIButton = QtGui.QPushButton('Histogram ROI')
        self.histogramROIButton.setCheckable(True)
        self.histogramROIButton.clicked.connect(self.histogramROI)
        self.histogramROIButton.setToolTip('Visualize an histogram in \
                                           the selected ROI area')

    # ROI Lineal
        self.roiline = None
        self.ROIlineButton = QtGui.QPushButton('line ROI line')
        self.ROIlineButton.setCheckable(True)
        self.ROIlineButton.clicked.connect(self.ROIlinear)
        self.selectlineROIButton = QtGui.QPushButton('Plot line ROI')
        self.selectlineROIButton.clicked.connect(self.selectLineROI)

        self.ROIlineButton.setToolTip('Creates a linear ROI to \
                                      se linear intensities')
        self.selectlineROIButton.setToolTip('Make a plot with the linear\
                                            ROI intensities, for save')

    # Point scan
        self.PointButton = QtGui.QPushButton('Point scan')
        self.PointButton.setCheckable(False)
        self.PointButton.clicked.connect(self.PointStart)
        self.PointLabel = QtGui.QLabel('<strong>0.00|0.00')
        self.PointButton.setToolTip('continuously measures the APDs')

    # Max counts
        self.maxcountsLabel = QtGui.QLabel('Max Counts (red|green)')
        self.maxcountsEdit = QtGui.QLabel('<strong> 0|0')
        newfont = QtGui.QFont("Times", 14, QtGui.QFont.Bold)
        self.maxcountsEdit.setFont(newfont)

    # Scanning parameters
#        self.initialPositionLabel = QtGui.QLabel('Initial Pos [x0 y0 z0](µm)')
#        self.initialPositionEdit = QtGui.QLineEdit('0 0 1')
        self.scanRangeLabel = QtGui.QLabel('Scan range (µm)')
        self.scanRangeEdit = QtGui.QLineEdit('10')
        self.pixelTimeLabel = QtGui.QLabel('Pixel time (ms)')
        self.pixelTimeEdit = QtGui.QLineEdit('0.01')
        self.pixelTimeEdit.setToolTip('0.01 ms = 10 µs  :)')
#        self.accelerationLabel = QtGui.QLabel('puntos agregados ')
# Acceleration (µm/ms^2)')
#        self.accelerationEdit = QtGui.QLineEdit('3')
#        self.accelerationLabel.setToolTip('The aceleration of the \
#                                          ramps (developer only)')  # CAMBIO

        self.numberofPixelsLabel = QtGui.QLabel('Number of pixels')
        self.numberofPixelsEdit = QtGui.QLineEdit('500')
        self.pixelSizeLabel = QtGui.QLabel('Pixel size (nm)')
        self.pixelSizeValue = QtGui.QLineEdit('20')

        self.added_points_Label = QtGui.QLabel('puntos agregados ')
        self.added_points_Edit = QtGui.QLineEdit('3')
        self.added_points_Label.setToolTip('Added points to the \
                                          created ramps (developer only)')

        self.vueltaLabel = QtGui.QLabel('Back Velocity (relative)')
        self.vueltaEdit = QtGui.QLineEdit('10')
        self.vueltaLabel.setToolTip('The velocity of the back\
                                    ramps (developer only)')

        self.triggerLabel = QtGui.QLabel('Trigger ')
        self.triggerEdit = QtGui.QLineEdit('1')
        self.triggerLabel.setToolTip('addition a delay before\
                                     start (developer only)')

        self.timeTotalLabel = QtGui.QLabel('total scan time (s)')
#        self.timeTotalValue = QtGui.QLabel('')
        self.timeTotalLabel.setToolTip('Is an aproximate value')

        self.onlyInt = QtGui.QIntValidator(0, 10001)
        self.numberofPixelsEdit.setValidator(self.onlyInt)
        self.onlypos = QtGui.QDoubleValidator(0, 1000, 10)
        self.pixelTimeEdit.setValidator(self.onlypos)
        self.scanRangeEdit.setValidator(self.onlypos)

        self.numberofPixelsEdit.textEdited.connect(self.PixelSizeChange)
        self.pixelSizeValue.textEdited.connect(self.NpixChange)
        self.scanRangeEdit.textEdited.connect(self.PixelSizeChange)

        self.scanMode.activated.connect(self.SlalomMode)

        self.presetsMode.activated.connect(self.PreparePresets)

        self.paramWidget = QtGui.QWidget()

#        grid = QtGui.QGridLayout()
#        self.setLayout(grid)
#        grid.addWidget(imageWidget, 0, 0)
#        grid.addWidget(self.paramWidget, 0, 1)

        subgrid = QtGui.QGridLayout()
        self.paramWidget.setLayout(subgrid)

        self.paramWidget2 = QtGui.QWidget()
        subgrid2 = QtGui.QGridLayout()
        self.paramWidget2.setLayout(subgrid2)

        self.paramWidget3 = QtGui.QWidget()
        subgrid3 = QtGui.QGridLayout()
        self.paramWidget3.setLayout(subgrid3)

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
        subgrid.addWidget(self.Continouscheck,     12, 1)
        subgrid.addWidget(self.autoLevelscheck,    13, 1)
        subgrid.addWidget(self.imagecheck,         14, 1)
        subgrid.addWidget(self.maxcountsLabel,     15, 1)
        subgrid.addWidget(self.maxcountsEdit,      16, 2, 2, 1)

    # Columna 2
        subgrid2.addWidget(self.NameDirButton,       0, 2)
        subgrid2.addWidget(self.OpenButton,          1, 2)
        subgrid2.addWidget(self.create_day_Button,   2, 2)
#        subgrid2.addWidget(self.triggerLabel,        4, 2)
#        subgrid2.addWidget(self.triggerEdit,         5, 2)
#        subgrid2.addWidget(self.added_points_Label,   6, 2)
#        subgrid2.addWidget(self.added_points_Edit,    7, 2)
#        subgrid2.addWidget(self.vueltaLabel,         8, 2)
#        subgrid2.addWidget(self.vueltaEdit,          9, 2)
#        subgrid2.addWidget(QtGui.QLabel(""),         2, 2)
        subgrid2.addWidget(self.detectMode,          3, 2)
        subgrid2.addWidget(QtGui.QLabel(""),         4, 2)
#        subgrid2.addWidget(QtGui.QLabel(""),         5, 2)
#        subgrid2.addWidget(QtGui.QLabel(""),         6, 2)
        subgrid2.addWidget(QtGui.QLabel(""),         7, 2)
        subgrid2.addWidget(QtGui.QLabel(""),         8, 2)
        subgrid2.addWidget(self.VideoCheck,          9, 2)
        subgrid2.addWidget(QtGui.QLabel(""),        10, 2)
        subgrid2.addWidget(label_save,              11, 2)
        subgrid2.addWidget(self.edit_save,          12, 2)
        subgrid2.addWidget(self.saveimageButton,    13, 2)
        subgrid2.addWidget(QtGui.QLabel(""),        14, 2)
        subgrid2.addWidget(self.presetsMode,        15, 2)
        subgrid2.addWidget(self.timeTotalLabel,     16, 2)
#        subgrid2.addWidget(self.timeTotalValue,     17, 2)

    # Columna 3
#        subgrid.addWidget(self.algobutton,            0, 3)
        subgrid3.addWidget(self.ROIButton,            0, 3)
        subgrid3.addWidget(self.selectROIButton,      1, 3)
        subgrid3.addWidget(QtGui.QLabel(""),          2, 3)
        subgrid3.addWidget(self.ROIlineButton,        3, 3)
        subgrid3.addWidget(self.selectlineROIButton,  4, 3)
        subgrid3.addWidget(QtGui.QLabel(""),          5, 3)
        subgrid3.addWidget(self.histogramROIButton,   6, 3)
#        subgrid3.addWidget(QtGui.QLabel(""),          1, 3)
#        subgrid3.addWidget(QtGui.QLabel(""),          2, 3)
#        subgrid3.addWidget(QtGui.QLabel(""),          4, 3)
#        subgrid3.addWidget(QtGui.QLabel(""),          5, 3)
#        subgrid3.addWidget(QtGui.QLabel(""),          6, 3)
        subgrid3.addWidget(QtGui.QLabel(""),          7, 3)
        subgrid3.addWidget(QtGui.QLabel(""),          8, 3)
#        subgrid3.addWidget(QtGui.QLabel(""),          9, 3)
#        subgrid3.addWidget(self.ROIlineButton,        6, 3)
#        subgrid3.addWidget(self.selectlineROIButton,  7, 3)
        subgrid3.addWidget(self.PointButton,          9, 3)
        subgrid3.addWidget(self.PointLabel,          10, 3)
        subgrid3.addWidget(QtGui.QLabel(""),         11, 3)
        subgrid3.addWidget(self.graphcheck,          12, 3)
        subgrid3.addWidget(self.plotLivebutton,      13, 3)
        subgrid3.addWidget(QtGui.QLabel(""),         14, 3)
#        subgrid3.addWidget(self.CMcheck,             12, 3)
#        subgrid.addWidget(self.Gausscheck,           13, 3)
        subgrid3.addWidget(self.scanMode,            15, 3)
        subgrid3.addWidget(self.PSFMode,             16, 3)

# ---  Positioner part ---------------------------------
        # Axes control
        self.xLabel = QtGui.QLabel('-5.0')
        self.xLabel.setTextFormat(QtCore.Qt.RichText)
        self.xname = QtGui.QLabel("<strong>x =")
        self.xname.setTextFormat(QtCore.Qt.RichText)
        self.xUpButton = QtGui.QPushButton("(+x) ►")  # →
        self.xUpButton.pressed.connect(self.xMoveUp)
        self.xDownButton = QtGui.QPushButton("◄ (-x)")  # ←
        self.xDownButton.pressed.connect(self.xMoveDown)
        self.xStepEdit = QtGui.QLineEdit("1")
        self.xStepUnit = QtGui.QLabel(" µm")

        self.yLabel = QtGui.QLabel('-5.0')
        self.yLabel.setTextFormat(QtCore.Qt.RichText)
        self.yname = QtGui.QLabel("<strong>y =")
        self.yname.setTextFormat(QtCore.Qt.RichText)
        self.yUpButton = QtGui.QPushButton("(+y) ▲")  # ↑
        self.yUpButton.pressed.connect(self.yMoveUp)
        self.yDownButton = QtGui.QPushButton("(-y) ▼")  # ↓
        self.yDownButton.pressed.connect(self.yMoveDown)
        self.yStepEdit = QtGui.QLineEdit("1")
        self.yStepUnit = QtGui.QLabel(" µm")

        self.zLabel = QtGui.QLabel('5.0')
        self.zLabel.setTextFormat(QtCore.Qt.RichText)
        self.zname = QtGui.QLabel("<strong>z =")
        self.zname.setTextFormat(QtCore.Qt.RichText)
        self.zUpButton = QtGui.QPushButton("+z ▲")
        self.zUpButton.pressed.connect(self.zMoveUp)
        self.zDownButton = QtGui.QPushButton("-z ▼")
        self.zDownButton.pressed.connect(self.zMoveDown)
        self.zStepEdit = QtGui.QLineEdit("1")
        self.zStepUnit = QtGui.QLabel(" µm")

        self.positioner = QtGui.QWidget()
#        grid.addWidget(self.positioner, 1, 0)
        layout = QtGui.QGridLayout()
        self.positioner.setLayout(layout)
        layout.addWidget(self.xname,       1, 0)
        layout.addWidget(self.xLabel,      1, 1)
        layout.addWidget(self.xUpButton,   2, 4, 2, 1)
        layout.addWidget(self.xDownButton, 2, 2, 2, 1)
#        layout.addWidget(QtGui.QLabel("Step x"), 1, 6)
#        layout.addWidget(self.xStepEdit, 1, 7)
#        layout.addWidget(self.xStepUnit, 1, 8)

        layout.addWidget(self.yname,       2, 0)
        layout.addWidget(self.yLabel,      2, 1)
        layout.addWidget(self.yUpButton,   1, 3, 2, 1)
        layout.addWidget(self.yDownButton, 3, 3, 2, 1)
        layout.addWidget(QtGui.QLabel("Length of step xy"), 1, 6)
        layout.addWidget(self.yStepEdit,   2, 6)
        layout.addWidget(self.yStepUnit,   2, 7)

        layout.addWidget(self.zname,       4, 0)
        layout.addWidget(self.zLabel,      4, 1)
        layout.addWidget(self.zUpButton,   1, 5, 2, 1)
        layout.addWidget(self.zDownButton, 3, 5, 2, 1)
        layout.addWidget(QtGui.QLabel("Length of step z"), 3, 6)
        layout.addWidget(self.zStepEdit,   4, 6)
        layout.addWidget(self.zStepUnit,   4, 7)

        layout.addWidget(self.NameDirValue, 8, 0, 1, 7)

        tamaño = 40
        self.yStepEdit.setFixedWidth(tamaño)
        self.zStepEdit.setFixedWidth(tamaño)
#        self.yStepEdit.setValidator(self.onlypos)
#        self.zStepEdit.setValidator(self.onlypos)

        self.gotoWidget = QtGui.QWidget()
#        grid.addWidget(self.gotoWidget, 1, 1)
        layout2 = QtGui.QGridLayout()
        self.gotoWidget.setLayout(layout2)
        layout2.addWidget(QtGui.QLabel("X"), 1, 1)
        layout2.addWidget(QtGui.QLabel("Y"), 2, 1)
        layout2.addWidget(QtGui.QLabel("Z"), 3, 1)
        self.xgotoLabel = QtGui.QLineEdit("0")
        self.ygotoLabel = QtGui.QLineEdit("0")
        self.zgotoLabel = QtGui.QLineEdit("0")
        self.gotoButton = QtGui.QPushButton("♫ G0 To ♪")
        self.gotoButton.pressed.connect(self.goto)
        layout2.addWidget(self.gotoButton, 1, 3, 2, 2)
        layout2.addWidget(self.xgotoLabel, 1, 2)
        layout2.addWidget(self.ygotoLabel, 2, 2)
        layout2.addWidget(self.zgotoLabel, 3, 2)
        self.zgotoLabel.setValidator(self.onlypos)
#        tamaño = 50
        self.xgotoLabel.setFixedWidth(tamaño)
        self.ygotoLabel.setFixedWidth(tamaño)
        self.zgotoLabel.setFixedWidth(tamaño)

        layout3 = QtGui.QGridLayout()
        self.goCMWidget = QtGui.QWidget()
        self.goCMWidget.setLayout(layout3)
        self.CMxLabel = QtGui.QLabel('CM X')
        self.CMxValue = QtGui.QLabel('NaN')
        self.CMyLabel = QtGui.QLabel('CM Y')
        self.CMyValue = QtGui.QLabel('NaN')
        layout3.addWidget(self.CMxLabel, 3, 1)
        layout3.addWidget(self.CMxValue, 4, 1)
        layout3.addWidget(self.CMyLabel, 3, 2)
        layout3.addWidget(self.CMyValue, 4, 2)
        self.goCMButton = QtGui.QPushButton("♠ Go CM ♣")
        self.goCMButton.pressed.connect(self.goCM)
        layout3.addWidget(self.goCMButton, 1, 4)  # , 2, 2)
        layout3.addWidget(self.CMcheck, 1, 1)

        self.GaussxLabel = QtGui.QLabel('Gauss X')
        self.GaussxValue = QtGui.QLabel('NaN')
        self.GaussyLabel = QtGui.QLabel('Gauss Y')
        self.GaussyValue = QtGui.QLabel('NaN')
        layout3.addWidget(self.GaussxLabel, 3, 4)
        layout3.addWidget(self.GaussxValue, 4, 4)
        layout3.addWidget(self.GaussyLabel, 3, 5)
        layout3.addWidget(self.GaussyValue, 4, 5)
#        layout3.addWidget(QtGui.QLabel(' '), 4, 4)
        self.goCMButton = QtGui.QPushButton("♥ Go Gauss ♦")
        self.goCMButton.pressed.connect(self.goGauss)
        layout3.addWidget(self.goCMButton, 2, 4)  # , 2, 2)
        layout3.addWidget(self.Gausscheck, 2, 1)
# ---- fin positioner part----------

#        saveBtn = QtGui.QPushButton('Save dock state')
#        restoreBtn = QtGui.QPushButton('Restore dock state')
#        restoreBtn.setEnabled(False)
#        subgrid2.addWidget(saveBtn,    5, 2)
#        subgrid2.addWidget(restoreBtn, 6, 2)

        self.state = None

# ----DOCK cosas, mas comodo!
        hbox = QtGui.QHBoxLayout(self)
        dockArea = DockArea()

        viewDock = Dock('viewbox', size=(500, 450))
        viewDock.addWidget(imageWidget)
        viewDock.hideTitleBar()
        dockArea.addDock(viewDock, 'left')

        self.otrosDock = Dock('Other things', size=(1, 1))
#        self.otrosDock.addWidget(HistoWidget)
        dockArea.addDock(self.otrosDock, 'bottom')

        posDock = Dock('positioner', size=(1, 1))
        posDock.addWidget(self.positioner)
        dockArea.addDock(posDock, 'above', self.otrosDock)

        goCMDock = Dock('Cm and Gauss', size=(1, 1))
        goCMDock.addWidget(self.goCMWidget)
        dockArea.addDock(goCMDock, 'right', posDock)

        gotoDock = Dock('goto', size=(1, 1))
        gotoDock.addWidget(self.gotoWidget)
        dockArea.addDock(gotoDock, 'above', goCMDock)

        scanDock3 = Dock('ROI Things', size=(1, 1))
        scanDock3.addWidget(self.paramWidget3)
        dockArea.addDock(scanDock3, 'right')

        scanDock2 = Dock('Other parameters', size=(1, 1))
        scanDock2.addWidget(self.paramWidget2)
        dockArea.addDock(scanDock2, 'above', scanDock3)

        scanDock = Dock('Scan parameters', size=(1, 1))
        scanDock.addWidget(self.paramWidget)
        dockArea.addDock(scanDock, 'left', scanDock2)

        hbox.addWidget(dockArea)
        self.setLayout(hbox)
#        self.setGeometry(10, 40, 300, 800)
#        self.setWindowTitle('Py Py Python scan')
#        self.setFixedHeight(550)

        self.paramChanged()
        self.PixelSizeChange()
#        self.paramWidget.setFixedHeight(500)

        self.vb.setMouseMode(pg.ViewBox.RectMode)
        self.img = pg.ImageItem()
        self.img.translate(-0.5, -0.5)
        self.vb.addItem(self.img)
        self.vb.setAspectLocked(True)
        imageWidget.setAspectLocked(True)
        self.hist = pg.HistogramLUTItem(image=self.img)
        self.hist.gradient.loadPreset('thermal')
# 'thermal', 'flame', 'yellowy', 'bipolar', 'spectrum',
# 'cyclic', 'greyclip', 'grey' # Solo son estos
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

#        self.blankImage = np.zeros((self.numberofPixels, self.numberofPixels))
#        self.image = np.zeros((self.numberofPixels, self.numberofPixels))
#        self.image2 = np.zeros((self.numberofPixels, self.numberofPixels))
        self.zeroImage()
        self.dy = 0

        self.imageWidget = imageWidget

        # self.startRutine()
        # TODO: # que lea de algun lado la posicion y la setee como start x,y,z

    # Agrego un atajo para que empieze tocando Ctrl+a
        self.liveviewAction = QtGui.QAction(self)
        self.liveviewAction.setShortcut('Ctrl+a')
        QtGui.QShortcut(
            QtGui.QKeySequence('Ctrl+a'), self, self.liveviewKey)
#        self.liveviewAction.triggered.connect(self.liveviewKey)
        self.liveviewAction.setEnabled(False)

        self.PreparePresets()
        self.dockArea = dockArea

# %% Un monton de pequeñas cosas que agregé
    def liveviewKey(self):
        '''Triggered by the liveview shortcut.'''
        if self.liveviewButton.isChecked():
            self.liveviewStop()
            self.liveviewButton.setChecked(False)
        else:
            self.liveviewButton.setChecked(True)
            self.liveview()
#            self.liveviewStart()

    def autoLevelset(self):
        if self.autoLevelscheck.isChecked():
            self.autoLevels = True
        else:
            self.autoLevels = False

    def PSFYZ(self):
        if self.PSFMode.currentText() == self.PSFModes[0]:
            self.YZ = False
        else:
            self.YZ = True

    def SlalomMode(self):
        if self.scanMode.currentText() == "slalom":
            self.vueltaEdit.setText("1")
            self.vueltaEdit.setStyleSheet(" background-color: red; ")
        else:
            self.vueltaEdit.setText("10")
            self.vueltaEdit.setStyleSheet("{ background-color: }")

    def zeroImage(self):
        self.blankImage = np.zeros((self.numberofPixels, self.numberofPixels))
        self.image = np.copy(self.blankImage)
        self.image2 = np.copy(self.blankImage)

    def PixelSizeChange(self):
        scanRange = float(self.scanRangeEdit.text())
        numberofPixels = int(self.numberofPixelsEdit.text())
        self.pixelSize = scanRange/numberofPixels
        self.pixelSizeValue.setText('{}'.format(
                                    np.around(1000 * self.pixelSize, 2)))
        pixelTime = float(self.pixelTimeEdit.text()) / 10**3
        pixelTime = float(self.pixelTimeEdit.text()) / 10**3
        self.timeTotalLabel.setText("Tiempo total (s) = " + '{}'.format(
                                  np.around(numberofPixels**2 * pixelTime, 2)))

    def NpixChange(self):
        scanRange = float(self.scanRangeEdit.text())
        pixelSize = float(self.pixelSizeValue.text())/1000
        self.numberofPixelsEdit.setText('{}'.format(int(scanRange/pixelSize)))
        pixelTime = float(self.pixelTimeEdit.text()) / 10**3
        self.timeTotalLabel.setText("Tiempo total (s) = " + '{}'.format(
                                np.around(
                                  int(scanRange/pixelSize)**2 * pixelTime, 2)))

# %%--- paramChanged / PARAMCHANGEDinitialize
    def paramChangedInitialize(self):
        """ update de parameters only if something change"""
        tic = ptime.time()

        a = [self.scanRange,
             self.numberofPixels,
             self.pixelTime,
             self.initialPosition,
             self.scanModeSet,
             self.PSFModeSet,
             self.ptsamano,
             self.Vback]

        b = [float(self.scanRangeEdit.text()),
             int(self.numberofPixelsEdit.text()),
             float(self.pixelTimeEdit.text()) / 10**3,
             (float(self.xLabel.text()), float(self.yLabel.text()),
              float(self.zLabel.text())),
             self.scanMode.currentText(),
             self.PSFMode.currentText(),
             int(self.added_points_Edit.text()),
             float(self.vueltaEdit.text())]

        print("\n", a)
        print(b, "\n")
        if a != b:
            self.paramChanged()

        toc = ptime.time()
        print("tiempo paramchangeInitailize (ms)", (toc-tic)*10**3, "\n")

    def paramChanged(self):
        tic = ptime.time()

        self.GaussPlot = False
        self.CMplot = False

        self.scanModeSet = self.scanMode.currentText()
        self.PSFModeSet = self.PSFMode.currentText()
        self.ptsamano = int(self.added_points_Edit.text())
        self.Vback = float(self.vueltaEdit.text())

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
        # print(self.Napd, "=Napd\n")

        self.pixelSize = self.scanRange / self.numberofPixels

        self.pixelSizeValue.setText('{}'.format(np.around(
                                        1000 * self.pixelSize, 2)))  # en nm

        self.linetime = self.pixelTime * self.numberofPixels  # en s

#        #print(self.linetime, "linetime")

#        self.timeTotalValue.setText('{}'.format(np.around(
#                         self.numberofPixels * self.linetime, 2)))

        self.timeTotalLabel.setText("Time total(s) ~ " + '{}'.format(np.around(
                        2 * self.numberofPixels * self.linetime, 2)))

        if self.scanMode.currentText() == scanModes[1]:  # "step scan":
            # en el caso step no hay frecuencias
            # print("Step time, very slow")
            self.Steps()
#            # print(self.linetime, "linetime\n")

        else:
            rango = self.scanRange
            if self.scanMode.currentText() == scanModes[2]:  # "full fre ramp":
                self.sampleRate = (rango / resolucionDAQ) / (self.linetime)
                self.nSamplesrampa = int(np.ceil(rango / resolucionDAQ))
#                print("a full resolucion\n", self.nSamplesrampa,
#                      "Nsamples", self.sampleRate, "sampleRate")

            else:  # ramp y slalom
                self.nSamplesrampa = self.numberofPixels
                self.sampleRate = np.round(1 / self.pixelTime, 9)
#                print("los Nsamples = Npix y 1/tpix la frecuencia\n",
#                self.nSamplesrampa, "Nsamples", self.sampleRate, "sampleRate")
            self.Ramps()
            self.reallinetime = len(self.onerampx) * self.pixelTime  # seconds
            # print(self.linetime, "linetime")
            print(self.reallinetime, "reallinetime\n")
            self.PMT = np.zeros(len(self.onerampx))
        # print(self.linetime, "linetime\n")

#        self.autoLevels = True
        self.zeroImage()
        # numberofpixels is the relevant part of the total ramp.
        self.APD = np.zeros((
                     self.numberofPixels + self.pixelsofftotal) * self.Napd)
        self.APD2 = np.copy(self.APD)
        self.APDstep = np.zeros((self.Napd+1))

        toc = ptime.time()
        print("\n tiempo paramCahnged (ms)", (toc-tic)*10**3, "\n")
#        self.PMT = np.zeros((self.numberofPixels + self.pixelsofftotal,
#                              self.numberofPixels))
        self.maxcountsEdit.setStyleSheet("{ background-color: }")


# %%--- liveview------
# This is the function triggered by pressing the liveview button
    def liveview(self):
        if self.liveviewButton.isChecked():
            """if dy != 0:  # aca prentendia poner la parte con lectura de ai
#            """
            print("---------------------------------------------------------")
#            self.openShutter("red")
            self.paramChangedInitialize()
            self.MovetoStart()  # getini: se va
            self.liveviewStart()
        else:
            self.liveviewStop()

    def liveviewStart(self):
        # self.working = True
        # self.paramChangedInitialize()
        if self.scanMode.currentText() == scanModes[1]:  # "step scan":
            self.channelsOpenStep()
#            self.inStart = False
            self.tic = ptime.time()
            self.steptimer.start(5)  # 100*self.pixelTime*10**3)  # imput in ms
        else:  # "ramp scan" or "otra frec ramp" or slalom
            self.channelsOpenRamp()
            self.tic = ptime.time()
            self.startingRamps()
            self.maxcountsEdit.setStyleSheet("{ background-color: }")
            if self.detectMode.currentText() == "PMT":
                self.maxcountsLabel.setText('Max Counts (V)')
                self.PMTtimer.start(self.reallinetime*10**3)  # imput in ms
            else:
                self.maxcountsLabel .setText('Max Counts (red|green)')
                self.viewtimer.start(self.reallinetime*10**3)  # imput in ms

    def liveviewStop(self):
        self.MovetoStart()
        # print("liveStop")
        self.liveviewButton.setChecked(False)
        self.viewtimer.stop()
        self.steptimer.stop()
        self.PMTtimer.stop()
#        self.closeShutter("red")
        self.closeAllShutters()
        self.done()
        print("-----------------------------------------------------------")

#    def startingSteps(self):

# %%
    def startingRamps(self):
        """ Send the signals to the NiDaq,
        but only start when the trigger is on """
        if self.YZ:
            self.aotask.write(np.array(
                [self.totalrampx / convFactors['x'],
                 self.totalrampy / convFactors['y'],
                 self.totalrampz / convFactors['z']]), auto_start=True)
        else:
            self.aotask.write(np.array(
                [self.totalrampx / convFactors['x'],
                 self.totalrampy / convFactors['y']]), auto_start=True)

        if self.detectMode.currentText() != "PMT":
            self.APD1task.start()
            self.APD2task.start()
        else:
            self.PMTtask.start()

        print("ya arranca...")
        self.Presets()  # abre los shutters que sean

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
        elif self.detectMode.currentText() == detectModes[2]:
            # print("se viene!")
            (self.APD, self.APD2) = (self.APD1task.read((
                       (self.numberofPixels + self.pixelsofftotal)*self.Napd)),
                self.APD2task.read((
                       (self.numberofPixels + self.pixelsofftotal)*self.Napd)))
#        elif self.detectMode .currentText() == detectModes[-1]:
#            print("algo salio muy mal. entró a APDupdate, con la opcion PMT")

        # have to analize the signal from the counter
        self.apdpostprocessing()

        self.image[:, -1-self.dy] = self.counts[:]
        # + np.random.rand(self.numberofPixels)[:] # f

        """ verificar si Slalom es mas rapido que normal"""
        if self.scanMode.currentText() == scanModes[-1]:  # "slalom":
            self.image[:, -2-self.dy] = (self.backcounts[:])
            paso = 2
        else:
            self.backimage[:, -1-self.dy] = self.backcounts[:]  # np.flip(,0)

        self.image2[:, -1-self.dy] = self.counts2[:]
        # + 50*np.random.rand(self.numberofPixels)[:] # f
        self.backimage2[:, -1-self.dy] = self.backcounts2[:]

    # The plotting method is slow (2-3 ms each, for 500x500 pix)
    # , don't know how to do it fast
    # , so I´m plotting in packages. It's looks like realtime
#        if self.numberofPixels >= 500:
#            multi5 = np.arange(0, self.numberofPixels, 15)
        if self.numberofPixels >= 200:
            multi5 = np.arange(0, self.numberofPixels+1, 10)
        else:
            multi5 = np.arange(0, self.numberofPixels+1, 2)
        multi5[-1] = self.numberofPixels-1

        if self.dy in multi5:
            if self.imagecheck.isChecked():
                self.img.setImage(self.image2, autoLevels=self.autoLevels)
            else:
                self.img.setImage(self.image, autoLevels=self.autoLevels)
            self.MaxCounts()

        if self.dy < self.numberofPixels-paso:
            self.dy = self.dy + paso
        else:
            self.closeAllShutters()
            if self.VideoCheck.isChecked():
                self.saveFrame()  # para guardar siempre (Alan idea)
            print(ptime.time()-self.tic, "Tiempo imagen completa.")
            self.viewtimer.stop()
            self.triggertask.stop()
            self.aotask.stop()
            self.APDstop()
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

# %% MAX Counts
    def MaxCounts(self):
        m = np.max(self.image)
        m2 = np.max(self.image2)
        self.maxcountsEdit.setText("<strong> {}|{}".format(int(m), int(m2)))
        maxsecure = (5000 * self.pixelTime*10**3)
        if m >= maxsecure or m2 >= maxsecure:
            self.maxcountsEdit.setStyleSheet(" background-color: red; ")


# %% runing Ramp loop (PMT)
    def PMTupdate(self):
        paso = 1
    # The counter will reads this numbers of points when the trigger starts
        self.PMT[:] = self.PMTtask.read(len(self.onerampx))

    # limpio la parte acelerada.
        pixelsEnd = len(self.xini[:-1]) + self.numberofPixels
        self.image[:, -1-self.dy] = self.PMT[len(self.xini[:-1]):pixelsEnd]

        pixelsIniB = pixelsEnd+len(self.xchange[1:-1])
        if self.scanMode.currentText() == scanModes[-1]:  # "slalom":
            self.image[:, -2-self.dy] = (self.PMT[pixelsIniB:-
                                                  len(self.xstops[1:])])
            paso = 2
        else:
            self.backimagePMT[:, -1-self.dy] = self.PMT[pixelsIniB:-
                                                        len(self.xstops[1:])]
        self.MaxPMT()
    # The plotting method is slow (2-3 ms each, for 500x500 pix)
    # , don't know how to do it fast
    # , so I´m plotting in packages. It's looks like realtime
#        if self.numberofPixels >= 1000:  # (self.pixelTime*10**3) <= 0.5:
#            multi5 = np.arange(0, self.numberofPixels+1, 20)
        if self.numberofPixels >= 101:
            multi5 = np.arange(0, self.numberofPixels+1, 10)
        else:
            multi5 = np.arange(0, self.numberofPixels+1, 2)
        multi5[-1] = self.numberofPixels-1

        if self.dy in multi5:
            self.img.setImage(self.image, autoLevels=self.autoLevels)
#            if self.graphcheck.isChecked():
#                self.img.setImage(self.backimagePMT, autoLevels=self.autoLeve
#            else:
#                self.img.setImage(self.image, autoLevels=self.autoLevels)

        if self.dy < self.numberofPixels-paso:
            self.dy = self.dy + paso
        else:
            self.closeAllShutters()
            if self.VideoCheck.isChecked():
                self.saveFrame()  # para guardar siempre (Alan idea)
            print(ptime.time()-self.tic, "Tiempo imagen completa.")
            self.PMTtimer.stop()
            self.triggertask.stop()
            self.aotask.stop()
            self.PMTtask.stop()
            self.MovetoStart()
            if self.Continouscheck.isChecked():
                self.liveviewStart()
            else:
                self.liveviewStop()

# %% MAX PMT
    def MaxPMT(self):
        m = np.max(self.image)
#        m2 = np.max(self.backimagePMT)  # ,float(m2)))
        self.maxcountsEdit.setText("<strong> {0:.2}".format(float(m)))
        if m >= 1:  # or m2 >= 1:
            self.maxcountsEdit.setStyleSheet(" background-color: red; ")

# %% --- Creating Ramps  ----
    def Ramps(self):
        tic = ptime.time()
    # arma los barridos con los parametros dados
        self.counts = np.zeros((self.numberofPixels))
        self.counts2 = np.zeros((self.numberofPixels))  # self.counts

        self.acceleration()
        self.backcounts = np.zeros((self.pixelsoffB))
        self.backcounts2 = np.zeros((self.pixelsoffB))  # self.backcounts
        self.backimage = np.zeros((self.pixelsoffB, self.numberofPixels))
        self.backimage2 = np.copy(self.backimage)
        self.backimagePMT = np.zeros((len(self.xback[:]), self.numberofPixels))

#    Barrido x
        startX = float(self.initialPosition[0])

        Npuntos = self.nSamplesrampa  # self.numberofPixels  #
        wantedrampx = np.linspace(0, self.scanRange, Npuntos)
        + self.xini[-1] - (self.scanRange / 2)

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
        rampay = np.ones(len(self.onerampx))*startY - (self.scanRange/2)

        muchasrampasy = np.tile(rampay, (self.numberofPixels, 1))
        self.onerampy = np.zeros((self.numberofPixels, len(rampay)))

        if self.scanMode.currentText() == scanModes[-1]:  # "slalom":
            fast = 2  # Gotta go fast
        else:
            fast = 1  # not fast

        p = len(self.xini[:-1]) + len(wantedrampx)
        self.p = p
        for i in range(self.numberofPixels):
            j = fast*i
            self.onerampy[i, :p] = muchasrampasy[i, :p] + (j) * stepy
            self.onerampy[i, p:] = muchasrampasy[i, p:] + (j+1) * stepy

        self.totalrampy = (self.onerampy.ravel())

#        if self.PSFMode.currentText() == 'XY normal psf':
#            # print("escaneo x y normal R")
        if self.PSFMode.currentText() == 'XZ':
            # print("intercambio y por z R")
            self.totalrampz = self.totalrampy - startY + startZ
            self.totalrampy = np.ones(len(self.totalrampx)) * startY

        elif self.PSFMode.currentText() == 'YZ':
            # print("intercambio x por z R")
            self.totalrampz = self.totalrampy - startY + startZ
            self.totalrampy = self.totalrampx - startX + startY
            self.totalrampx = np.ones(len(self.totalrampx)) * startX

        toc = ptime.time()
        print("\n tiempo Ramps (ms)", (toc-tic)*10**3, "\n")

# %% posptocessing APD signal
    def apdpostprocessing(self):
        """ takes the evergrowing valors from the counter measure and convert
        it into "number or events" """
#        tic = ptime.time()
        Napd = self.Napd

#        j = self.dy

        if self.pixelsoffL == 0:
            self.counts[0] = self.APD[Napd-1] - self.APD[0]
            self.counts2[0] = self.APD2[Napd-1] - self.APD2[0]

        else:
            self.counts[0] = self.APD[(Napd*(1+self.pixelsoffL))-1]\
                             - self.APD[(Napd*(self.pixelsoffL))-1]
            self.counts2[0] = self.APD2[(Napd*(1+self.pixelsoffL))-1]\
                - self.APD2[(Napd*(1+self.pixelsoffL-1))-1]

#        self.counts[0] = 0
#        self.counts[0:5] = 5  # probando cosas

        for i in range(1, self.numberofPixels):
            ei = ((self.pixelsoffL+i) * Napd)-1
            ef = ((self.pixelsoffL+i+1) * Napd)-1
            self.counts[i] = self.APD[ef] - self.APD[ei]
            self.counts2[i] = self.APD2[ef] - self.APD2[ei]
        # Lo que sigue esta en creacion, para la imagen de vuelta

        for i in range(len(self.backcounts)):  # len(back...)= pixelsoffB
            evi = (-(self.pixelsoffR + self.pixelsoffB) + (i)) * Napd
            evf = (-(self.pixelsoffR + self.pixelsoffB) + (i+1)) * Napd
#            evi = ((self.pixelsoffR + i + 1) * Napd)
#            evf = ((self.pixelsoffR + i) * Napd)
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
# #     Lo que sigue esta en creacion, para la imagen de vuelta
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
        acceleration = (200*self.scanRange) / (
                                (self.numberofPixels*self.pixelTime*10**3)**2)

        startX = float(self.initialPosition[0])
        ptsamano = self.ptsamano  # int(self.accelerationEdit.text())

        ti = velocity / acceleration
        xipuntos = int(np.ceil(ti * rate)) + ptsamano

        xini = np.zeros(xipuntos)
        tiempoi = np.linspace(0, ti, xipuntos)
        for i in range(xipuntos):
            xini[i] = 0.5*acceleration*(((tiempoi[i])**2-(tiempoi[-1]**2))
                                        ) + startX

        xr = xini[-1] + self.scanRange
#        tr = T + ti

        Vback = self.Vback  # float(self.vueltaEdit.text())  # /V

    # impongo una velocidad de vuelta Vback veces mayor a la de ida
        tcasi = ((1+Vback) * velocity) / acceleration  # -a*t + V = -Vback*V
        xchangepuntos = int(np.ceil(tcasi * rate)) + ptsamano
        tiempofin = np.linspace(0, tcasi, xchangepuntos)
        xchange = np.zeros(xchangepuntos)
        for i in range(xchangepuntos):
            xchange[i] = (-0.5*acceleration*((tiempofin[i])**2) +
                          velocity * (tiempofin[i])) + xr

    # After the wanted ramp, it get a negative acceleration:
        av = acceleration
        tlow = Vback*velocity/av
        xlow = 0.5*av*(tlow**2) + startX
        Nvuelta = abs(int(np.round(
                           ((xchange[-1]-xlow)/(Vback*velocity)) * (rate))))

    # To avoid wrong going back in x
        if xchange[-1] < xlow:
            if xchange[-1] < startX:
                q = np.where(xchange <= startX)[0][0]
                xchange = xchange[:q]
                print("! xchange < 0")
                self.xback = np.linspace(0, 0, 4) + startX
                # lo creo para que no tire error nomas

            else:
                q = np.where(xchange <= xlow)[0][0]
                xchange = xchange[:q]
                self.xback = np.linspace(xlow, startX, Nvuelta)
                print("! xchange < xlow")
            xstops = np.linspace(0, 0, 2) + startX
        else:

            self.xback = np.linspace(xchange[-1], xlow, Nvuelta)

            xlowpuntos = int(np.ceil(tlow * rate)) + ptsamano
            tiempolow = np.linspace(0, tlow, xlowpuntos)
            # print("acceleration ok")
            xstops = np.zeros(xlowpuntos)
            for i in range(xlowpuntos):
                xstops[i] = 0.5*(av)*(tiempolow[i]**2) + startX

            xstops = np.flip(xstops, axis=0)
        # print("\n")

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
        suma = self.pixelsoffL+self.pixelsoffM+self.pixelsoffB+self.pixelsoffR
        print("pixelsofftotal", self.pixelsofftotal, "\n pixelsoff Suma", suma)
        # Si no dan lo mismo, puedo tener problemas

# %% --- ChannelsOpen (todos)
    def channelsOpen(self):
        if self.scanMode.currentText() == scanModes[1]:  # "step scan":
            self.channelsOpenStep()
        else:
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
            print("Ya estaban abiertos los canales rampa")  # to dont opn again
        else:
            if self.piezosteps:
                self.aotask.stop()
                self.aotask.close()
                # print("cierro auque no es necesario")
        # Create the channels
            self.aotask = nidaqmx.Task('aotask')
            if self.YZ:
                AOchans2 = [0, 1, 2]
            else:
                AOchans2 = AOchans
        # Following loop creates the voltage channels
            for n in range(len(AOchans2)):
                self.aotask.ao_channels.add_ao_voltage_chan(
                    physical_channel='Dev1/ao%s' % AOchans2[n],
                    name_to_assign_to_channel='chan_%s' % activeChannels[n],
                    min_val=minVolt[activeChannels[n]],
                    max_val=maxVolt[activeChannels[n]])

            self.piezoramp = True
            self.aotask.timing.cfg_samp_clk_timing(
                rate=self.sampleRate,
                # source=r'100kHzTimeBase',
                sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                samps_per_chan=len(self.totalrampx))

    def PiezoOpenStep(self):
        if self.piezosteps:
            print("Ya estaban abiertos los canales steps")  # to dont opn again
        else:
            if self.piezoramp:
                self.aotask.stop()
                self.aotask.close()
                # print("cierro para abrir de nuevo")
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
        else:
            # if self.PMTon:
                # print("ojo que sigue preparado el PMT (solo aviso)")
            self.APDson = True
            self.APD1task = nidaqmx.Task('APD1task')

            # Configure the counter channel to read the APD
            self.APD1task.ci_channels.add_ci_count_edges_chan(
                                counter='Dev1/ctr{}'.format(COchans[0]),
                                name_to_assign_to_channel=u'conter_RED',
                                initial_count=0)
            if self.scanMode.currentText() == scanModes[1]:  # "step scan":
                totalcinumber = self.Napd + 1
            else:
                totalcinumber = ((self.numberofPixels+self.pixelsofftotal) *
                                 self.Napd)*self.numberofPixels

            self.APD1task.timing.cfg_samp_clk_timing(
              rate=self.apdrate,
              sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
              source=r'100kHzTimebase',  # 1000k
              samps_per_chan=totalcinumber)

            self.APD2task = nidaqmx.Task('APD2task')

            # Configure the counter channel to read the APD
            self.APD2task.ci_channels.add_ci_count_edges_chan(
                                counter='Dev1/ctr{}'.format(COchans[1]),
                                name_to_assign_to_channel=u'conter_GREEN',
                                initial_count=0)

            self.APD2task.timing.cfg_samp_clk_timing(
              rate=self.apdrate,
              sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
              source=r'100kHzTimebase',
              samps_per_chan=totalcinumber)

            self.totalcinumber = totalcinumber

    def PMTOpen(self):
        if self.PMTon:
            print("Ya esta el PMT")  # to dont open again
        else:
            # if self.APDson:
                # print("ojo que sigue preparado el APD (solo aviso)")
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
        else:
            if self.triggerAPD:
                self.triggertask.stop()
                self.triggertask.close()
                self.triggerAPD = False

            self.triggertask = nidaqmx.Task('TriggerPMTtask')
        # Create the signal trigger
            triggerrate = self.sampleRate
            num = int(self.triggerEdit.text())
            trigger2 = [True, True, False]
            # trigger2 = np.tile(trigger, self.numberofPixels)
            self.trigger = np.concatenate((np.zeros(num, dtype="bool"),
                                           trigger2))

            # print((num/triggerrate)*10**3,
            # "delay (ms)")  # "\n", num, "num elegido",

        # Configure the digital channels to trigger the synchronization signal
            self.triggertask.do_channels.add_do_chan(
                lines="Dev1/port0/line6", name_to_assign_to_lines='chan6',
                line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)

            self.triggertask.timing.cfg_samp_clk_timing(
                         rate=triggerrate,  # muestras por segundo
                         sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                         # source='100kHzTimebase',
                         active_edge=nidaqmx.constants.Edge.RISING,
                         samps_per_chan=len(self.trigger))
        # Configure a start trigger to synchronizate the measure and movement
            triggerchannelname = "PFI4"
            self.aotask.triggers.start_trigger.cfg_dig_edge_start_trig(
                                trigger_source=triggerchannelname)  # ,
            # trigger_edge = nidaqmx.constants.Edge.RISING)
            self.PMTtask.triggers.start_trigger.cfg_dig_edge_start_trig(
                            trigger_source=triggerchannelname)  # ,
            self.triggerPMT = True

    def TriggerOpenAPD(self):
        if self.triggerAPD:
            print("Ya esta el trigger APD")  # to dont open again

        else:
            if self.triggerPMT:
                self.triggertask.stop()
                self.triggertask.close()
                self.triggerPMT = False

            self.triggertask = nidaqmx.Task('TriggerAPDtask')
        # Create the signal trigger
            triggerrate = self.apdrate
            num = int((int(self.triggerEdit.text()) *
                       self.Napd)*self.apdrate/10**3)

#            trigger = np.zeros((len(self.onerampx)*self.Napd),dtype="bool")
#            trigger[:] = True
#            trigger1 = np.concatenate((trigger, np.zeros(100,dtype="bool")))
            # 2ms de apagado, hace cosas raras
            trigger2 = np.ones(self.totalcinumber-num, dtype='bool')
            # [True,False,True, True, False]
            # np.tile(trigger, self.numberofPixels)

            self.trigger = np.concatenate((np.zeros(num, dtype="bool"),
                                           trigger2))

            # print((num/self.apdrate)*10**3,
            # "delay (ms)")  # "\n", num, "num elegido",

        # Configure the digital channels to trigger the synchronization signal
            self.triggertask.do_channels.add_do_chan(
                lines="Dev1/port0/line6", name_to_assign_to_lines='chan6',
                line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)

            self.triggertask.timing.cfg_samp_clk_timing(
                         rate=triggerrate,  # muestras por segundo
                         sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                         # source='100kHzTimebase',
                         active_edge=nidaqmx.constants.Edge.RISING,
                         samps_per_chan=len(self.trigger))

        # Configure a start trigger to synchronizate the measure and movement
            triggerchannelname = "PFI4"
            self.aotask.triggers.start_trigger.cfg_dig_edge_start_trig(
                                trigger_source=triggerchannelname)  # ,
#                                trigger_edge = nidaqmx.constants.Edge.RISING)

            self.APD1task.triggers.arm_start_trigger.dig_edge_src = triggerchannelname
            self.APD1task.triggers.arm_start_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_EDGE

            self.APD2task.triggers.arm_start_trigger.dig_edge_src = triggerchannelname
            self.APD2task.triggers.arm_start_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_EDGE

            self.triggerAPD = True

# %%---- done
    def done(self):
        """ stop and close all the channels"""
        # if self.channelramp or self.channelsteps:
        try:
            # print("Cierro todos los canales")
            self.aotask.stop()  # Piezo
            self.aotask.close()
        except:
            # print("a")
            pass
        try:
            self.APD1task.stop()  # Apd
            self.APD1task.close()
        except:
            pass
            # print("b_0")
        try:
            self.APD2task.stop()  # Apd
            self.APD2task.close()
        except:
            pass
            # print("b_1")
        try:
            self.PMTtask.stop()  # PMT
            self.PMTtask.close()
        except:
            pass
            # print("c")
        try:
            self.triggertask.stop()  # trigger, antes dotask
            self.triggertask.close()
        except:
            pass
            # print("d")
        try:
            self.pointtask.stop()
            self.pointtask.close()
        except:
            pass
        try:
            self.pointtask2.stop()
            self.pointtask2.close()
        except:
            pass
            # print("d")

#        self.shuttertask.stop()
#        self.shuttertask.close()
#        self.shuttering = False
        self.channelramp = False
        self.channelsteps = False
        self.piezoramp = False
        self.piezosteps = False
        self.PMTon = False
        self.APDson = False
        self.triggeron = False  # separo los canales en partes
        self.triggerAPD = False
        self.triggerPMT = False
#        else:
#            print("llego hasta el done pero no tenia nada que cerrar")
#            # Esto no tendria que pasar

# %%--- Step Cosas --------------
    def stepLine(self):
        # tic = ptime.time()

        for i in range(self.numberofPixels):
            # tec = ptime.time()
            # self.citask.stop()
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
            resta = self.APDstep[-1] - self.APDstep[0]
            self.image[-1-i, self.numberofPixels-1-self.dy] = resta

# --stepScan ---
    def stepScan(self):
        """the step clock calls this function"""
        self.stepLine()

#        self.image[:, self.numberofPixels-1-(self.dy)] = self.cuentas
        self.img.setImage(self.image, autoLevels=self.autoLevels)

        if self.dy < self.numberofPixels-1:
            self.dy = self.dy + 1
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
        gox = (np.linspace(0, sizeX, Npuntos) + startX) - (self.scanRange/2)
        self.allstepsx = np.transpose(np.tile(gox, (self.numberofPixels, 1)))
    # a matrix [i,j] where i go for the complete ramp and j evolves in y lines
#        self.gox = gox

#    Barrido y: secondary signal
        startY = float(self.initialPosition[1])
        goy = np.ones(Npuntos) * startY
        self.allstepsy = np.zeros((self.numberofPixels, self.numberofPixels))
        stepy = self.scanRange / self.numberofPixels
        for j in range(len(self.allstepsy)):
            self.allstepsy[:, j] = goy + (j) * stepy

#    Barrido z (se queda en la posicion inicial): thirth signal (static)
        startZ = float(self.initialPosition[2])
        goz = np.ones(Npuntos) * startZ
        self.allstepsz = np.tile(goz, (self.numberofPixels, 1))

        if self.PSFMode.currentText() == 'XY normal psf':
            print("escaneo x y normal S")

        elif self.PSFMode.currentText() == 'XZ':
            # print("intercambio y por z S")
            self.allstepsz = self.allstepsy - startY + startZ  # -(sizeX/2)
            goy = np.ones(len(self.allstepsx)) * startY
            self.allstepsy = np.tile(goy, (self.numberofPixels, 1))

        elif self.PSFMode.currentText() == 'YZ':
            # print("intercambio x por y S")
            self.allstepsz = self.allstepsy - startY + startZ  # -(sizeX/2)
            self.allstepsy = self.allstepsx - startX + startY
            gox = np.ones(len(self.allstepsy)) * startX
            self.allstepsx = np.tile(gox, (self.numberofPixels, 1))

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

    # Habia una version con rampas, y la borre.
    # buscar en archivos viejos si se quiere
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
        PosZ = self.initialPosition[2]
        if PosZ < float(getattr(self, 'z' + "StepEdit").text()):
            print("OJO!, te vas a Z's negativos")
            self.zStepEdit.setStyleSheet(" background-color: red; ")
#            setStyleSheet("color: rgb(255, 0, 255);")
        else:
            self.moveZ('z', -float(getattr(self, 'z' + "StepEdit").text()))
            self.zStepEdit.setStyleSheet("{ background-color: }")
        if PosZ == 0:  # para no ira z negativo
            self.zDownButton.setStyleSheet(
                "QPushButton { background-color: red; }"
                "QPushButton:pressed { background-color: blue; }")
            self.zDownButton.setEnabled(False)

    def moveZ(self, axis, dist):
        """moves the position along the Z axis a distance dist."""

        with nidaqmx.Task("Ztask") as Ztask:
            # self.Ztask = nidaqmx.Task('Ztask')
            # Following loop creates the voltage channels
            n = 2
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

# %% Go Cm, go Gauss y go to
    def goCM(self):
        rango2 = self.scanRange/2
        self.zgotoLabel.setStyleSheet(" background-color: ")
        print("arranco en", float(self.xLabel.text()),
              float(self.yLabel.text()),
              float(self.zLabel.text()))

        startX = float(self.xLabel.text())
        startY = float(self.yLabel.text())
        self.moveto((float(self.CMxValue.text()) + startX) - rango2,
                    (float(self.CMyValue.text()) + startY) - rango2,
                    float(self.zLabel.text()))

        print("termino en", float(self.xLabel.text()),
              float(self.yLabel.text()),
              float(self.zLabel.text()))

    def goGauss(self):
            self.zgotoLabel.setStyleSheet(" background-color: ")
            print("arranco en", float(self.xLabel.text()),
                  float(self.yLabel.text()),
                  float(self.zLabel.text()))

            startX = float(self.xLabel.text())
            startY = float(self.yLabel.text())
            self.moveto((float(self.GaussxValue.text()) + startX) - rango2,
                        (float(self.GaussyValue.text()) + startY) - rango2,
                        float(self.zLabel.text()))

            print("termino en", float(self.xLabel.text()),
                  float(self.yLabel.text()),
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

# # ---moveto ---
    def moveto(self, x, y, z):
        """moves the position along the axis to a specified point."""
        self.PiezoOpenStep()  # se mueve de a puntos, no rampas.
#        t = self.moveTime
        N = self.moveSamples

    # read initial position for all channels
        texts = [getattr(self, ax + "Label").text()
                 for ax in activeChannels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]

        if float(initPos[0]) != x or float(initPos[1]) != y\
           or float(initPos[2]) != z:
            rampx = np.linspace(float(initPos[0]), x, N)
            rampy = np.linspace(float(initPos[1]), y, N)
            rampz = np.linspace(float(initPos[2]), z, N)

            tuc = ptime.time()
            for i in range(N):
                self.aotask.write([
                               rampx[i] / convFactors['x'],
                               rampy[i] / convFactors['y']], auto_start=True)
#                              rampz[i] / convFactors['z']], auto_start=True)
#                time.sleep(t / N)

            print("se mueve todo en", np.round(ptime.time()-tuc, 4), "segs\n")

            self.xLabel.setText("{}".format(np.around(float(rampx[-1]), 2)))
            self.yLabel.setText("{}".format(np.around(float(rampy[-1]), 2)))
            self.zLabel.setText("{}".format(np.around(float(rampz[-1]), 2)))
            self.paramChanged()
            self.done()
#            self.channelsOpen()
        else:
            print("¡YA ESTOY EN ESAS COORDENADAS!")


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
        for i in range(3):
            if p == shutters[i]:
                self.shuttersignal[i] = True
        self.shuttertask.write(self.shuttersignal, auto_start=True)
        # print(self.shuttersignal)
        self.checkShutters()
        print("open", p)

    def closeShutter(self, p):
        for i in range(len(shutters)):
            if p == shutters[i]:
                self.shuttersignal[i] = False
        self.shuttertask.write(self.shuttersignal, auto_start=True)
        # print(self.shuttersignal)
        self.checkShutters()
        print("close", p)

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
        if not self.shuttering:
            self.shuttering = True
            self.shuttertask = nidaqmx.Task("shutter")
            self.shuttertask.do_channels.add_do_chan(
                lines="Dev1/port0/line0:2", name_to_assign_to_lines='shutters',
                line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
#        else:
#            #print("ya estaban abiertos los canales shutters")

    def closeAllShutters(self):
        for i in range(len(shutters)):
            self.shuttersignal[i] = False
        self.shuttertask.write(self.shuttersignal, auto_start=True)
        self.checkShutters()
        print("cierra shutters", self.shuttersignal)

# %%--- MovetoStart ---
    def MovetoStart(self):
        """ When called, it gets to the start point"""
        tic = ptime.time()
        if self.dy == 0:
            print("is already in start")

        else:
            self.inStart = True
            # print("moving to start")
            self.done()

    #         Creates the voltage channels to move "slowly"
            with nidaqmx.Task("aotask") as aotask:
                # self.aotask = nidaqmx.Task('aotask')
                for n in range(len(AOchans)):
                    aotask.ao_channels.add_ao_voltage_chan(
                        physical_channel='Dev1/ao%s' % AOchans[n],
                        name_to_assign_to_channel='cha_%s' % activeChannels[n],
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
                    maximox = self.allstepsx[-1, self.dy]
                    maximoy = self.allstepsy[-1, self.dy]
#                    maximoz = self.allstepsz[-1,self.dy]
                else:
                    stops = ((len(self.onerampx))-1) * self.dy
                    maximox = self.totalrampx[stops]
                    maximoy = self.totalrampy[stops]
#                    maximoz = self.totalrampz[stops]
                    """
                    maximox = self.realposX
                    maximoy = self.realposY
#                    maximoz = self.realposZ
#                    """

                volviendox = np.linspace(maximox, startX, self.moveSamples)
                volviendoy = np.linspace(maximoy, startY, self.moveSamples)
#                volviendoz = np.linspace(maximoz, startZ, self.moveSamples)

                aotask.write(np.array(
                    [volviendox / convFactors['x'],
                     volviendoy / convFactors['y']]), auto_start=True)
    #                 volviendoz / convFactors['z']]), auto_start=True)
#                aotask.wait_until_done()
#                print(np.round(ptime.time() - tic, 5)*10**3,
#                      "MovetoStart (ms)")

#            self.aotask.stop()
#            self.aotask.close()

        self.dy = 0
        toc = ptime.time()
        print("\n tiempo movetoStart (ms)", (toc-tic)*10**3, "\n")

# %%--- ploting in live
    def plotLive(self):
        tic = ptime.time()
        rango = self.scanRange
        texts = [getattr(self, ax + "Label").text() for ax in activeChannels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]
        x = np.linspace(0, rango, self.numberofPixels) + float(initPos[0])
        y = np.linspace(0, rango, self.numberofPixels) + float(initPos[1])
        X, Y = np.meshgrid(x, y)
        fig, ax = plt.subplots()
        p = ax.pcolor(X, Y, np.transpose(self.image), cmap=plt.cm.jet)
        fig.colorbar(p)  # cb =
        ax.set_xlabel('x [um]')
        ax.set_ylabel('y [um]')
        if self.CMplot:
            xc = int(np.floor(self.xcm))
            yc = int(np.floor(self.ycm))
            X2 = np.transpose(X)
            Y2 = np.transpose(Y)
            resol = 2
            for i in range(resol):
                for j in range(resol):
                    ax.text(X2[xc+i, yc+j], Y2[xc+i, yc+j], "CM", color='m')
            Normal = self.scanRange / self.numberofPixels  # Normalizo
            ax.set_title((self.xcm*Normal+float(initPos[0]),
                          self.ycm * Normal + float(initPos[1])))
        if self.GaussPlot:
            xc = int(np.floor(self.xGauss))
            yc = int(np.floor(self.yGauss))
            X2 = np.transpose(X)
            Y2 = np.transpose(Y)
            resol = 2
            for i in range(resol):
                for j in range(resol):
                    ax.text(X2[xc+i, yc+j], Y2[xc+i, yc+j], "Ga", color='m')
            Normal = self.scanRange / self.numberofPixels  # Normalizo
            ax.set_title((xc*Normal+float(initPos[0]),
                          yc * Normal + float(initPos[1])))

        plt.show()
        toc = ptime.time()
        print("\n tiempo Plotlive", toc-tic, "\n")

# %%--- SaveFrame ---
    def save_name_update(self):
        self.edit_Name = str(self.edit_save.text())
        self.NameNumber = 0

#    def create_daily_directory(self):
#        root = tk.Tk()
#        root.withdraw()
#
#        self.file_path = filedialog.askdirectory()
#
#        timestr = time.strftime("%Y-%m-%d")  # -%H%M%S")
#
#        newpath = self.file_path + "/" + timestr
#        if not os.path.exists(newpath):
#            os.makedirs(newpath)
#        else:
#            print("Ya existe esa carpeta")
#
#        self.file_path = newpath
#        self.NameDirValue.setText(self.file_path)
#        self.NameDirValue.setStyleSheet(" background-color: ; ")

    def saveFrame(self):
        """ Config the path and name of the file to save, and save it"""
        try:
            filepath = self.main.file_path
            # nombre con la fecha -hora
            name = str(filepath + "/" + str(self.edit_save.text()) + ".tiff")
            if self.imagecheck.isChecked():
                guardado = Image.fromarray(
                                         np.transpose(np.flip(self.image2, 1)))
            else:
                guardado = Image.fromarray(
                                         np.transpose(np.flip(self.image, 1)))

            guardado.save(name)
            self.NameNumber = self.NameNumber + 1
            self.edit_save.setText(self.edit_Name + str(self.NameNumber))
            print("\n Image saved\n")
        except IOError as e:
            print("I/O error({0}): {1}".format(e.errno, e.strerror))
#
#    def selectFolder(self):
#        root = tk.Tk()
#        root.withdraw()
#        self.file_path = filedialog.askdirectory()
#        # print(self.file_path,2)
#        self.NameDirValue.setText(self.file_path)
#        self.NameDirValue.setStyleSheet(" background-color: ")
#
#    def openFolder(self):
#        os.startfile(self.file_path)

# %% GaussFit
    def GaussFit(self):
        tic = ptime.time()
        self.data = self.image
        params = fitgaussian(self.data)
        self.fit = gaussian(*params)
        self.params = params
        (height, x, y, width_x, width_y) = params
        self.xGauss = x
        self.yGauss = y
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
        self.GaussPlot = True
        print(np.round((tac-tic)*10**3, 3), "(ms)Gauss fit\n")

# %% CMmeasure
    def CMmeasure(self):

        tic = ptime.time()
        Z = self.image
        xcm, ycm = ndimage.measurements.center_of_mass(Z)
        self.xcm = xcm
        self.ycm = ycm
#        xc = int(np.round(xcm,2))
#        yc = int(np.round(ycm,2))
        Normal = self.scanRange / self.numberofPixels
        self.CMxValue.setText(str(xcm*Normal))
        self.CMyValue.setText(str(ycm*Normal))
        tac = ptime.time()
        self.CMplot = True
        print(np.round((tac-tic)*10**3, 3), "(ms) CM\n")

# %% arma los datos para modular.(mapa)

    def mapa(self):
        Z = self.image
        N = len(Z)
        lomas = np.max(Z)
        Npasos = 4
        paso = lomas/Npasos
        tec = ptime.time()
        SZ = Z.ravel()
        mapa = np.zeros((N, N))
        Smapa = mapa.ravel()
        for i in range(len(SZ)):
            if SZ[i] > paso:
                Smapa[i] = 10
            if SZ[i] > paso*2:
                Smapa[i] = 20
            if SZ[i] > paso*3:
                Smapa[i] = 30
        mapa = np.split(Smapa, N)
        print(np.round((ptime.time()-tec)*10**3, 4), "ms tarda mapa\n")
        self.img.setImage((np.array(mapa)), autoLevels=True)
#        self.img.setImage((np.flip(mapa,0)), autoLevels=False)

# %%  ROI cosas
    def ROImethod(self):
        if self.roi is None:

            ROIpos = (0.5 * self.numberofPixels - 64,
                      0.5 * self.numberofPixels - 64)
            self.roi = viewbox_tools.ROI(self.numberofPixels, self.vb,
                                         ROIpos,
                                         handlePos=(1, 0),
                                         handleCenter=(0, 1),
                                         scaleSnap=True,
                                         translateSnap=True)
        else:
            self.vb.removeItem(self.roi)
            self.roi.hide()
            self.roi.disconnect()
            if self.ROIButton.isChecked():
                ROIpos = (0.5 * self.numberofPixels - 64,
                          0.5 * self.numberofPixels - 64)
                self.roi = viewbox_tools.ROI(self.numberofPixels, self.vb,
                                             ROIpos,
                                             handlePos=(1, 0),
                                             handleCenter=(0, 1),
                                             scaleSnap=True,
                                             translateSnap=True)

    def selectROI(self):
        self.liveviewStop()

        array = self.roi.getArrayRegion(self.image, self.img)
        ROIpos = np.array(self.roi.pos())
        newPos_px = tools.ROIscanRelativePOS(ROIpos,
                                             self.numberofPixels,
                                             np.shape(array)[1])
        newPos_µm = newPos_px * self.pixelSize + self.initialPosition[0:2]

        newPos_µm = np.around(newPos_µm, 2)

        print("estaba en", float(self.xLabel.text()),
              float(self.yLabel.text()), float(self.zLabel.text()))

        self.moveto(float(newPos_µm[0]),
                    float(newPos_µm[1]),
                    float(self.initialPosition[2]))

        print("ROI fue a", float(self.xLabel.text()),
              float(self.yLabel.text()), float(self.zLabel.text()), "/n")

        newRange_px = np.shape(array)[0]
        newRange_µm = self.pixelSize * newRange_px
        newRange_µm = np.around(newRange_µm, 2)

        print("cambió el rango, de", self.scanRange)
        self.scanRangeEdit.setText('{}'.format(newRange_µm))
        print("hasta :", self.scanRange, "\n")
        self.paramChanged()

# %% Roi Histogram
    def histogramROI(self):
        # ----
        def updatehistogram():
            array = self.roihist.getArrayRegion(self.image, self.img)
            ROIpos = np.array(self.roihist.pos())
            newPos_px = tools.ROIscanRelativePOS(ROIpos,
                                                 self.numberofPixels,
                                                 np.shape(array)[1])
            newRange_px = np.shape(array)[0]

            roizone = self.image[
                      int(newPos_px[0]):int(newPos_px[0]+newRange_px),
                      self.numberofPixels-int(newPos_px[1]+newRange_px):
                      self.numberofPixels-int(newPos_px[1])]
            y, x = np.histogram(roizone,
                                bins=np.linspace(
                                 -0.5, np.ceil(np.max(self.image))+2,
                                 np.ceil(np.max(self.image))+3))
            m = np.mean(roizone)
            m2 = np.max(roizone)
            text = "<strong> mean = {:.3} | max = {:.3}".format(
                                                           float(m), float(m2))
            self.p6.setLabel('top', text)
            self.curve.setData(x, y, name=text, stepMode=True,
                               fillLevel=0,
                               brush=(0, 0, 255, 150))
        # ----
        if self.histogramROIButton.isChecked():
            ROIpos = (0.5 * self.numberofPixels - 64,
                      0.5 * self.numberofPixels - 64)
            self.roihist = viewbox_tools.ROI(self.numberofPixels, self.vb,
                                             ROIpos,
                                             handlePos=(1, 0),
                                             handleCenter=(0, 1),
                                             scaleSnap=True,
                                             translateSnap=True)
            self.roihist.sigRegionChanged.connect(updatehistogram)

            self.HistoWidget = pg.GraphicsLayoutWidget()
            self.p6 = self.HistoWidget.addPlot(row=2, col=1)

            self.p6.showGrid(x=True, y=True)
            self.p6.setLabel('left', 'Number of pixels with this counts')
            self.p6.setLabel('bottom', 'counts')
            self.p6.setLabel('right', '')
            self.curve = self.p6.plot(open='y')
            self.algo.textChanged.connect(updatehistogram)
            self.otrosDock.addWidget(self.HistoWidget)

        else:
            self.vb.removeItem(self.roihist)
            self.roihist.hide()
            self.HistoWidget.deleteLater()
            self.roihist.disconnect()
            self.maxcountsEdit.disconnect()


# %% Roi lineal
    def ROIlinear(self):
        largo = self.numberofPixels/1.5+10

        def updatelineal():
            array = self.linearROI.getArrayRegion(self.image, self.img)
            self.curve.setData(array)

        if self.ROIlineButton.isChecked():

            self.linearROI = pg.LineSegmentROI([[10, 64], [largo, 64]], pen='m')
            self.vb.addItem(self.linearROI)
            self.linearROI.sigRegionChanged.connect(updatelineal)

            self.LinearWidget = pg.GraphicsLayoutWidget()
            self.p6 = self.LinearWidget.addPlot(row=2, col=1,
                                                title="Linear plot")
            self.p6.showGrid(x=True, y=True)
            self.curve = self.p6.plot(open='y')
            self.otrosDock.addWidget(self.LinearWidget)
        else:
            self.vb.removeItem(self.linearROI)
            self.linearROI.hide()
            self.LinearWidget.deleteLater()

    def selectLineROI(self):
        fig, ax = plt.subplots()
        array = self.linearROI.getArrayRegion(self.image, self.img)
        plt.plot(array)
        ax.set_xlabel('Roi')
        ax.set_ylabel('Intensity (N photons)')
        plt.show()

# %% Presets, shutters
        # otra idea de presets. abrir los shutters que se quieran
    def PreparePresets(self):
        # presetsModes = ['Red','Yellow','STED','Yell+STED','Red+STED','nada']
        if self.presetsMode .currentText() == self.presetsModes[0]:  # rojo
            self.presetsMode.setStyleSheet("QComboBox{color: rgb(255,0,0);}\n")
        elif self.presetsMode .currentText() == self.presetsModes[1]:  # amarlo
            self.presetsMode.setStyleSheet("QComboBox{color:rgb(128,128,0);}")
        elif self.presetsMode .currentText() == self.presetsModes[2]:  # TED
            self.presetsMode.setStyleSheet("QComboBox{color: rgb(128,0,0);}\n")
        elif self.presetsMode .currentText() == self.presetsModes[3]:  # am+TED
            self.presetsMode.setStyleSheet("QComboBox{color:rgb(210,105,30);}")
        elif self.presetsMode .currentText() == self.presetsModes[4]:  # ro+TED
            self.presetsMode.setStyleSheet("QComboBox{color:rgb(255,90,0);}\n")
        elif self.presetsMode .currentText() == self.presetsModes[5]:  # nada
            self.presetsMode.setStyleSheet("QComboBox{color: rgb(0,0,0);}\n")
# https://www.rapidtables.com/web/color/RGB_Color.html  COLORES en rgb

    def Presets(self):
        # shutters = ["red", "STED", "yellow"]  # digitals out channs [0, 1, 2]
        # presetsModes = ['Red','Yellow','STED','Yell+STED','Red+STED','nada']
        # Estan definidos mas arriba, los copio aca como referencia
        if self.presetsMode .currentText() == self.presetsModes[0]:  # rojo
            self.openShutter(shutters[0])
        elif self.presetsMode .currentText() == self.presetsModes[1]:  # amaril
            self.openShutter(shutters[2])
        elif self.presetsMode .currentText() == self.presetsModes[2]:  # TED
            self.openShutter(shutters[1])
        elif self.presetsMode .currentText() == self.presetsModes[3]:  # am+TED
            self.openShutter(shutters[2])
            self.openShutter(shutters[1])
        elif self.presetsMode .currentText() == self.presetsModes[4]:  # ro+TED
            self.openShutter(shutters[0])
            self.openShutter(shutters[1])

# %% getInitPos  Posiciones reales, si agrego los cables que faltan
    def getInitPos(self):
        tic = ptime.time()
#        aitask = nidaqmx.Task("aitask")
#        aitask.ai_channels.add_ai_voltage_chan("Dev1/ai7:6")
        # por comodidad de cables esta decreciente 7 6
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

        print("Lecturas de las ai 7y6", data[0][-1], data[1][-1])
        self.realposX = data[0][-1] * convFactors['x']
        self.realposY = data[1][-1] * convFactors['y']
        print("Posiciones Actuales", self.realposX, self.realposY)
        valorX = find_nearest(self.totalrampx, self.realposX)
        valorY = find_nearest(self.totalrampy, self.realposY)
        print("valorx,y", valorX, valorY)
        self.indiceX = np.where(self.totalrampx == valorX)[0][0]
        self.indiceY = np.where(self.totalrampy == valorY)[0][0]  # [-self.p]
        print(self.indiceX, self.indiceX)
        print("En la rampa X:", self.totalrampx[self.indiceX])
        print("En la rampa Y:", self.totalrampy[self.indiceY])
        # ojo, el indice en x se repite Npix veces
        #  y el indice en y es el mismo para len(onerampx) valores
        nrampa = np.round(self.indiceY / len(self.onerampx))*len(self.onerampx)
        # tengo que hacer esto porque y cambia antes (recordar el p que puse)
        print("índice posta", int(nrampa+self.indiceX))
        print("valor en totalrampx", self.totalrampx[int(nrampa+self.indiceX)])
    # definir dy para que empieze a dibujar por donde corresponda
#        self.dy=

        toc = ptime.time()
        print("\n tiempo getInitPos", toc-tic, "\n")

# %% Point scan ---+--- Hay que elegir APD
    def PointStart(self):
        print("Opening a new popup window...")
        self.w = Traza(self.main)
        self.w.setGeometry(QtCore.QRect(750, 50, 450, 600))
        self.w.show()


# %% Clase para TRAZA
class Traza(QtGui.QWidget):

    def closeEvent(self, event):
        self.pointtimer.stop()
        self.running = False
        print("flor de relozzz")

    def __init__(self, main, *args, **kwargs):
        QtGui.QWidget.__init__(self)
        super().__init__(*args, **kwargs)
        self.main = main
        self.ScanWidget = ScanWidget(main, device)
#        self.form_widget = ScanWidget(self, device)
        self.traza_Widget2 = pg.GraphicsLayoutWidget()
        self.running = False
        grid = QtGui.QGridLayout()
        self.setLayout(grid)

        self.p6 = self.traza_Widget2.addPlot(row=2, col=1, title="Traza")
        self.p6.showGrid(x=True, y=True)
        self.curve = self.p6.plot(open='y')

        self.p7 = self.traza_Widget2.addPlot(row=3, col=1, title="Traza")
        self.p7.showGrid(x=True, y=True)
        self.curve2 = self.p7.plot(open='y')

    #  buttons
        self.play_pause_Button = QtGui.QPushButton('► Play / Pause ‼')
        self.play_pause_Button.setCheckable(True)
        self.play_pause_Button.clicked.connect(self.play_pause)
        self.play_pause_Button.setToolTip('Pausa y continua la traza')
#        self.pause_Button.setStyleSheet(
#                "QPushButton { background-color: rgb(200, 200, 10); }"
#                "QPushButton:pressed { background-color: blue; }")

        self.stop_Button = QtGui.QPushButton('Stop ◘')
        self.stop_Button.setCheckable(False)
        self.stop_Button.clicked.connect(self.stop)
        self.stop_Button.setToolTip('Para la traza')

        grid.addWidget(self.traza_Widget2,      0, 0)
        grid.addWidget(self.play_pause_Button,  0, 3)
        grid.addWidget(self.stop_Button,        1, 3)
        self.play_pause_Button.setChecked(True)
        self.PointScan()
#        self.connect(self, QtCore.SIGNAL('triggered()'), self.hola)

# TODO: a seguir mejorando esta parte
#     def play(self):
#         if self.play_Button.isChecked():
#             if self.running == True:
#                 self.pointtimer.start(self.tiempo)
#             else:
#                 self.PointScan()
#         else:
#             self.pointtimer.stop()

    def play_pause(self):
        if self.play_pause_Button.isChecked():
            # self.pause_Button.setStyleSheet(
            #        "QPushButton { background-color: ; }")
            if self.running:
                self.pointtimer.start(self.tiempo)
            else:
                self.PointScan()
        else:
            self.pointtimer.stop()
            # self.pause_Button.setStyleSheet(
            #        "QPushButton { background-color: red; }")

    def stop(self):

        try:
            self.pointtimer.stop()
        except IOError as e:
            print("I/O error({0}): {1}".format(e.errno, e.strerror))
        self.running = False
        self.play_pause_Button.setChecked(False)

    def PointScan(self):
        self.running = True
        self.tiempo = 400  # ms  # refresca el numero cada este tiempo
        self.points = np.zeros(int((apdrate * (self.tiempo / 10**3))))
        self.points2 = np.copy(self.points)

        self.pointtask = nidaqmx.Task('pointtask')
        # Configure the counter channel to read the APD
        self.pointtask.ci_channels.add_ci_count_edges_chan(
                            counter='Dev1/ctr{}'.format(COchans[0]),
                            name_to_assign_to_channel=u'Line_counter',
                            initial_count=0)

        self.pointtask2 = nidaqmx.Task('pointtask2')
        # Configure the counter channel to read the APD
        self.pointtask2.ci_channels.add_ci_count_edges_chan(
                            counter='Dev1/ctr{}'.format(COchans[1]),
                            name_to_assign_to_channel=u'Line_counter',
                            initial_count=0)
        self.ptr1 = 0
        self.timeaxis = []
        self.data1 = []  # np.empty(100)
        self.data2 = []  # np.empty(300)

        self.pointtimer = QtCore.QTimer()
        self.pointtimer.timeout.connect(self.updatePoint)
        self.pointtimer.start(self.tiempo)

    def updatePoint(self):
        N = len(self.points)
        self.points[:] = self.pointtask.read(N)
        self.points2[:] = self.pointtask2.read(N)

        m = np.mean(self.points)
        m2 = np.mean(self.points2)
#        #print("valor traza", m)
        self.ScanWidget.PointLabel.setText("<strong>{0:.2e}|{0:.2e}".format(
                                           float(m), float(m2)))

        self.timeaxis.append((self.tiempo * 10**-3)*self.ptr1)
        self.data1.append(m)
        self.ptr1 += 1
        self.curve.setData(self.timeaxis, self.data1)

        self.data2 = np.roll(self.data2, -1)            # (see also: np.roll)
        self.data2.append(m2)
        self.curve2.setData(self.timeaxis, self.data2)
#        self.curve2.setPos(self.timeaxis[0], 0)


# %% Otras Funciones
def gaussian(height, center_x, center_y, width_x, width_y):
    """Returns a gaussian function with the given parameters"""
    width_x = float(width_x)
    width_y = float(width_y)
    return lambda x, y: height*np.exp(
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


def find_nearest(array, value):
    idx = (np.abs(array-value)).argmin()
    return array[idx]
# %% FIN
app = QtGui.QApplication([])
win = ScanWidget(device)
# win = MainWindow()
win.show()

app.exec_()
