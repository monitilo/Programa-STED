# %%
""" Programa inicial donde miraba como anda el liveScan
 sin usar la pc del STED. incluye positioner"""

# import subprocess
# import scipy.ndimage as ndi

#import sys
import os

import numpy as np
import time

import matplotlib.pyplot as plt

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui

from pyqtgraph.dockarea import DockArea, Dock
import pyqtgraph.ptime as ptime
#
from PIL import Image

import re

import tkinter as tk
from tkinter import filedialog

import tools
from sys import stdout
try:
    import viewbox_toolsQT5 as viewbox_tools
    stdout.write("\033[1;31m")
    print("\n uso Qt5 \n")
except:
    import viewbox_tools
    stdout.write("\033[1;31m")
    print("\n uso Qt4 \n")
stdout.write("\033[0;0m")

# =============================================================================
# RED   = "\033[1;31m"  
# BLUE  = "\033[1;34m"
# CYAN  = "\033[1;36m"
# GREEN = "\033[0;32m"
# RESET = "\033[0;0m"
# BOLD    = "\033[;1m"
# REVERSE = "\033[;7m"
# =============================================================================

from scipy import ndimage
from scipy import optimize

device = 9
convFactors = {'x': 25, 'y': 25, 'z': 1.683}  # la calibracion es 1 µm = 40 mV;
# la de z es 1 um = 0.59 V
apdrate = 10**5
shutters = ['532 (verde)', '640 (rojo)', '405 (azul)']
# TODO: estar seguro cual es cual en las salidas digitales
activeChannels = ["x", "y", "z"]

# import ctypes  # For the pop ups warnings, Pero uso QtGui.QMessageBox
# ctypes.windll.user32.MessageBoxW(0,
#                                 "No lo tomo como grilla, AVISAR!\
#                                 \n Pero igual creó una carpeta",
#                                 "Algo raro paso ;(", 0)


# %% Main Window
class MainWindow(QtGui.QMainWindow):
    """
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
#    """
#    Signal1 = QtCore.pyqtSignal()

    def newCall(self):
        self.a = 0
        print('New')

    def openCall(self):
        self.a = 1.5
        namebien = (self.form_widget.NameDirValue.text()).replace("/", "\\")
#        print("corregido", namebien)
#        namebien = self.form_widget.NameDirValue.text()
#        print("normal",namebien)
        os.startfile(namebien)
#        print('Open')

    def exitCall(self):
        self.a = -1.5
        print('Exit app (no hace nada)')

    def localDir(self):
        print('poner la carpeta donde trabajar')
        root = tk.Tk()
        root.withdraw()

        file_path = filedialog.askdirectory()
        if not file_path:
            print("No elegiste nada")
        else:
            self.file_path = file_path
            print(" direccion elegida ", self.file_path)
            self.form_widget.NameDirValue.setText(self.file_path)
            self.form_widget.NameDirValue.setStyleSheet(" background-color: ")
    #        self.form_widget.paramChanged()

    def create_daily_directory(self):
        root = tk.Tk()
        root.withdraw()

        file_path = filedialog.askdirectory()
        if not file_path:
            print("No crea la carpeta")
        else:
            timestr = time.strftime("%Y-%m-%d")  # -%H%M%S")

            newpath = file_path + "/" + timestr
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
#        self.setMinimumSize(QtCore.QSize(500, 500))
        self.setWindowTitle("PC PyPrintingPy PC")

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
        dailyAction = QtGui.QAction(QtGui.QIcon('create.png'),
                                    '&Create daily Dir', self)
        dailyAction.setStatusTip('Create the work folder')
        dailyAction.setShortcut('Ctrl+D')
        dailyAction.triggered.connect(self.create_daily_directory)

    # Create de create daily directory action
        save_docks_Action = QtGui.QAction(QtGui.QIcon('save.png'),
                                          '&Save Docks', self)
        save_docks_Action.setStatusTip('Saves the Actual Docks configuration')
        save_docks_Action.setShortcut('Ctrl+p')
        save_docks_Action.triggered.connect(self.save_docks)

    # Create de create daily directory action
        load_docks_Action = QtGui.QAction(QtGui.QIcon('load.png'),
                                          '&Load Docks', self)
        load_docks_Action.setStatusTip('Load a previous Docks configuration')
        load_docks_Action.setShortcut('F11')
        load_docks_Action.triggered.connect(self.load_docks)

    # Create menu bar and add action
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')
        fileMenu.addAction(localDirAction)
        fileMenu.addAction(openAction)
        fileMenu.addAction(dailyAction)
        fileMenu.addAction(exitAction)

        fileMenu2 = menuBar.addMenu('&Docs config')
        fileMenu2.addAction(save_docks_Action)
        fileMenu2.addAction(load_docks_Action)
#        fileMenu3 = menuBar.addMenu('&Local Folder')
#        fileMenu3.addAction(localDiraction)
        fileMenu4 = menuBar.addMenu('&<--Selecciono la carpeta desde aca!')
        fileMenu4.addAction(openAction)

        self.form_widget = ScanWidget(self, device)
        self.setCentralWidget(self.form_widget)
        self.setGeometry(10, 40, 600, 550)  # (PosX, PosY, SizeX, SizeY)
        self.save_docks()

        self.umbralLabel = self.form_widget.umbralLabel
        self.umbralEdit = self.form_widget.umbralEdit
        self.grid_traza_control = True


# %% Scan Widget
class ScanWidget(QtGui.QFrame):

    def __init__(self, main, device, *args, **kwargs):  # main

        super().__init__(*args, **kwargs)

        self.main = main
        self.device = device

# ---  COSAS DE PRINTIG!


        self.locked_focus = False

        self.grid_start_action = QtGui.QAction(self)
        QtGui.QShortcut(
            QtGui.QKeySequence('F5'), self, self.grid_start)

        self.focus_maximun_action = QtGui.QAction(self)
        QtGui.QShortcut(
            QtGui.QKeySequence('F8'), self, self.focus_go_to_maximun)

        self.grid_read_action = QtGui.QAction(self)
        QtGui.QShortcut(
            QtGui.QKeySequence('F1'), self, self.grid_read)

        self.grid_autocorr_action = QtGui.QAction(self)
        QtGui.QShortcut(
            QtGui.QKeySequence('F9'), self, self.focus_autocorr)

    # Cosas para la rutina de imprimir. Grid

    # umbral
        self.umbralLabel = QtGui.QLabel('Umbral')
        self.umbralEdit = QtGui.QLineEdit('10')
        self.umbralEdit.setFixedWidth(40)
        self.umbralEdit.setToolTip('promedios de valores nuevo/anteriores ')
        self.umbralLabel.setToolTip('promedios de valores nuevo/anteriores ')

    # umbral
        self.tmaxLabel = QtGui.QLabel('t max (s)')
        self.tmaxEdit = QtGui.QLineEdit('60')
        self.tmaxEdit.setFixedWidth(40)
        self.tmaxEdit.setToolTip('Tiempo que espera un envento. Si no, sigue')
        self.tmaxLabel.setToolTip('Tiempo que espera un envento. Si no, sigue')

    # Defino el tipo de laser que quiero para imprimir
        self.grid_laser = QtGui.QComboBox()
        self.grid_laser.addItems(shutters)
        self.grid_laser.setCurrentIndex(0)
        self.grid_laser.setToolTip('Elijo el shuter para IMPRIMIR la grilla')
        self.grid_laser.setFixedWidth(80)
        self.grid_laser.activated.connect(lambda: self.color_menu(self.grid_laser))
        self.color_menu(self.grid_laser)

    # Buttons 
        self.cargar_archivo_button = QtGui.QPushButton('Cargar Archivo')
        self.cargar_archivo_button.clicked.connect(self.grid_read)
        self.cargar_archivo_button.setStyleSheet(
                "QPushButton { background-color: orange; }"
                "QPushButton:pressed { background-color: blue; }")
        self.cargar_archivo_button.setToolTip('Carga el archivo con la grilla,\
                                              y plotea para ver si esta bien')

    # Print button. Que en realidad solo crea la carpeta
        self.imprimir_button = QtGui.QPushButton('IMPRIMIR (no)')
        self.imprimir_button.setCheckable(True)
        self.imprimir_button.clicked.connect(self.grid_create_folder)
        self.imprimir_button.setStyleSheet(
                "QPushButton:pressed { background-color: blue; }")
        self.imprimir_button.setToolTip('En realidad solo crea la carpeta\
                                        El mundo es una gran mentira.')
#                "QPushButton:checked {color: white; background-color: blue;}")

    # Print button. Que en realidad solo crea la carpeta
        self.next_button = QtGui.QPushButton('Next ►')
        self.next_button.setCheckable(False)
        self.next_button.clicked.connect(self.grid_start)
        self.next_button.setStyleSheet(
                "QPushButton:pressed { background-color: blue; }")
        self.next_button.setToolTip('Empeiza o continua la grilla')

    # go ref button.
        self.go_ref_button = QtGui.QPushButton('go reference')
        self.go_ref_button.setCheckable(False)
#        self.go_ref_button.clicked.connect(self.gor_reference)
        self.go_ref_button.setStyleSheet(
                "QPushButton:pressed { background-color: blue; }")
        self.go_ref_button.setToolTip('Va a la referencia seteada')
        self.go_ref_button.setFixedWidth(80)

    # set reference button.
        self.set_ref_button = QtGui.QPushButton('set reference')
        self.set_ref_button.setCheckable(False)
#        self.set_ref_button.clicked.connect(self.set_reference)
        self.set_ref_button.setStyleSheet(
                "QPushButton:pressed { background-color: blue; }")
        self.set_ref_button.setToolTip('setea la referencia')
        self.set_ref_button.setFixedWidth(150)

    # La grid con las cosas de printing. Mas abajo entra en el dock
        self.grid_print = QtGui.QWidget()
        grid_print_layout = QtGui.QGridLayout()
        self.grid_print.setLayout(grid_print_layout)
        grid_print_layout.addWidget(self.cargar_archivo_button,   0, 1, 2, 1) # QtGui.QLabel(" ")
        grid_print_layout.addWidget(self.imprimir_button,         0, 2, 2, 1)
        grid_print_layout.addWidget(self.next_button,             2, 2, 2, 1)
        grid_print_layout.addWidget(self.go_ref_button,           2, 1)
        grid_print_layout.addWidget(self.set_ref_button,          3, 1)
        grid_print_layout.addWidget(QtGui.QLabel('<strong> Print Laser'),  0, 3, 1, 2)
        grid_print_layout.addWidget(self.grid_laser,              1, 3, 1, 2)
        grid_print_layout.addWidget(self.umbralLabel,             3, 3)
        grid_print_layout.addWidget(self.umbralEdit,              4, 3)
        grid_print_layout.addWidget(self.tmaxLabel,               3, 4)
        grid_print_layout.addWidget(self.tmaxEdit,                4, 4)

    # Cosas para la parte del foco

    # Defino el tipo de laser que quiero para hacer foco
        self.focus_laser = QtGui.QComboBox()
        self.focus_laser.addItems(shutters)
        self.focus_laser.setCurrentIndex(2)
        self.focus_laser.setToolTip('Elijo el shuter para HACER FOCO')
        self.focus_laser.setFixedWidth(80)
        self.focus_laser.activated.connect(lambda: self.color_menu(self.focus_laser))
        self.color_menu(self.focus_laser)

    # Boton para Lockear el foco
        self.focus_lock_button = QtGui.QPushButton('Lock Focus')
        self.focus_lock_button.setCheckable(False)
        self.focus_lock_button.clicked.connect(self.focus_lock_focus)
        self.focus_lock_button.setToolTip('guarda el patron en el z actual')

    # Boton de Autocorrelacion, con el foco ya lockeado
        self.focus_autocorr_button = QtGui.QPushButton('Autocorrelacion')
        self.focus_autocorr_button.setCheckable(False)
        self.focus_autocorr_button.clicked.connect(self.focus_autocorr)
        self.focus_autocorr_button.setToolTip('guarda el patron en el z actual')

    # Go to maximun
        self.focus_gotomax_button = QtGui.QPushButton('go to maximun')
        self.focus_gotomax_button.setCheckable(False)
        self.focus_gotomax_button.clicked.connect(self.focus_go_to_maximun)
        self.focus_gotomax_button.setToolTip('guarda el patron en el z actual')

    # En otra grid poner las cosas del foco
        self.grid_focus = QtGui.QWidget()
        grid_focus_layout = QtGui.QGridLayout()
        self.grid_focus.setLayout(grid_focus_layout)
        grid_focus_layout.addWidget(self.focus_lock_button,       1, 1, 2, 1)
        grid_focus_layout.addWidget(self.focus_autocorr_button,   2, 1, 2, 1)
        grid_focus_layout.addWidget(self.focus_gotomax_button,    3, 1, 2, 1)
        grid_focus_layout.addWidget(QtGui.QLabel('<strong> Focus Laser'),  2, 2)
        grid_focus_layout.addWidget(self.focus_laser,             3, 2)

    # particles to autofocus
        self.autofocLabel = QtGui.QLabel('Particles after autofocus')
        self.autofocEdit = QtGui.QLineEdit('10')
        self.autofocEdit.setFixedWidth(40)
        self.autofocEdit.setToolTip('Cantida de impresiones hasta autofoquear ')

    # shift x
        self.shifxLabel = QtGui.QLabel('focus shift X [µm]')
        self.shiftxEdit = QtGui.QLineEdit('10')
        self.shiftxEdit.setFixedWidth(40)
        self.shiftxEdit.setToolTip('Para que haga el autofoco corrido ')

    # shift y
        self.shiftyLabel = QtGui.QLabel('focus shift Y [µm]')
        self.shiftyEdit = QtGui.QLineEdit('10')
        self.shiftyEdit.setFixedWidth(40)
        self.shiftyEdit.setToolTip('Para que haga el autofoco corrido ')

    # En otra grid poner las cosas del foco
        self.grid_shift = QtGui.QWidget()
        grid_shift_layout = QtGui.QGridLayout()
        self.grid_shift.setLayout(grid_shift_layout)
        grid_shift_layout.addWidget(self.autofocLabel, 1, 0)
        grid_shift_layout.addWidget(self.autofocEdit,  2, 0)
        grid_shift_layout.addWidget(self.shifxLabel,   3, 0)
        grid_shift_layout.addWidget(self.shiftxEdit,   4, 0)
        grid_shift_layout.addWidget(self.shiftyLabel,  5, 0)
        grid_shift_layout.addWidget(self.shiftyEdit,   6, 0)

    # separo tambien los shutters y flipper
        self.shuttersignal = [False, False, False]
    # Shutters buttons
        self.shutter0button = QtGui.QCheckBox('shutter Green')
        self.shutter0button.clicked.connect(self.shutter0)
        self.shutter0button.setStyleSheet("color: green; ")

        self.shutter1button = QtGui.QCheckBox('shutter Red')
        self.shutter1button.clicked.connect(self.shutter1)
        self.shutter1button.setStyleSheet("color: red; ")

        self.shutter2button = QtGui.QCheckBox('shutter Blue')
        self.shutter2button.clicked.connect(self.shutter2)
        self.shutter2button.setStyleSheet("color: blue; ")

        self.shutter0button.setToolTip('Open/close Green 532 Shutter')
        self.shutter1button.setToolTip('Open/close red 640 Shutter')
        self.shutter2button.setToolTip('Open/close blue 405 Shutter')

        self.power_check = QtGui.QCheckBox('Potencia')
#        self.power_check.setChecked(False)
        self.power_check.clicked.connect(self.power_change)
        self.power_check.setToolTip('Picado es baja, no picado es alta')
        self.power_change()

        self.grid_shutters = QtGui.QWidget()
        grid_shutters_layout = QtGui.QGridLayout()
        self.grid_shutters.setLayout(grid_shutters_layout)
        grid_shutters_layout.addWidget(self.shutter0button,        0, 1)
        grid_shutters_layout.addWidget(self.shutter1button,        1, 1)
        grid_shutters_layout.addWidget(self.shutter2button,        2, 1)
        grid_shutters_layout.addWidget(self.power_check,           1, 2, 2, 2)


    # boton de dimeros
        self.dimeros_button = QtGui.QPushButton("DIMEROS")
        self.dimeros_button.setCheckable(False)
#        self.dimeros_button.clicked.connect(self.focus_go_to_maximun)
        self.dimeros_button.setToolTip('no se que hace')

    # Go to maximun
        self.dimeros_next_button = QtGui.QPushButton("Next Dimer")
        self.dimeros_next_button.setCheckable(False)
#        self.dimeros_button.clicked.connect(self.focus_go_to_maximun)
        self.dimeros_next_button.setToolTip('empieza')

    # tiempo de espera dimeros
        self.t_waitLabel = QtGui.QLabel('t espera (s)')
        self.t_waitEdit = QtGui.QLineEdit('60')
        self.t_waitEdit.setFixedWidth(40)
        self.t_waitEdit.setToolTip('Tiempo que mantiene el laser prendido.')
        self.t_waitLabel.setToolTip('Tiempo que mantiene el laser prendido.')

    # Defino el tipo de laser que quiero para imprimir
        self.preescan_laser = QtGui.QComboBox()
        self.preescan_laser.addItems(shutters)
        self.preescan_laser.setCurrentIndex(1)
        self.preescan_laser.setToolTip('Elijo el shuter para Preescanear el que ya está')
        self.preescan_laser.setFixedWidth(80)
        self.preescan_laser.activated.connect(lambda: self.color_menu(self.preescan_laser))
        self.color_menu(self.preescan_laser)

    # Defino el tipo de laser que quiero para imprimir
        self.dimerscan_laser = QtGui.QComboBox()
        self.dimerscan_laser.addItems(shutters)
        self.dimerscan_laser.setCurrentIndex(2)
        self.dimerscan_laser.setToolTip('Elijo el shuter para escanear el dimero ')
        self.dimerscan_laser.setFixedWidth(80)
        self.dimerscan_laser.activated.connect(lambda: self.color_menu(self.dimerscan_laser))
        self.color_menu(self.dimerscan_laser)

#    # preescan laser
#        self.preescan_laser_532 = QtGui.QRadioButton('preescan 532')
#        self.preescan_laser_532.setChecked(True)
#        self.preescan_laser_405 = QtGui.QRadioButton('preescan 405')
#
#
#    # dimer scan laser
#        self.dimerscan_laser_532 = QtGui.QRadioButton('Dimer scan 532')
#        self.dimerscan_laser_532.setChecked(True)
#        self.dimerscan_laser_405 = QtGui.QRadioButton('Dimer scan 405')

    # En otra grid poner las cosas de crecimiento/Dimeros
        self.grid_grow = QtGui.QWidget()

#        group1 = QtGui.QButtonGroup(self.grid_grow)
#        group1.addButton(self.preescan_laser_532)
#        group1.addButton(self.preescan_laser_405)
#
#        group2 = QtGui.QButtonGroup(self.grid_grow)
#        group2.addButton(self.dimerscan_laser_532)
#        group2.addButton(self.dimerscan_laser_405)

        grid_grow = QtGui.QGridLayout()
        self.grid_grow.setLayout(grid_grow)
        grid_grow.addWidget(self.dimeros_button,       1, 0)
        grid_grow.addWidget(self.dimeros_next_button,  1, 1)
        grid_grow.addWidget(self.t_waitLabel,          3, 1)
        grid_grow.addWidget(self.t_waitEdit,           4, 1)
#        grid_grow.addWidget(self.preescan_laser_532,   3, 0)
#        grid_grow.addWidget(self.preescan_laser_405,   4, 0)
#        grid_grow.addWidget(self.dimerscan_laser_532,  3, 2)
#        grid_grow.addWidget(self.dimerscan_laser_405,  4, 2)
        
        grid_grow.addWidget(QtGui.QLabel('Pre scan Laser'),   4, 0)
        grid_grow.addWidget(QtGui.QLabel('Dimer scan Laser'),  4, 2)
        grid_grow.addWidget(self.preescan_laser,   5, 0)
        grid_grow.addWidget(self.dimerscan_laser,  5, 2)

        grid_grow.addWidget(QtGui.QLabel(''),          2, 0)
#        grid_grow.addWidget(QtGui.QLabel(''),          5, 0)
        grid_grow.addWidget(QtGui.QLabel(''),          6, 0)

#        grid_grow.addWidget(self.shiftyLabel,  5, 0)
#        grid_grow.addWidget(self.shiftyEdit,   6, 0)


# --- FIN COSAS PRINTING

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

        self.step = 1
        imageWidget = pg.GraphicsLayoutWidget()
        self.vb = imageWidget.addViewBox(row=1, col=1)

        self.point_graph_Gauss = pg.ScatterPlotItem(size=10,
                                                    symbol='o', color='m')
        self.point_graph_CM = pg.ScatterPlotItem(size=10,
                                                 symbol='+', color='m')

    # LiveView Button
        self.liveviewButton = QtGui.QPushButton('confocal LIVEVIEW')
        self.liveviewButton.setCheckable(True)
        self.liveviewButton.clicked.connect(self.liveview)
        self.liveviewButton.setStyleSheet(
                "QPushButton { background-color: green; }"
                "QPushButton:pressed { background-color: blue; }")
        self.liveviewButton.setToolTip('This is a tooltip message.')

    # save image Button
        self.saveimageButton = QtGui.QPushButton('Save Frame')
        self.saveimageButton.setCheckable(False)
        self.saveimageButton.clicked.connect(self.guardarimagen)
        self.saveimageButton.setStyleSheet(
                "QPushButton { background-color: rgb(200, 200, 10); }"
                "QPushButton:pressed { background-color: blue; }")

        label_save = QtGui.QLabel('Nombre del archivo')
        label_save.resize(label_save.sizeHint())
        self.edit_save = QtGui.QLineEdit('imagenScan')
        self.edit_save.resize(self.edit_save.sizeHint())

        self.edit_Name = str(self.edit_save.text())
        self.edit_save.textEdited.connect(self.save_name_update)
        self.save_name_update()
        tamaño = 110
        self.edit_save.setFixedWidth(tamaño)
        self.saveimageButton.setFixedWidth(tamaño)

#        self.NameDirButton = QtGui.QPushButton('select Dir')
#        self.NameDirButton.clicked.connect(self.selectFolder)
        self.file_path = os.path.abspath("")
#        self.OpenButton = QtGui.QPushButton('open dir')
#        self.OpenButton.clicked.connect(self.openFolder)
#        self.create_day_Button = QtGui.QPushButton('Create daily dir')
#        self.create_day_Button.clicked.connect(self.create_daily_directory)
        self.NameDirValue = QtGui.QLabel('')
        self.NameDirValue.setText(self.file_path)
        self.NameDirValue.setStyleSheet(" background-color: red; ")

    # Defino el tipo de Scan que quiero
        self.scanMode = QtGui.QComboBox()
        self.scanModes = ['step scan', 'ramp scan', 'otro scan']
        self.scanMode.addItems(self.scanModes)
        self.scanMode.setCurrentIndex(0)
#        self.scanMode.currentIndexChanged.connect(self.paramChanged)
        self.scanMode.setToolTip('Elijo el modo de escaneo')

    # Presets simil inspector
        self.presetsMode = QtGui.QComboBox()
        self.presetsModes = ['Manual', '500x0.01', '128x0.1']
        self.presetsMode.addItems(self.presetsModes)
        self.presetsMode.activated.connect(self.Presets)
        self.presetsMode.setFixedWidth(tamaño)
#        self.presetsMode.setStyleSheet("QComboBox{color: rgb(255,0,200);}\n")
#                     "background-color: transparent;\n"
#                     "background-image:url(background.png);}\n"
#                     "QComboBox QAbstractItemView{border: 0px;color:orange}")

    # to run continuously
        self.Continouscheck = QtGui.QCheckBox('Continous')
        self.Continouscheck.setChecked(False)

    # XZ PSF scan
        self.XYcheck = QtGui.QRadioButton('XZ psf scan')
        self.XYcheck.setChecked(True)

        self.XZcheck = QtGui.QRadioButton('XZ psf scan')
        self.XZcheck.setChecked(False)

        self.YZcheck = QtGui.QRadioButton('YZ psf scan')
        self.YZcheck.setChecked(False)

    # para que guarde todo (trazas de Alan)
        self.Alancheck = QtGui.QCheckBox('"VIDEO" save')
        self.Alancheck.setChecked(False)

    # Calcula el centro de la particula
        self.CMcheck = QtGui.QCheckBox('calcula CM')
        self.CMcheck.setChecked(False)
        self.CMcheck.clicked.connect(self.CMmeasure)

        self.Gausscheck = QtGui.QCheckBox('calcula Gauss')
        self.Gausscheck.setChecked(False)
        self.Gausscheck.clicked.connect(self.GaussMeasure)

    # Para alternar entre pasos de a 1 y de a 2 (en el programa final se va)
        self.stepcheck = QtGui.QCheckBox('hacerlo de a 2')
        self.stepcheck.clicked.connect(self.steptype)

#       This boolean is set to True when open the nidaq channels
        self.ischannelopen = False

    # Point scan
        self.PointButton = QtGui.QPushButton('TRAZA')
        self.PointButton.setCheckable(False)
        self.PointButton.clicked.connect(self.PointStart)
        self.PointLabel = QtGui.QLabel('<strong>0.00|0.00')
        self.PointButton.setToolTip('continuously measures the APDs (Ctrl+T)')

        self.PiontAction = QtGui.QAction(self)
        QtGui.QShortcut(
            QtGui.QKeySequence('Ctrl+T'), self, self.PointStart)

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
        self.pixelSizeValue = QtGui.QLineEdit('20')
        self.timeTotalLabel = QtGui.QLabel('tiempo total (s)')
#        self.timeTotalValue = QtGui.QLabel('')

        self.pixelSizeLabel.setToolTip('Anda tambien en labels')
        self.pixelSizeValue.setToolTip('y en los valores')

        self.actualizar = QtGui.QLineEdit('0.5')

#        newfont = QtGui.QFont("Times", 14, QtGui.QFont.Bold)
#        self.pixelSizeValue.setFont(newfont)

        self.onlyInt = QtGui.QIntValidator(0, 5000)
        self.numberofPixelsEdit.setValidator(self.onlyInt)
        self.onlypos = QtGui.QDoubleValidator(0, 1000, 10)
        self.pixelTimeEdit.setValidator(self.onlypos)
        self.scanRangeEdit.setValidator(self.onlypos)

        self.numberofPixelsEdit.textEdited.connect(self.PixelSizeChange)
        self.pixelSizeValue.textEdited.connect(self.NpixChange)
        self.scanRangeEdit.textEdited.connect(self.PixelSizeChange)

        self.CMxLabel = QtGui.QLabel('CM X')
        self.CMxValue = QtGui.QLabel('NaN')
        self.CMyLabel = QtGui.QLabel('CM Y')
        self.CMyValue = QtGui.QLabel('NaN')
        self.a = QtGui.QLineEdit('-1.5')
        self.b = QtGui.QLineEdit('-1.5')
        tamaño = 80
        self.a.setFixedWidth(tamaño)
        self.b.setFixedWidth(tamaño)
        self.numberofPixelsEdit.setFixedWidth(tamaño)
        self.pixelTimeEdit.setFixedWidth(tamaño)
        self.scanRangeEdit.setFixedWidth(tamaño)
        self.pixelSizeValue.setFixedWidth(tamaño)
#        self.a.textChanged.connect(self.paramChanged)
#        self.b.textChanged.connect(self.paramChanged)

        self.GaussxLabel = QtGui.QLabel('Gauss fit X')
        self.GaussxValue = QtGui.QLabel('NaN G')
        self.GaussyLabel = QtGui.QLabel('Gauss fit Y')
        self.GaussyValue = QtGui.QLabel('NaN G')

        self.plotLivebutton = QtGui.QPushButton('Plot this image')
        self.plotLivebutton.setChecked(False)
        self.plotLivebutton.clicked.connect(self.plotLive)
        self.plotLivebutton.clicked.connect(self.otroPlot)

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
        self.histogramROIButton.setToolTip('Visualize an histogram \
                                           in the selected ROI area')

    # ROI Lineal
        self.roiline = None
        self.ROIlineButton = QtGui.QPushButton('lineROIline')
        self.ROIlineButton.setCheckable(True)
        self.ROIlineButton.clicked.connect(self.ROIlinear)
        self.selectlineROIButton = QtGui.QPushButton('Plot line ROI')
        self.selectlineROIButton.clicked.connect(self.selectLineROI)

    # Max counts
        self.maxcountsLabel = QtGui.QLabel('Counts (max|mean)')
        self.maxcountsEdit = QtGui.QLabel('<strong> 0|0')
        newfont = QtGui.QFont("Times", 14, QtGui.QFont.Bold)
        self.maxcountsEdit.setFont(newfont)

        self.paramWidget = QtGui.QWidget()

#        grid = QtGui.QGridLayout()
#        self.setLayout(grid)
#        grid.addWidget(imageWidget, 0, 0)
#        grid.addWidget(self.paramWidget, 2, 1)

        subgrid = QtGui.QGridLayout()
        self.paramWidget.setLayout(subgrid)

        self.paramWidget2 = QtGui.QWidget()
        subgrid2 = QtGui.QGridLayout()
        self.paramWidget2.setLayout(subgrid2)

        group1 = QtGui.QButtonGroup(self.paramWidget)
        group1.addButton(self.XYcheck)
        group1.addButton(self.XZcheck)
        group1.addButton(self.YZcheck)

        self.aLabel = QtGui.QLabel('a')
        self.bLabel = QtGui.QLabel('b')

        group2 = QtGui.QButtonGroup(self.paramWidget)
        self.APDred = QtGui.QRadioButton("APD red")
        self.APDgreen = QtGui.QRadioButton("APD green")
        self.APDred.setChecked(True)
        self.APDgreen.setChecked(False)
        group2.addButton(self.APDred)
        group2.addButton(self.APDgreen)

#        subgrid.addWidget(self.shutter0button,        0, 1)
#        subgrid.addWidget(self.shutter1button,        1, 1)
#        subgrid.addWidget(self.shutter2button,        2, 1)
        subgrid.addWidget(QtGui.QLabel('         '),   0, 1)
        subgrid.addWidget(QtGui.QLabel('         '),   1, 1)
        subgrid.addWidget(QtGui.QLabel('         '),   2, 1)
        subgrid.addWidget(self.scanRangeLabel,         3, 1)
        subgrid.addWidget(self.scanRangeEdit,          4, 1)
        subgrid.addWidget(pixelTimeLabel,              5, 1)
        subgrid.addWidget(self.pixelTimeEdit,          6, 1)
        subgrid.addWidget(numberofPixelsLabel,         7, 1)
        subgrid.addWidget(self.numberofPixelsEdit,     8, 1)
        subgrid.addWidget(self.pixelSizeLabel,         9, 1)
        subgrid.addWidget(self.pixelSizeValue,        10, 1)
        subgrid.addWidget(self.liveviewButton,        11, 1)
        subgrid.addWidget(self.Continouscheck,        12, 1)
        subgrid.addWidget(QtGui.QLabel('Autolevels'), 13, 1)
        subgrid.addWidget(QtGui.QLabel('Img Check'),  14, 1)
        subgrid.addWidget(self.maxcountsLabel,        15, 1)
        subgrid.addWidget(self.maxcountsEdit,         16, 2, 2, 1)

    # Columna 2
#        subgrid2.addWidget(QtGui.QLabel("NameDir"),    0, 2)
#        subgrid2.addWidget(QtGui.QLabel("OpenDir"),    1, 2)
#        subgrid2.addWidget(QtGui.QLabel("CreateDir"),  2, 2)
#        subgrid2.addWidget(QtGui.QLabel("DetectMode"), 3, 2)
#        subgrid2.addWidget(QtGui.QLabel(""),           4, 2)

#        subgrid2.addWidget(self.aLabel,                1, 2)
        subgrid2.addWidget(self.a,                     1, 2)
#        subgrid2.addWidget(self.bLabel,                3, 2)
        subgrid2.addWidget(self.b,                     2, 2)
        subgrid2.addWidget(QtGui.QLabel("DetectMode"), 3, 2)
#        subgrid2.addWidget(QtGui.QLabel(""),           4, 2)
#        subgrid2.addWidget(QtGui.QLabel(""),           5, 2)
#        subgrid2.addWidget(self.umbralLabel,      4, 2)
#        subgrid2.addWidget(self.umbralEdit,       5, 2)
        subgrid2.addWidget(QtGui.QLabel(""),           4, 2)
        subgrid2.addWidget(QtGui.QLabel(""),           5, 2)
        subgrid2.addWidget(QtGui.QLabel(""),           6, 2)
        subgrid2.addWidget(self.stepcheck,             7, 2)
        subgrid2.addWidget(QtGui.QLabel(""),           8, 2)
        subgrid2.addWidget(self.Alancheck,             9, 2)
        subgrid2.addWidget(QtGui.QLabel(""),           10, 2)
        subgrid2.addWidget(label_save,                 11, 2)  # , 1, 2)
        subgrid2.addWidget(self.edit_save,             12, 2)  # , 1, 2)
        subgrid2.addWidget(self.saveimageButton,       13, 2)
        subgrid2.addWidget(QtGui.QLabel(""),           14, 2)
        subgrid2.addWidget(self.presetsMode,           15, 2)
        subgrid2.addWidget(self.timeTotalLabel,        16, 2)
#        subgrid2.addWidget(self.timeTotalValue,        17, 2)

#        subgrid.addWidget(self.APDred,                0, 1)
#        subgrid2.addWidget(self.APDgreen,              0, 2)

#        subgrid2.addWidget(self.XYcheck,                14, 2)
#        subgrid2.addWidget(self.XZcheck,                15, 2)
#        subgrid2.addWidget(self.YZcheck,                16, 2)

        self.paramWidget3 = QtGui.QWidget()
        subgrid3 = QtGui.QGridLayout()
        self.paramWidget3.setLayout(subgrid3)

    # Columna 3
        subgrid3.addWidget(self.ROIButton,            0, 3)
        subgrid3.addWidget(self.selectROIButton,      1, 3)
        subgrid3.addWidget(QtGui.QLabel(""),          2, 3)
        subgrid3.addWidget(self.ROIlineButton,        3, 3)
        subgrid3.addWidget(self.selectlineROIButton,  4, 3)
        subgrid3.addWidget(self.histogramROIButton,   6, 3)
        subgrid3.addWidget(QtGui.QLabel(""),          5, 3)
        subgrid3.addWidget(QtGui.QLabel(""),          7, 3)
        subgrid3.addWidget(QtGui.QLabel(""),          8, 3)
        subgrid3.addWidget(self.PointButton,          9, 3)
        subgrid3.addWidget(self.PointLabel,          10, 3)
        subgrid3.addWidget(QtGui.QLabel(""),         11, 3)
        subgrid3.addWidget(QtGui.QLabel("scanplot"), 12, 3)  # graphcheck
        subgrid3.addWidget(self.plotLivebutton,      13, 3)
        subgrid3.addWidget(QtGui.QLabel(""),         14, 3)
        subgrid3.addWidget(self.scanMode,            15, 3)
        subgrid3.addWidget(QtGui.QLabel("PSFMode"),  16, 3)

# --- POSITIONERRRRR-------------------------------

        # Axes control
        self.xLabel = QtGui.QLabel('1.0')
#            "<strong>x = {0:.2f} µm</strong>".format(self.x))
        self.xLabel.setTextFormat(QtCore.Qt.RichText)
        self.xname = QtGui.QLabel("<strong>x =")
        self.xname.setTextFormat(QtCore.Qt.RichText)
        self.xUpButton = QtGui.QPushButton("(+x) ►")  # →
        self.xUpButton.pressed.connect(
                       lambda: self.move("x",float(self.StepEdit.text())))
        self.xDownButton = QtGui.QPushButton("◄ (-x)")  # ←
        self.xDownButton.pressed.connect(
                       lambda: self.move("x",-float(self.StepEdit.text())))
        self.xStepEdit = QtGui.QLineEdit("1.0")  # estaban en 0.05<
#        self.xStepUnit = QtGui.QLabel(" µm")
        self.xUp2Button = QtGui.QPushButton("++x ►►")  # →
        self.xUp2Button.pressed.connect(
                       lambda: self.move("x",10*float(self.StepEdit.text())))
        self.xDown2Button = QtGui.QPushButton("◄◄ --x")  # ←
        self.xDown2Button.pressed.connect(
                       lambda: self.move("x",-10*float(self.StepEdit.text())))

        self.yLabel = QtGui.QLabel('2.0')
#            "<strong>y = {0:.2f} µm</strong>".format(self.y))
        self.yLabel.setTextFormat(QtCore.Qt.RichText)
        self.yname = QtGui.QLabel("<strong>y =")
        self.yname.setTextFormat(QtCore.Qt.RichText)
        self.yUpButton = QtGui.QPushButton("(+y) ▲")  # ↑
        self.yUpButton.pressed.connect(
                       lambda: self.move("y",float(self.StepEdit.text())))
        self.yDownButton = QtGui.QPushButton("(-y) ▼")  # ↓
        self.yDownButton.pressed.connect(
                       lambda: self.move("y",-float(self.StepEdit.text())))
        self.StepEdit = QtGui.QLineEdit("1.0")
#        self.yStepUnit = QtGui.QLabel(" µm")
        self.yUp2Button = QtGui.QPushButton("++y ▲▲")  # ↑
        self.yUp2Button.pressed.connect(
                       lambda: self.move("y",10*float(self.StepEdit.text())))
        self.yDown2Button = QtGui.QPushButton("--y ▼▼")  # ↓
        self.yDown2Button.pressed.connect(
                       lambda: self.move("y",-10*float(self.StepEdit.text())))


        self.zLabel = QtGui.QLabel('3.0')
#            "<strong>z = {0:.2f} µm</strong>".format(self.z))
        self.zLabel.setTextFormat(QtCore.Qt.RichText)
        self.zname = QtGui.QLabel("<strong>z =")
        self.zname.setTextFormat(QtCore.Qt.RichText)
        self.zUpButton = QtGui.QPushButton("+z ▲")
        self.zUpButton.pressed.connect(
                       lambda: self.zMoveUp())
        self.zDownButton = QtGui.QPushButton("-z ▼")
        self.zDownButton.pressed.connect(
                       lambda: self.zMoveDown())
        self.zStepEdit = QtGui.QLineEdit("1.0")
#        self.zStepUnit = QtGui.QLabel(" µm")
        self.zup2Button = QtGui.QPushButton("++z ▲▲")
        self.zup2Button.pressed.connect(
                       lambda: self.zMoveUp(10))
        self.zDown2Button = QtGui.QPushButton("--z ▼▼")
        self.zDown2Button.pressed.connect(
                       lambda: self.zMoveDown(10))


        tamaño = 30
        self.xLabel.setFixedWidth(tamaño)
        self.yLabel.setFixedWidth(tamaño)
        self.zLabel.setFixedWidth(tamaño)
        tamaño = 50
#        self.xStepUnit.setFixedWidth(tamaño)
#        self.yStepUnit.setFixedWidth(tamaño)
#        self.zStepUnit.setFixedWidth(tamaño)
        self.xUp2Button.setFixedWidth(tamaño)
        self.xDown2Button.setFixedWidth(tamaño)
        self.xUpButton.setFixedWidth(tamaño)
        self.xDownButton.setFixedWidth(tamaño)
        self.yUp2Button.setFixedWidth(tamaño)
        self.yDown2Button.setFixedWidth(tamaño)
        self.yUpButton.setFixedWidth(tamaño)
        self.yDownButton.setFixedWidth(tamaño)

        self.positioner = QtGui.QWidget()
#        grid.addWidget(self.positioner, 1, 0)
        layout = QtGui.QGridLayout()
        self.positioner.setLayout(layout)
        layout.addWidget(self.xname,        1, 0)
        layout.addWidget(self.xLabel,       1, 1)
        layout.addWidget(self.xUpButton,    2, 6, 2, 1)
        layout.addWidget(self.xDownButton,  2, 4, 2, 1)
        layout.addWidget(self.xUp2Button,   2, 7, 2, 1)
        layout.addWidget(self.xDown2Button, 2, 3, 2, 1)
#        layout.addWidget(QtGui.QLabel("Step x"), 1, 6)
#        layout.addWidget(self.xStepEdit, 1, 7)
#        layout.addWidget(self.xStepUnit, 1, 8)

        layout.addWidget(self.yname,       2, 0)
        layout.addWidget(self.yLabel,      2, 1)
        layout.addWidget(self.yUpButton,   1, 5, 3, 1)
        layout.addWidget(self.yDownButton, 3, 5, 2, 1)
        layout.addWidget(QtGui.QLabel("step xy µm) "), 4, 6, 1, 2)
        layout.addWidget(self.StepEdit,   5, 6)
#        layout.addWidget(self.yStepUnit,   5, 5)
        layout.addWidget(self.yUp2Button,   0, 5, 2, 1)
        layout.addWidget(self.yDown2Button, 4, 5, 2, 1)

        layout.addWidget(self.zname,       4, 0)
        layout.addWidget(self.zLabel,      4, 1)
        layout.addWidget(self.zup2Button,   0, 9, 2, 1)
        layout.addWidget(self.zUpButton,   1, 9, 3, 1)
        layout.addWidget(self.zDownButton, 3, 9, 2, 1)
        layout.addWidget(self.zDown2Button, 4, 9, 2, 1)
        layout.addWidget(QtGui.QLabel("step z (­­­µm)"), 4, 10)
        layout.addWidget(self.zStepEdit,   5, 10)
#        layout.addWidget(self.zStepUnit,   2, 7)

#        Hline =QtGui.QLabel("________________________________________________________________________________________________")
#        Hline.setFixedWidth(300)
#        layout.addWidget(Hline,7, 0,1,7)


        layout.addWidget(self.NameDirValue, 8, 0, 1, 7)

        tamaño = 40
        self.StepEdit.setFixedWidth(tamaño)
        self.zStepEdit.setFixedWidth(tamaño)
#        self.yStepEdit.setValidator(self.onlypos)
#        self.zStepEdit.setValidator(self.onlypos)
        layout.addWidget(QtGui.QLabel("|"),  1, 2)
        layout.addWidget(QtGui.QLabel("|"),  2, 2)
        layout.addWidget(QtGui.QLabel("|"),  3, 2)
        layout.addWidget(QtGui.QLabel("|"),  4, 2)
        layout.addWidget(QtGui.QLabel("|"),  5, 2)

        layout.addWidget(QtGui.QLabel("|"),  1, 8)
        layout.addWidget(QtGui.QLabel("|"),  2, 8)
        layout.addWidget(QtGui.QLabel("|"),  3, 8)
        layout.addWidget(QtGui.QLabel("|"),  4, 8)
        layout.addWidget(QtGui.QLabel("|"),  5, 8)


        self.gotoWidget = QtGui.QWidget()
#        grid.addWidget(self.gotoWidget, 1, 1)
        layout2 = QtGui.QGridLayout()
        self.gotoWidget.setLayout(layout2)
        layout2.addWidget(QtGui.QLabel("X [µm]"), 1, 1)
        layout2.addWidget(QtGui.QLabel("Y [µm]"), 2, 1)
        layout2.addWidget(QtGui.QLabel("Z [µm]"), 3, 1)
        self.xgotoLabel = QtGui.QLineEdit("0.000")
        self.ygotoLabel = QtGui.QLineEdit("0.000")
        self.zgotoLabel = QtGui.QLineEdit("0.000")
        self.gotoButton = QtGui.QPushButton("♫ G0 To ♪")
        self.gotoButton.pressed.connect(self.goto)
        layout2.addWidget(self.gotoButton, 1, 5, 2, 2)
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
        layout3.addWidget(self.goCMButton, 1, 4, 1, 2)
        layout3.addWidget(self.CMcheck, 1, 1, 1, 2)

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
        layout3.addWidget(self.goCMButton, 2, 4, 1, 2)  # , 2, 2)
        layout3.addWidget(self.Gausscheck, 2, 1, 1, 2)
# --- fin POSITIONEERRRRRR---------------------------


# ----DOCKs, mas comodo!
        self.state = None
        hbox = QtGui.QHBoxLayout(self)
        dockArea = DockArea()

        viewDock = Dock('viewbox', size=(500, 450))
        viewDock.addWidget(imageWidget)
        viewDock.hideTitleBar()
        dockArea.addDock(viewDock, 'left')

        scanDock = Dock('Scan parameters', size=(1, 1))
        scanDock.addWidget(self.paramWidget)
        dockArea.addDock(scanDock, 'right', viewDock)

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
        dockArea.addDock(scanDock2, 'left', scanDock3)

        grid_print_dock = Dock('Printing grids', size=(5, 10))
        grid_print_dock.addWidget(self.grid_print)
        dockArea.addDock(grid_print_dock, 'bottom')

        grid_focus_dock = Dock('Focus cosas', size=(1, 1))
        grid_focus_dock.addWidget(self.grid_focus)
        dockArea.addDock(grid_focus_dock, 'bottom', scanDock2)

        grid_shift_dock = Dock('Focus shift', size=(1, 1))
        grid_shift_dock.addWidget(self.grid_shift)
        dockArea.addDock(grid_shift_dock, 'right', grid_print_dock)

        shutters_dock = Dock('Shutters', size=(1, 1))
        shutters_dock.addWidget(self.grid_shutters)
        dockArea.addDock(shutters_dock, 'bottom', scanDock3)

        grow_dock = Dock('Dimeros/Crecimiento', size=(1, 1))
        grow_dock.addWidget(self.grid_grow)
        dockArea.addDock(grow_dock, 'right', grid_shift_dock)

        hbox.addWidget(dockArea)
        self.setLayout(hbox)
#        self.setGeometry(10, 40, 300, 800)  # (PosX, PosY, SizeX, SizeY)
#        self.setWindowTitle('Py Py Python scan')
#        self.setFixedHeight(550)

#        self.paramWidget.setFixedHeight(500)

        self.vb.setMouseMode(pg.ViewBox.PanMode)
        self.img = pg.ImageItem()
        self.img.translate(-0.5, -0.5)
        self.vb.addItem(self.img)
        self.vb.setAspectLocked(True)
        imageWidget.setAspectLocked(True)
        self.hist = pg.HistogramLUTItem(image=self.img)
        self.hist.gradient.loadPreset('thermal')  # thermal
# 'thermal', 'flame', 'yellowy', 'bipolar', 'spectrum',
# 'cyclic', 'greyclip', 'grey' # Solo son estos
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

        self.imageWidget = imageWidget

        self.liveviewAction = QtGui.QAction(self)
#        self.liveviewAction.setShortcut('Ctrl+a')
        QtGui.QShortcut(
            QtGui.QKeySequence('Ctrl+a'), self, self.liveviewKey)
#        self.liveviewAction.triggered.connect(self.liveviewKey)
#        self.liveviewAction.setEnabled(True)

        self.Presets()
#        save_docks()
        self.dockArea = dockArea
        self.paramChanged()


# --- Cosas pequeñas que agregue
    def PixelSizeChange(self):
        scanRange = float(self.scanRangeEdit.text())
        numberofPixels = int(self.numberofPixelsEdit.text())
        self.pixelSize = scanRange/numberofPixels
        self.pixelSizeValue.setText('{}'.format(
                                        np.around(1000 * self.pixelSize, 2)))
        pixelTime = float(self.pixelTimeEdit.text()) / 10**3
        self.timeTotalLabel.setText("Tiempo total(s)= "+'{}'.format(np.around(
                         numberofPixels**2 * pixelTime, 2)))

    def NpixChange(self):
        scanRange = float(self.scanRangeEdit.text())
        pixelSize = float(self.pixelSizeValue.text())/1000
        self.numberofPixelsEdit.setText('{}'.format(int(scanRange/pixelSize)))
        pixelTime = float(self.pixelTimeEdit.text()) / 10**3
        self.timeTotalLabel.setText("Tiempo total(s)= "+'{}'.format(np.around(
                         int(scanRange/pixelSize)**2 * pixelTime, 2)))

# %%--- paramChanged / PARAMCHANGEDinitialize
    def paramChangedInitialize(self):
        a = [self.scanRange, self.numberofPixels, self.pixelTime,
             self.initialPosition, self.scanModeSet]
        b = [float(self.scanRangeEdit.text()),
             int(self.numberofPixelsEdit.text()),
             float(self.pixelTimeEdit.text()) / 10**3,
             (float(self.xLabel.text()), float(self.yLabel.text()),
              float(self.zLabel.text())),
             self.scanMode.currentText()]
        print("\n", a)
        print(b, "\n")

        if a == b:
            print("\n no cambió ningun parametro\n")
        else:
            print("\n pasaron cosas\n")
            self.paramChanged()

    def paramChanged(self):

        self.scanModeSet = self.scanMode.currentText()
#        self.PSFModeSet = self.PSFMode.currentText()

        self.scanRange = float(self.scanRangeEdit.text())
#        self.scanRangey = self.scanRangex  # float(self.scanRangeyEdit.text())

        self.numberofPixels = int(self.numberofPixelsEdit.text())
        self.pixelTime = float(self.pixelTimeEdit.text()) / 10**3

        self.Napd = int(np.round(apdrate * self.pixelTime))

        print(self.Napd, "Napd")
        self.initialPosition = (float(self.xLabel.text()),
                                float(self.yLabel.text()),
                                float(self.zLabel.text()))

        print(self.initialPosition)

        self.pixelSize = self.scanRange/self.numberofPixels

        self.pixelSizeValue.setText('{}'.format(np.around(
                                        1000 * self.pixelSize, 2)))  # en nm

#        newfont = QtGui.QFont("Times", 14, QtGui.QFont.Bold)
#        self.pixelSizeValue.setFont(newfont)


#        self.linetime = (1/1000)*float(
#                self.pixelTimeEdit.text())*int(self.numberofPixelsEdit.text())
        self.linetime = self.pixelTime * self.numberofPixels

        print(self.linetime, "linetime")

        self.timeTotalLabel.setText("Tiempo total (s)= "+'{}'.format(np.around(
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

    def steptype(self):
        if self.stepcheck.isChecked():
            self.step = 2
            print("step es 2", self.step == 2)
        else:
            self.step = 1
            print("step es 1", self.step == 1)
        self.paramChanged()

# %% Liveview
# This is the function triggered by pressing the liveview button
    def liveview(self):
        """ Image live view when not recording"""
        if self.liveviewButton.isChecked():
            self.paramChangedInitialize()
            self.openShutter(shutters[0])
            self.liveviewStart()

        else:
            self.liveviewStop()

    def liveviewStart(self):
        self.maxcountsEdit.setStyleSheet(" background-color: ")
        if self.scanMode.currentText() in ["step scan", "ramp scan"]:
            self.tic = ptime.time()
            self.viewtimer.start(self.linetime)
        else:
            print("elegri step o ramp scan")
            self.liveviewButton.setChecked(False)
#        if self.detectMode.currentText() == "PMT":
#            # channelopen PMT
#            print("PMT")

    def liveviewStop(self):
        self.closeShutter(shutters[0])
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
            ptime.sleep(0.1)

        if self.XZcheck.isChecked():
            print("intercambio y por z")  # falla si y,z iniciales son iguales

        if self.step == 1:
            self.lineData = self.cuentas  # self.inputImage[:, self.dy]
            self.image[:, -1-self.i] = self.lineData  # f
        else:
            cuentas2 = np.split(self.cuentas, 2)
            self.lineData = cuentas2[0]  # self.inputImage[:, self.dy]
            lineData2 = cuentas2[1]

    #        self.lineData = self.inputImage[:, self.i]  # + 2.5*self.i
    #        lineData2 = self.inputImage[:, self.i + 1]
            self.image[:, self.numberofPixels-1-self.i] = self.lineData  # f
            self.image[:, self.numberofPixels-2-self.i] = lineData2  # f

#        self.image[25, self.i] = 333
#        self.image[9, -self.i] = 333

        self.img.setImage(self.image, autoLevels=False)
        self.MaxCounts()

        time = (ptime.time()-self.tic)
        self.actualizar.setText("{}".format(str(time)))
        if self.i < self.numberofPixels-self.step:
            self.i = self.i + self.step
        else:
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

# %% MAX Counts
    def MaxCounts(self):
        m = np.max(self.image)
        m2 = np.mean(self.image)
        m3 = np.median(self.image)
        m4 = np.min(self.image)
        self.maxcountsEdit.setText("<strong> {}|{}".format(int(m), int(m2)) +
                                   " \n" + " {}|{}".format(int(m3), int(m4)))
        maxsecure = 5  # (5000 * self.pixelTime*10**3)
        if m >= maxsecure or m2 >= maxsecure:
            self.maxcountsEdit.setStyleSheet(" background-color: red; ")

# %% Barridos
    def barridos(self):
        N = self.numberofPixels
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
                if Z[i, j] < 0:
                    Z[i, j] = 0.1
        self.Z = Z
        print("barridos")

    def linea(self):
        Z = self.Z
        if self.step == 1:
            self.cuentas = Z[self.i, :] * abs(
                        np.random.normal(size=(1, self.numberofPixels))[0])*20
#            for i in range(self.numberofPixels):
#                borrar = 2
#            time.sleep(self.pixelTime*self.numberofPixels)
    #        print("linea")

        else:  # para hacerlo de a lineas y que no sea de 2 en 2:
            self.cuentas = np.zeros((2 * self.numberofPixels))
            self.cuentas = np.concatenate((Z[self.i, :], Z[self.i+1, :]))
            # np.random.normal(size=(1, 2*self.numberofPixels))[0]
#            for i in range(self.numberofPixels * 2):
#                borrar = 2
#            time.sleep(self.pixelTime*self.numberofPixels*2)
    #        print("linea")

# %% MovetoStart
    def MovetoStart(self):
        t = self.moveTime
#        N = self.moveSamples
        tic = ptime.time()
#        startY = float(self.initialPosition[1])
#        maximoy = startY + ((self.i+1) * self.pixelSize)
#        volviendoy = np.linspace(maximoy, startY, N)
#        volviendox = np.ones(len(volviendoy)) * float(self.initialPosition[0])
#        volviendoz = np.ones(len(volviendoy)) * float(self.initialPosition[2])
#        for i in range(len(volviendoy)):
#            borrar = volviendoy[i] + volviendox[i] + volviendoz[i]
#            self.aotask.write(
#                 [volviendox[i] / convFactors['x'],
#                  volviendoy[i] / convFactors['y'],
#                  volviendoz[i] / convFactors['z']], auto_start=True)
#            time.sleep(t / N)
        print(t, "vs", np.round(ptime.time() - tic, 2))
        self.i = 0
        self.Z = self.Z  # + np.random.choice([1,-1])*0.01

# %%--- Guardar imagen SAVE
    def save_name_update(self):
        self.edit_Name = str(self.edit_save.text())
        self.number = 0
        print("Actualizo el save name")

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
#        self.file_path = newpath
#        self.NameDirValue.setText(self.file_path)
#        self.NameDirValue.setStyleSheet(" background-color: ; ")

    def guardarimagen(self):
        try:
            # filepath = self.file_path
            filepath = self.main.file_path
    #        filepath = "C:/Users/Santiago/Desktop/Germán Tesis de lic/
    #    Winpython (3.5.2 para tormenta)/WinPython-64bit-3.5.2.2/notebooks/"
#            timestr = time.strftime("%Y%m%d-%H%M%S")  + str(self.number)
            name = str(filepath + "/" + str(self.edit_save.text()) + ".tiff")
            guardado = Image.fromarray(np.transpose(np.flip(self.image, 1)))
            guardado.save(name)
            self.number = self.number + 1
            self.edit_save.setText(self.edit_Name + str(self.number))
            print("\n Guardo la imagen\n")
        except IOError as e:
            print("I/O error({0}): {1}".format(e.errno, e.strerror))

# %%---Move----------------------------------------
    def move(self, axis, dist):
        """moves the position along the axis specified a distance dist."""
#        t = self.moveTime
#        N = self.moveSamples
        # read initial position for all channels
        texts = [getattr(self, ax + "Label").text()
                 for ax in self.activeChannels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]
        initPos = np.array(initPos, dtype=float)[:, np.newaxis]
        fullPos = np.repeat(initPos, self.nSamples, axis=1)

        # make position ramp for moving axis
        ramp = np.linspace(0, dist, self.nSamples)
        fullPos[self.activeChannels.index(axis)] += ramp

#        factors = np.array([convFactors['x'], convFactors['y'],
#                           convFactors['z']])[:, np.newaxis]
#        fullSignal = fullPos/factors
        toc = ptime.time()
#        for i in range(self.nSamples):
#            self.aotask.write(fullSignal, auto_start=True)
#            time.sleep(t / N)
#            borrar = 1+1

        print("se mueve en", np.round(ptime.time() - toc, 3), "segs")

        # update position text
        newPos = fullPos[self.activeChannels.index(axis)][-1]
#        newText = "<strong>" + axis + " = {0:.2f} µm</strong>".format(newPos)
        newText = "{}".format(newPos)
        getattr(self, axis + "Label").setText(newText)
        self.paramChanged()

#    def xMoveUp(self):
#        self.move('x', float(getattr(self, 'y' + "StepEdit").text()))
#
#    def xMoveDown(self):
#        self.move('x', -float(getattr(self, 'y' + "StepEdit").text()))
#
#    def yMoveUp(self):
#        self.move('y', float(getattr(self, 'y' + "StepEdit").text()))
#
#    def yMoveDown(self):
#        self.move('y', -float(getattr(self, 'y' + "StepEdit").text()))

    def zMoveUp(self, algo=1):
        self.move('z', algo*float(getattr(self, 'z' + "StepEdit").text()))
        self.zDownButton.setEnabled(True)
        self.zDownButton.setStyleSheet(
            "QPushButton { background-color: }")
        self.zStepEdit.setStyleSheet("background-color: ")
        self.zDown2Button.setStyleSheet("background-color: ")

    def zMoveDown(self,algo=1):
        PosZ = self.initialPosition[2]
        if PosZ < algo*float(getattr(self, 'z' + "StepEdit").text()):
            print("OJO!, te vas a Z's negativos")
            self.zStepEdit.setStyleSheet(" background-color: red; ")
#            setStyleSheet("color: rgb(255, 0, 255);")
        else:
            self.move('z', -algo*float(getattr(self, 'z' + "StepEdit").text()))
            self.zStepEdit.setStyleSheet(" background-color: ")
            if self.initialPosition[2] == 0:  # para no ir a z negativo
                self.zDownButton.setStyleSheet(
                    "QPushButton { background-color: orange; }")
                self.zDown2Button.setStyleSheet(
                    "QPushButton { background-color: orange; }")
        if PosZ == 0:  # para no ir a z negativo
            self.zDownButton.setStyleSheet(
                "QPushButton { background-color: red; }"
                "QPushButton:pressed { background-color: blue; }")
            self.zDownButton.setEnabled(False)

# %% Go Cm, go Gauss y go to
    def goCM(self):

        self.zgotoLabel.setStyleSheet(" background-color: ")
        print("arranco en", float(self.xLabel.text()),
              float(self.yLabel.text()), float(self.zLabel.text()))

        startX = float(self.xLabel.text())
        startY = float(self.yLabel.text())
        self.moveto((float(self.CMxValue.text()) + startX)-(self.scanRange/2),
                    (float(self.CMyValue.text()) + startY)-(self.scanRange/2),
                    float(self.zLabel.text()))

        print("termino en", float(self.xLabel.text()),
              float(self.yLabel.text()), float(self.zLabel.text()))

    def goGauss(self):
        rango2 = self.scanRange/2
        self.zgotoLabel.setStyleSheet(" background-color: ")
        print("arranco en", float(self.xLabel.text()),
              float(self.yLabel.text()), float(self.zLabel.text()))

        startX = float(self.xLabel.text())
        startY = float(self.yLabel.text())
        self.moveto((float(self.GaussxValue.text()) + startX) - rango2,
                    (float(self.GaussyValue.text()) + startY) - rango2,
                    float(self.zLabel.text()))

        print("termino en", float(self.xLabel.text()),
              float(self.yLabel.text()), float(self.zLabel.text()))

    def goto(self):

        if float(self.zgotoLabel.text()) < 0:
            QtGui.QMessageBox.question(self, '¿¡ Como pusiste z negativo !?',
                                       'Algo salio mal. :(  Avisar')
            print("Z no puede ser negativo!!!")
            self.zgotoLabel.setStyleSheet(" background-color: red")
            time.sleep(1)

        else:
            self.zgotoLabel.setStyleSheet(" background-color: ")
            print("arranco en", float(self.xLabel.text()),
                  float(self.yLabel.text()), float(self.zLabel.text()))

            self.moveto(float(self.xgotoLabel.text()),
                        float(self.ygotoLabel.text()),
                        float(self.zgotoLabel.text()))

            print("termino en", float(self.xLabel.text()),
                  float(self.yLabel.text()), float(self.zLabel.text()))

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
#        t = self.moveTime * 3
#        N = self.moveSamples * 3
        # read initial position for all channels
        texts = [getattr(self, ax + "Label").text()
                 for ax in self.activeChannels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]
        # falta el :  / convFactors['x']
        rampx = np.linspace(float(initPos[0]), x, self.nSamples)
        rampy = np.linspace(float(initPos[1]), y, self.nSamples)
        rampz = np.linspace(float(initPos[2]), z, self.nSamples)
#        ramp = np.array((rampx, rampy, rampz))

        tuc = ptime.time()
#        for i in range(self.nSamples):
#            borrar = rampx[i] + rampy[i] + rampz[i]
#            self.aotask.write([rampx[i] / convFactors['x'],
#                               rampy[i] / convFactors['y'],
#                               rampz[i] / convFactors['z']], auto_start=True)
#            time.sleep(t / N)

        print("se mueve todo en", np.round(ptime.time()-tuc, 3), "segs")

        self.xLabel.setText("{}".format(np.around(float(rampx[-1]), 2)))
        self.yLabel.setText("{}".format(np.around(float(rampy[-1]), 2)))
        self.zLabel.setText("{}".format(np.around(float(rampz[-1]), 2)))

# %%--- Shutter time --------------------------

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
#        self.shuttertask.write(self.shuttersignal, auto_start=True)
        print(self.shuttersignal)
        self.checkShutters()
        print("open", p)

    def closeShutter(self, p):
        for i in range(len(shutters)):
            if p == shutters[i]:
                self.shuttersignal[i] = False
#        self.shuttertask.write(self.shuttersignal, auto_start=True)
        print(self.shuttersignal)
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
#        if self.shuttergreen.isChecked():
#            print("shutter verde")
#
#        if self.shutterotro.isChecked():
#            print("shutter otro")
# Es una idea de lo que tendria que hacer la funcion

# %% rampas
    def rampas(self):
        N = self.numberofPixels
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
                if Z[i, j] < 0:
                    Z[i, j] = 0
        self.Z = Z
        print("rampsa")

    def linearampa(self):
        Z = self.Z
        if self.step == 1:
            self.cuentas = np.zeros((self.numberofPixels))
            self.cuentas = Z[self.i, :] * 5
#            for i in range(self.numberofPixels):
#                borrar = 2
#            time.sleep(self.pixelTime*self.numberofPixels)
    #        print("linearampa")
        else:  # para hacerlo de a lineas y que no sea de 2 en 2:
            self.cuentas = np.concatenate((Z[self.i, :], Z[self.i+1, :]))
#            for i in range(2*self.numberofPixels):
#                borrar = 2
#            time.sleep(self.pixelTime*2*self.numberofPixels)

# %%--- ploting in live
    def plotLive(self):
        Channels = self.activeChannels
        texts = [getattr(self, ax + "Label").text() for ax in Channels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]

        xv = np.linspace(0, self.scanRange,
                         self.numberofPixels) + float(initPos[0])
        yv = np.linspace(0, self.scanRange,
                         self.numberofPixels) + float(initPos[1])
        X, Y = np.meshgrid(xv, yv)
        fig, ax = plt.subplots()
        p = ax.pcolor(X, Y, np.transpose(self.image), cmap=plt.cm.jet)
        fig.colorbar(p)  # cb =

        ax.set_xlabel('x [um]')
        ax.set_ylabel('y [um]')
        try:
            xc = int(np.floor(self.xcm))
            yc = int(np.floor(self.ycm))
            X2 = np.transpose(X)
            Y2 = np.transpose(Y)
            resol = 2
            for i in range(resol):
                for j in range(resol):
                    ax.text(X2[xc+i, yc+j], Y2[xc+i, yc+j], "CM", color='m')
            Normal = self.scanRange / self.numberofPixels  # Normalizo
            ax.set_title((self.xcm*Normal + float(initPos[0]),
                          self.ycm*Normal + float(initPos[1])))
        except:
            pass
        try:
            (height, x, y, width_x, width_y) = self.params
            xg = int(np.floor(x))  # GaussxValue
            yg = int(np.floor(y))
            resol = 2
            for i in range(resol):
                for j in range(resol):
                    ax.text(X[xg+i, yg+j], Y[xg+i, yg+j], "Ga", color='m')
#                    ax.text(xv[int(x)+i], yv[int(y)+j], "GS", color='m')
            plt.text(0.95, 0.05, """
                    x : %.1f
                    y : %.1f """ % (X[xg, yg], Y[xg, yg]),
                     fontsize=16, horizontalalignment='right',
                     verticalalignment='bottom', transform=ax.transAxes)

        except:
            pass
        plt.show()

    def otroPlot(self):
        Channels = self.activeChannels
        texts = [getattr(self, ax + "Label").text() for ax in Channels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]
        xv = np.linspace(0, self.scanRange,
                         self.numberofPixels) + float(initPos[0])
        yv = np.linspace(0, self.scanRange,
                         self.numberofPixels) + float(initPos[1])
        X, Y = np.meshgrid(xv, yv)
#        data = np.flip(np.flip(self.image,0),1)
        try:
            plt.matshow(self.data, cmap=plt.cm.gist_earth_r, origin='lower',
                        interpolation='none',
                        extent=[xv[0], xv[-1], yv[0], yv[-1]])
            plt.colorbar()
            plt.grid(True)
            plt.contour(self.fit(*np.indices(self.data.shape)),
                        cmap=plt.cm.copper, interpolation='none',
                        extent=[xv[0], xv[-1], yv[0], yv[-1]])
            ax = plt.gca()
            (height, x, y, width_x, width_y) = self.params
#            xv = np.flip(xv)
#            yv = np.flip(yv)

            xc = int(np.floor(x))
            yc = int(np.floor(y))
            resol = 2
            xsum, ysum = 0, 0
            for i in range(resol):
                for j in range(resol):
                    ax.text(X[xc+i, yc+j], Y[xc+i, yc+j], "Ga", color='m')
                    xsum = X[xc+i, yc+j] + xsum
                    ysum = Y[xc+i, yc+j] + ysum
            xmean = xsum / (resol**2)
            ymean = ysum / (resol**2)
            ax.text(xmean, ymean, "✔", color='r')
#            Normal = self.scanRange / self.numberofPixels  # Normalizo
#            ax.set_title((self.xcm*Normal + float(initPos[0]),
#                          self.ycm*Normal + float(initPos[1])))
            plt.text(0.95, 0.05, """x : %.2f y : %.2f """
                     % (xmean, ymean),  # X[xc, yc], Y[xc, yc]
                     fontsize=16, horizontalalignment='right',
                     verticalalignment='bottom', transform=ax.transAxes)
            print("x", xv[int(x)], X[xc, yc], xmean)
#            Normal = self.scanRange / self.numberofPixels  # Normalizo
            ax.set_title("Centro en x={:.3f}, y={:.3f}".format(xmean, ymean))
            plt.show()
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

# %% GaussMeasure
    def GaussMeasure(self):
        tic = ptime.time()
        self.data = np.transpose(self.image)  # np.flip(np.flip(self.image,0),1
        params = fitgaussian(self.data)
        self.fit = gaussian(*params)
        self.params = params
        new_params = fitgaussian(self.image)
#        new_fit = gaussian(*new_params)
        (height, x, y, width_x, width_y) = new_params


#        Channels = self.activeChannels
#        texts = [getattr(self, ax + "Label").text() for ax in Channels]
#        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]
#        xv = np.linspace(0, self.scanRange,
#                         self.numberofPixels) + float(initPos[0])
#        yv = np.linspace(0, self.scanRange,
#                         self.numberofPixels) + float(initPos[1])

        Normal = self.scanRange / self.numberofPixels  # Normalizo
        xx = x*Normal
        yy = y*Normal

        R = self.scanRange
        if 0 < xx < R and 0 < yy < R:
            self.GaussxValue.setText("{:.2}".format(xx))
            self.GaussyValue.setText("{:.2}".format(yy))
            self.point_graph_Gauss.setData([x], [y])
            self.vb.addItem(self.point_graph_Gauss)
        else:
            self.GaussxValue.setText("{:.2}".format(np.nan))
            self.GaussyValue.setText("{:.2}".format(np.nan))
            print("OJO, el ajuste gaussiano no dio bien")
            try:
                self.vb.removeItem(self.point_graph_Gauss)
            except:
                pass

        tac = ptime.time()
        print(np.round((tac-tic)*10**3, 3), "(ms)solo Gauss\n")

# %% buttos to open and select folder
    def selectFolder(self):
        root = tk.Tk()
        root.withdraw()

        self.file_path = filedialog.askdirectory()
        print(self.file_path, 2)
        self.NameDirValue.setText(self.file_path)
        self.NameDirValue.setStyleSheet(" background-color: ; ")

    def openFolder(self):
        os.startfile(self.file_path)

# %%--- CM measure
    def CMmeasure(self):
        self.viewtimer.stop()
        I = self.image
#        N = len(I)  # numberfoPixels
        xcm, ycm = ndimage.measurements.center_of_mass(I)
        print("Xcm=", xcm, "\nYcm=", ycm)
        self.xcm = xcm
        self.ycm = ycm

        Normal = self.scanRange / self.numberofPixels  # Normalizo
        self.CMxValue.setText("{:.2}".format(xcm*Normal))
        self.CMyValue.setText("{:.2}".format(ycm*Normal))

        self.point_graph_CM.setData([xcm], [ycm])

        self.vb.addItem(self.point_graph_CM)

# %%  ROI cosas
    def ROImethod(self):
        size = (int(self.numberofPixels / 2), int(self.numberofPixels / 2))
        if self.roi is None:

            ROIpos = (0.5 * self.numberofPixels - 64,
                      0.5 * self.numberofPixels - 64)
            self.roi = viewbox_tools.ROI(self.numberofPixels, self.vb,
                                         ROIpos, size,
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
                                             ROIpos, size,
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

# %% --- Histogram

    def histogramROI(self):
        # ***----
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
        # ***----

        if self.histogramROIButton.isChecked():
            size = (int(self.numberofPixels / 2), int(self.numberofPixels / 2))
            ROIpos = (0.25 * self.numberofPixels,
                      0.25 * self.numberofPixels)
            self.roihist = viewbox_tools.ROI(self.numberofPixels, self.vb,
                                             ROIpos, size,
                                             handlePos=(1, 0),
                                             handleCenter=(0, 1),
                                             scaleSnap=True,
                                             translateSnap=True)
            self.roihist.sigRegionChanged.connect(updatehistogram)

            try:
                self.LinearWidget.deleteLater()
            except:
                pass
            try:
                self.HistoWidget.deleteLater()
            except:
                pass
            self.HistoWidget = pg.GraphicsLayoutWidget()
            self.p6 = self.HistoWidget.addPlot(row=2, col=1)

            self.p6.showGrid(x=True, y=True)
            self.p6.setLabel('left', 'Number of pixels with this counts')
            self.p6.setLabel('bottom', 'counts')
            self.p6.setLabel('right', '')
            self.curve = self.p6.plot(open='y')
            self.actualizar.textChanged.connect(updatehistogram)
            self.otrosDock.addWidget(self.HistoWidget)
            updatehistogram()

        else:
            self.actualizar.textChanged.disconnect()
#            self.roihist.sigRegionChanged.disconnect()
            self.vb.removeItem(self.roihist)
            self.roihist.hide()
#            self.otrosDock.removeWidget(self.HistoWidget)
#            self.HistoWidget.deleteLater()


# %%  ROI LINEARL
    def ROIlinear(self):
        larg = self.numberofPixels/1.5+10

    # ---
        def updatelineal():
            array = self.linearROI.getArrayRegion(self.image, self.img)
            self.curve.setData(array)

            m = np.mean(array)
            m2 = np.max(array)
            self.PointLabel.setText("<strong>{0:.2e}|{0:.2e}".format(
                                    float(m), float(m2)))
    # ---
        if self.ROIlineButton.isChecked():

            self.linearROI = pg.LineSegmentROI([[10, 64], [larg, 64]], pen='m')
            self.vb.addItem(self.linearROI)
            self.linearROI.sigRegionChanged.connect(updatelineal)

            try:
                self.HistoWidget.deleteLater()
            except:
                pass
            try:
                self.LinearWidget.deleteLater()
            except:
                pass

            self.LinearWidget = pg.GraphicsLayoutWidget()
            self.p6 = self.LinearWidget.addPlot(row=2, col=1,
                                                title="Linear plot")
            self.p6.showGrid(x=True, y=True)
            self.curve = self.p6.plot(open='y')
            self.otrosDock.addWidget(self.LinearWidget)
            self.actualizar.textChanged.connect(updatelineal)
            updatelineal()

        else:
            self.actualizar.textChanged.disconnect()
            self.vb.removeItem(self.linearROI)
            self.linearROI.hide()
#            self.LinearWidget.deleteLater()

    def selectLineROI(self):
        fig, ax = plt.subplots()
        array = self.linearROI.getArrayRegion(self.image, self.img)
        plt.plot(array)
        ax.set_xlabel('Roi')
        ax.set_ylabel('Intensity (N photons)')
        plt.show()


# %% Presets copiados del inspector
    def Presets(self):
        if self.presetsMode .currentText() == self.presetsModes[0]:
            self.scanRangeEdit.setText('5')
            self.pixelTimeEdit.setText('0.01')
            self.numberofPixelsEdit.setText('100')
            self.presetsMode.setStyleSheet("QComboBox{color: rgb(255,0,0);}\n")

        elif self.presetsMode .currentText() == self.presetsModes[1]:
            self.scanRangeEdit.setText('100')
            self.pixelTimeEdit.setText('0.2')
            self.numberofPixelsEdit.setText('128')
            self.presetsMode.setStyleSheet("QComboBox{color:rgb(153,153,10);}")

        elif self.presetsMode .currentText() == self.presetsModes[2]:
            self.scanRangeEdit.setText('50')
            self.pixelTimeEdit.setText('0.05')
            self.numberofPixelsEdit.setText('250')
            self.presetsMode.setStyleSheet("QComboBox{color:rgb(76,0,153);}\n")

        else:
            print("nunca tiene que entrar aca")

        self.paramChanged()
#        self.preseteado = True    creo que no lo voy a usar

# %% FUNCIONES PRINTING

    def grid_read(self):
        """ select the file where the grid comes from"""
        root = tk.Tk()
        root.withdraw()
#        name = "C://.../sarasa/10x15"
        name = filedialog.askopenfilename()
        f = open(name, "r")
        datos = np.loadtxt(name, unpack=True)
        f.close()
        self.grid_name = name
#        self.grid_create_folder()
        self.grid_x = datos[0, :]
        self.grid_y = datos[1, :]
#        z = datos[2, :]  # siempre cero en general.
        self.grid_plot()

    def grid_plot(self):
        """hace un plot de la grilla cargada para estar seguro que es lo que
        se quiere imprimir (nunca esta de mas)"""
        try:
            fig, ax = plt.subplots()
            plt.plot(self.grid_x, self.grid_y, 'o')
            ax.set_xlabel('x (µm)')
            ax.set_ylabel('y (µm)')
            ax.grid(True)
            plt.show()
        except IOError as e:
            print("I/O error({0}): {1}".format(e.errno, e.strerror))

            print("^ No hay nada cargado ^")

    def grid_create_folder(self):
        """ Crea una carpeta para este archivo particular.
        Si es una grilla, puede tener esa data en el nombre (ej: 10x15)"""
        base = os.path.basename(self.grid_name)
#        grid_name = filedialog.askopenfilename()

        q = base
        w = [""]*len(q)
        j = 0
        for i in range(len(q)):
            try:
                float(q[i]) == float
                print(q[i])
                w[j] = w[j] + str(q[i])
            except:
                print("separador", q[i])
                j = j+1
        print(w)
        numeros = [int(s) for s in w if s.isdigit()]

        timestr = time.strftime("%H-%M-%S")  # %Y%m%d-
        self.old_folder = self.main.file_path
        try:
            print("la grilla es de {}x{}".format(numeros[0], numeros[1]))
            new_folder = self.main.file_path + "/" + timestr +\
            "_Grilla {}x{}".format(numeros[0], numeros[1])

        except IOError as e:
            print("I/O error({0}): {1}".format(e.errno, e.strerror))
#            print("No lo tomo como grilla, AVISAR!")
            QtGui.QMessageBox.question(self,
                                       'Algo raro paso',
                                       'No lo tomo como grilla, AVISAR!\
                                       \n Pero igual creó una carpeta',
                                       QtGui.QMessageBox.Ok)

            new_folder = self.main.file_path + "/" + timestr + "_algo"
        os.makedirs(new_folder)
#        self.file_path = newpath  # no quiero perder el nombre anterior,
#        asi despues vuelvo
        self.NameDirValue.setText(new_folder)
        self.NameDirValue.setStyleSheet(" background-color: green ; ")
        self.main.file_path = new_folder
        self.i_global = 0

    def grid_start(self):
        """funcion que empieza el programa de imprimir una grilla
        (u otra cosa)"""
        self.i_global = 0  # Este no va aca. Queda en el de la carpeta
        self.a = np.zeros(11)
        self.grid_timer_traza = QtCore.QTimer()
        self.grid_timer_traza.timeout.connect(self.grid_detect_signal)
        self.grid_move()

    def grid_move(self):
        """ se mueve siguiendo las coordenadas que lee del archivo"""
        time.sleep(1)
        startX = float(self.xLabel.text())
        startY = float(self.yLabel.text())
        self.grid_openshutter()
#            self.aotask.write(np.array(
#                [self.grid_x[self.i_global] + startX / convFactors['x'],
#                 self.grid_y[self.i_global] + startY / convFactors['y']]),
#                auto_start=True)
        print("me muevo",
              self.grid_x[self.i_global] + startX,
              self.grid_y[self.i_global] + startY)

        self.grid_traza()

    def grid_openshutter(self):
        """ abre el shutter que se va a utilizar para imprimir"""
        time.sleep(1)
        if self.grid_laser.currentText() == shutters[0]:  # Verde
            self.openShutter(shutters[0])
            self.grid_shutterabierto = shutters[0]
        elif self.grid_laser.currentText() == shutters[1]:  # rojo
            self.openShutter(shutters[1])
            self.grid_shutterabierto = shutters[1]
        elif self.grid_laser.currentText() == shutters[2]:  # azul
            self.openShutter(shutters[2])
            self.grid_shutterabierto = shutters[2]

    def grid_traza(self):
        """ Abre la ventana nueva y mide la traza,
        preparado para detectar eventos de impresion"""
        self.main.grid_traza_control = False
        self.grid_timer_traza.start(10)  # no se que tiempo poner
        self.doit()
#        self.main.Signal1.connect(self.grid_detect)
#        while self.main.grid_traza_control == False:
#            pass
#        self.grid_detect()
#        self.main.grid_timer_traza.start(10)  # no se que tiempo poner

    def grid_detect_signal(self):
        """ Espera hasta detectar el evento de impresion.
        grid_timer_traza connect here"""
        if self.main.grid_traza_control:
            self.grid_timer_traza.stop()
            self.grid_detect()

    def grid_detect(self):
        """ Cuando detecta un evento de impresion, entra aca.
        Esta funcion define el paso siguiente.
        Puede ser: hacer autofoco, un scan de la PSF, o simplemente seguir """
        self.closeShutter(self.grid_shutterabierto)
#        time.sleep(1)
        self.i_global += 1
        print(" i global ", self.i_global)
        Nmax = 6  # self.Nmax  cantidad total de particulas
        autofoco = 2  # self.autofoco cada tanto
        multifoco = np.arange(0, Nmax, autofoco)  # ie:np.arange(0,6,2)=[0,2,4]
        if self.i_global < Nmax:
            if self.i_global in multifoco:
                print("Estoy haciendo foco")
                time.sleep(1)
#                #self.grid_autofoco()
            print(" i global ", self.i_global, "?")
            self.grid_move()
        else:
            self.main.file_path = self.old_folder
            self.NameDirValue.setText(self.old_folder)
            self.NameDirValue.setStyleSheet(" background-color: ; ")
#        self.moveto("back to origin")
#            print("TERMINÓ LA GRILLA")
            QtGui.QMessageBox.question(self,
                                           'Fin',
                                           'FIN!\
                                           \n fin',
                                           QtGui.QMessageBox.Ok)

    def move_z(self, dist):
        """moves the position along the Z axis a distance dist."""
#        time.sleep(0.1)
        dist = dist
#        print("me muevo en z", dist)
#        with nidaqmx.Task("Ztask") as Ztask:
#             self.Ztask = nidaqmx.Task('Ztask')
#             Following loop creates the voltage channels
#            n = 2
#            Ztask.ao_channels.add_ao_voltage_chan(
#                physical_channel='Dev1/ao{}'.format(n),
#                name_to_assign_to_channel='chan_%s' % activeChannels[n],
#                min_val=minVolt[activeChannels[n]],
#                max_val=maxVolt[activeChannels[n]])
#
#            N = abs(int(dist*2000))
#        # read initial position for all channels
#            toc = ptime.time()
#            rampz = np.linspace(0, dist, N) + float(self.zLabel.text())
#            for i in range(N):
#                Ztask.write([rampz[i] / convFactors['z']], auto_start=True)
#
#            print("se mueve en", np.round(ptime.time() - toc, 4), "segs")
#        # update position text
#            self.zLabel.setText("{}".format(np.around(float(rampz[-1]), 2)))
#        self.Ztask.stop()
#        self.Ztask.close()
#        self.paramChanged()

    def focus_go_to_maximun(self):
        """ barre en z mientras mira el PD, y va al maximo de intensidad"""
        self.focus_lock_focus()
        z_max = (np.max(self.z_profile))
#        print(self.z_profile, np.where(self.z_profile == z_max)[0][0], z_max)
#        print("\n z vector",self.z_vector)
        print("paso go to maximun")
        self.move_z(self.z_vector[np.where(self.z_profile == z_max)[0][0]])

    def focus_openshutter(self):
        """ abre el shutter con el que se hace foco"""
        time.sleep(1)
        if self.focus_laser.currentText() == shutters[0]:  # Verde
            self.openShutter(shutters[0])
            self.focus_shutterabierto = shutters[0]
        elif self.focus_laser.currentText() == shutters[1]:  # rojo
            self.openShutter(shutters[1])
            self.focus_shutterabierto = shutters[1]
        elif self.focus_laser.currentText() == shutters[2]:  # azul
            self.openShutter(shutters[2])
            self.focus_shutterabierto = shutters[2]
        time.sleep(1)

    def read_PD(self, color):
        """ Read de photodiode of the selecter 'color' """
        channel = {shutters[0]: 0, shutters[1]: 1, shutters[2]: 2}
#        time.sleep(0.1)
#        print("abre canal pmt")  # , channel)
#        with nidaqmx.Task("PDtask") as PDtask:
#            self.PDtask = nidaqmx.Task('PDtask')
#            PDtask.ai_channels.add_ai_voltage_chan(
#                physical_channel='Dev1/ai{}'.format(channel[color]),
#                name_to_assign_to_channel='chan_PD')
#            z_profile = PDtask.read()
        read = np.random.rand(10)[0]*50
        return read

    def focus_lock_focus(self):
        """ guarda el patron de intensidades, barriendo z en el foco actual"""
        self.Npasos = int(self.numberofPixelsEdit.text())  # algun numero de pasos a definir (50 dice en algun lado)
        z_start = float(self.zLabel.text()) - (self.scanRange/2)
        z_end = float(self.zLabel.text()) + (self.scanRange/2)  # initialPosition[2]
        self.z_vector = np.linspace(z_start, z_end, self.Npasos)
        self.z_profile = np.zeros((self.Npasos))
        self.focus_openshutter()
        for i in range(self.Npasos):
            self.move_z(self.z_vector[i])
            self.z_profile[i] = self.read_PD(self.focus_shutterabierto)
        # TODO: hacerlo con una rampa; averiguar cuanto tarda labview
        self.closeShutter(self.focus_shutterabierto)
        print("tengo el z_profile")
        self.locked_focus = True
        self.move_z((self.zLabel.text()))

    def focus_autocorr(self):
        """ correlaciona la medicion de intensidad moviendo z,
        respecto del que se lockeo con loc focus"""
        if self.locked_focus:
            Ncorrelations = 6  # tambien a definir....
            self.new_profile = np.zeros((Ncorrelations, self.Npasos))
            correlations = np.zeros((self.Npasos))
            maxcorr = np.zeros(Ncorrelations)
            z_vector_corr = np.zeros((Ncorrelations, self.Npasos))
#        self.z_vector = np.linspace(z_start, z_end, self.Npasos)
            for j in range(Ncorrelations):
                z_vector_corr[j, :] = self.z_vector-3+j
                for i in range(self.Npasos):
                    self.move_z(z_vector_corr[j, i])
                    self.new_profile[j, i] = self.read_PD(
                                                    self.focus_shutterabierto)
                correlations[:] = np.correlate(self.new_profile[j, :],
                                               self.z_profile, "same")
                maxcorr[j] = np.max(correlations)
#                plt.plot(z_vector_corr[j, :])
#                plt.plot(self.new_profile)
#                plt.plot(self.z_profile,'.-k')
#                plt.plot(correlations)
#                plt.plot(np.where(correlations==np.max(correlations)),
#                          np.max(correlations), marker='o')

            j_final = (np.where(maxcorr == np.max(maxcorr))[0][0])
            z_max = np.max(self.new_profile[j_final, :])
            donde_z_max = np.where(self.new_profile[j_final, :] == z_max)

            plt.plot(self.new_profile[j_final, :], 'o-')
            plt.show()
            print(j_final, z_vector_corr[j_final, donde_z_max])

        else:
            print("No esta Lockeado el foco")

    def grid_scan(self):
        """ Hace un confocal de la particula"""
        pass

# para saber si esta en potencia alta o baja
    def power_change(self):
        if self.power_check.isChecked():
            self.power_check.setText('Potencia \n BAJA')
            self.power_check.setStyleSheet("color: rgb(12, 183, 242); ")

        else:
            self.power_check.setText('Potencia \n ALTA')
            self.power_check.setStyleSheet("color: rgb(155, 064, 032); ")

# Con esta funcion me encargo de que los menus tengan colores
    def color_menu(self, QComboBox):
        """ le pongo color a los menus"""
        if QComboBox.currentText() == shutters[0]:  # verde
            QComboBox.setStyleSheet("QComboBox{color: rgb(0,128,0);}\n")
        elif QComboBox .currentText() == shutters[1]:  # rojo
            QComboBox.setStyleSheet("QComboBox{color: rgb(255,0,0);}\n")
        elif QComboBox .currentText() == shutters[2]: # azul
            QComboBox.setStyleSheet("QComboBox{color: rgb(0,0,255);}\n")


# %% Point scan (inaplicable aca)
# """
    def PointStart(self):
        self.doit()
#            self.PointScan()
        print("midiendo")
#        else:
#            self.PointScanStop()
# #            self.w.close()
#            print("fin")

    def PointScanStop(self):
        self.w.pointtimer.stop()
#        self.pointtimer.stop()
# #        self.pointtask.stop()
# #        self.pointtask.close()
# #        self.pointtask2.stop()
# #        self.pointtask2.close()
        print("fin traza")
#
#    def PointScan(self):
#
#        self.tiempo = 40 # ms  # refresca el numero cada este tiempo
# #        self.points = np.zeros(int((self.apdrate*(tiempo /10**3))))
# #        self.points2 = self.points
#
# #        self.pointtask = nidaqmx.Task('pointtask')
#
#        # Configure the counter channel to read the APD
# #        self.pointtask.ci_channels.add_ci_count_edges_chan(
# #                            counter='Dev1/ctr{}'.format(COchans[0]),
# #                            name_to_assign_to_channel=u'Line_counter',
# #                            initial_count=0)
#
# #        self.pointtask2 = nidaqmx.Task('pointtask2')
# #        # Configure the counter channel to read the APD
# #        self.pointtask2.ci_channels.add_ci_count_edges_chan(
# #                            counter='Dev1/ctr{}'.format(COchans[1]),
# #                            name_to_assign_to_channel=u'Line_counter',
# #                            initial_count=0)
#        self.timeaxis = []
#        try: self.traza_Widget.deleteLater()
#        except: pass
#        self.traza_Widget = pg.GraphicsLayoutWidget()
#        self.p6 = self.traza_Widget.addPlot(row=2,col=1,title="Traza")
#        self.p6.showGrid(x=True, y=True)
#        self.curve = self.p6.plot(open='y')
# #        self.otrosDock.addWidget(self.traza_Widget)
#        self.ptr1 = 0
#        self.data1 = []  # np.empty(100)
# #        self.data1 = np.zeros(300)
#
#
#        self.p7 = self.traza_Widget.addPlot(row=3,col=1,title="Traza")
#        self.p7.showGrid(x=True, y=True)
#        self.curve2 = self.p7.plot(open='y')
#        self.data2 = np.zeros(300)
#        self.timeaxis2 = np.zeros(300)
#        self.otrosDock.addWidget(self.traza_Widget)
#
#        self.pointtimer = QtCore.QTimer()
#        self.pointtimer.timeout.connect(self.updatePoint)
#        self.pointtimer.start(self.tiempo)
#
#    def updatePoint(self):
#        points = np.zeros(int((apdrate*(self.tiempo /10**3))))
#        points2 = points
#        points[:] = np.random.rand(len(points))  # self.pointtask.read(N)
#        points2[:] = np.random.rand(len(points2))  # self.pointtask.read(N)
#
#        m = np.mean(points)
#        m2 = np.mean(points2)
# #        self.PointLabel.setText("<strong>{0:.2e}|{0:.2e}".format(
#                                   float(m),float(m2)))
#
#        self.timeaxis.append((self.tiempo * 10**-3)*self.ptr1)
#        self.data1.append(m + np.log(self.ptr1)+points[0])
#        self.ptr1 += 1
#        self.curve.setData(self.timeaxis, self.data1)
# #        self.curve.setPos(-self.ptr1, 0)
#
# #    def updatePointAA(self):
# #        points = np.zeros(int((apdrate*(self.tiempo /10**3))))
# #        points2 = points
# # #        N = len(points)
# #        points[:] = np.random.rand(len(points))  # self.pointtask.read(N)
# #        points2[:] = np.random.rand(len(points2))  # self.pointtask.read(N)
#
# #        m = np.mean(points)
# #        m2 = np.mean(points2)
# #        #print("valor traza", m)
# #        self.PointLabel.setText("<strong>{0:.2e}|{0:.2e}".format(
#                                   float(m),float(m2)))
#
# #        self.ptr1 += 1
#        self.timeaxis2 = np.roll(self.timeaxis2,-1)
#        self.timeaxis2[-1] = (self.tiempo * 10**-3)*self.ptr1
# #        self.timeaxis2 = np.delete(self.timeaxis2,0)
# #        self.timeaxis2 = np.append(self.timeaxis2,(
#                                     self.tiempo * 10**-3)*self.ptr1)
# #        self.data2[:-1] = self.data2[1:]  # shift  one sample left
#        self.data2= np.roll(self.data2,-1)             # (see also: np.roll)
#        self.data2[-1] = m + np.log(self.ptr1) + points[0]
#        self.curve2.setData(self.timeaxis2, self.data2)
#        self.curve2.setPos(self.timeaxis2[0], 0)

    def doit(self):
        print("Opening a new popup window...")
        self.w = MyPopup_traza(self.main, self)
        self.w.setGeometry(QtCore.QRect(750, 50, 450, 600))
        self.w.show()


# """
class MyPopup_traza(QtGui.QWidget):

    def closeEvent(self, event):
        self.stop()
#        self.pointtimer.stop()
#        self.running = False
        print("Paró y cerró la traza")

    def __init__(self, main, ScanWidget, *args, **kwargs):
        QtGui.QWidget.__init__(self)
        super().__init__(*args, **kwargs)
        self.main = main
        self.ScanWidget = ScanWidget
        self.traza_Widget2 = pg.GraphicsLayoutWidget()
        self.running = False
        grid = QtGui.QGridLayout()
        self.setLayout(grid)

        self.p6 = self.traza_Widget2.addPlot(row=2, col=1, title="Traza")
        self.p6.showGrid(x=True, y=True)
        self.curve = self.p6.plot(open='y')
        self.line = self.p6.plot(open='y')
        self.line1 = self.p6.plot(open='y')
        self.line12 = self.p6.plot(open='y')

        self.p7 = self.traza_Widget2.addPlot(row=3, col=1, title="Traza")
        self.p7.showGrid(x=True, y=True)
        self.curve2 = self.p7.plot(open='y')
        self.line2 = self.p7.plot(open='y')

    #  buttons: play button
        self.play_pause_Button = QtGui.QPushButton('► Play / Pause ‼ (F1)')
        self.play_pause_Button.setCheckable(True)
        self.play_pause_Button.clicked.connect(self.play_pause)
        self.play_pause_Button.setToolTip('Pausa y continua la traza (F1)')
#        self.pause_Button.setStyleSheet(
#                "QPushButton { background-color: rgb(200, 200, 10); }"
#                "QPushButton:pressed { background-color: blue; }")

    # Stop button
        self.stop_Button = QtGui.QPushButton('◘ Stop (F2)')
        self.stop_Button.setCheckable(False)
        self.stop_Button.clicked.connect(self.stop)
        self.stop_Button.setToolTip('Para la traza (F2)')

    # save button
        self.save_Button = QtGui.QPushButton('plot and/or save')
        self.save_Button.setCheckable(False)
        self.save_Button.clicked.connect(self.save_traza)
        self.save_Button.setToolTip('Para Guardar la traza(tambien la plotea)')
        self.save_Button.setStyleSheet(
                "QPushButton { background-color: rgb(200, 200, 10); }"
                "QPushButton:pressed { background-color: blue; }")

    # umbral
        self.umbralLabel = self.ScanWidget.umbralLabel  # QtGui.QLabel('Umbral'
        self.umbralEdit = self.ScanWidget.umbralEdit  # QtGui.QLineEdit('10')
#        self.umbralEdit.settext()
#        print("umbral",self.main.umbralEdit.text())
#        self.umbralEdit.setFixedWidth(40)
        self.umbralLabel.setToolTip('promedios de valores nuevo/anteriores ')

        self.PointLabel = QtGui.QLabel('<strong>0.00|0.00')

        grid.addWidget(self.traza_Widget2,      0, 0, 1, 7)
        grid.addWidget(self.play_pause_Button,  1, 0)
        grid.addWidget(self.stop_Button,        1, 1)
#        grid.addWidget(self.umbralLabel,        1, 3)
#        grid.addWidget(self.umbralEdit,         1, 4)
        grid.addWidget(self.PointLabel,         1, 5)
        grid.addWidget(self.save_Button,        1, 6)
        self.setWindowTitle("Traza. (ESC lo cierra)")
        self.play_pause_Button.setChecked(True)
        self.PointScan()

        self.play_pause_Action = QtGui.QAction(self)
#        self.play_pause_Action.setShortcut('Ctrl+L')
        QtGui.QShortcut(
            QtGui.QKeySequence('F1'), self, self.play_pause_active)
#        self.play_pause_Action.triggered.connect(self.play_pause_active)
#        self.play_pause_Action.setEnabled(True)

        self.stop_Action = QtGui.QAction(self)
        QtGui.QShortcut(
            QtGui.QKeySequence('F2'), self, self.stop)

        self.close_Action = QtGui.QAction(self)
        QtGui.QShortcut(
            QtGui.QKeySequence('ESC'), self, self.close_win)

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

    def close_win(self):
        self.close()

    def play_pause_active(self):
        '''Triggered by the play_pause_Action shortcut.'''
        if self.play_pause_Button.isChecked():
            self.play_pause_Button.setChecked(False)
        else:
            self.play_pause_Button.setChecked(True)
        self.play_pause()

    def play_pause(self):
        if self.play_pause_Button.isChecked():
            print("play")
            self.timer_inicio = ptime.time()

            # self.pause_Button.setStyleSheet(
            #        "QPushButton { background-color: ; }")
            if self.running:
                self.pointtimer.start(self.tiempo)
            else:
                self.PointScan()
        else:
            print("pause")
            self.pointtimer.stop()
            # self.pause_Button.setStyleSheet(
            #        "QPushButton { background-color: red; }")

    def stop(self):
        print("stop")
        try:
            self.pointtimer.stop()
        except IOError as e:
            print("I/O error({0}): {1}".format(e.errno, e.strerror))
        self.running = False
        self.play_pause_Button.setChecked(False)

#    def paintEvent(self, e):
#        dc = QtGui.QPainter(self)
#        dc.drawLine(0, 0, 100, 100)
#        dc.drawLine(100, 0, 0, 100)

    def save_traza(self):
#        fig, ax = plt.subplots()
#        plt.plot(self.timeaxis[:self.ptr1], self.data1[:self.ptr1])
#        ax.set_xlabel('Tiempo (s) (puede fallar)')
#        ax.set_ylabel('Intensity (V)')
#        plt.show()

        try:
            # filepath = self.file_path
            filepath = self.main.file_path
            timestr = time.strftime("%H-%M-%S")  # %d%m%Y-
            name = str(filepath + "/" + timestr +"_"+ "Traza" + ".txt")
            f = open(name, "w")
            np.savetxt(name,
                       np.transpose([self.timeaxis[:self.ptr1],
                                     self.data1[:self.ptr1]]),
                       header="{} y umbral={}".format(
                        timestr, float(self.umbralEdit.text())))
            f.close()
            print("\n Guardo la Traza")
        except IOError as e:
            print("I/O error({0}): {1}".format(e.errno, e.strerror))

    def PointScan(self):
        self.running = True
        self.tiempo = 10  # ms  # refresca el numero cada este tiempo

        self.timeaxis = np.empty(100)  # [0]
#        try: self.traza_Widget2.deleteLater()
#        except: pass
#        self.traza_Widget2 = pg.GraphicsLayoutWidget()

#        self.otrosDock.addWidget(self.traza_Widget)
        self.ptr1 = 0
        self.data1 = np.empty(100)  # [0]  # np.empty(100)
#        self.data1 = np.zeros(300)

        self.data2 = np.zeros(300)
        self.timeaxis2 = np.zeros(300)
#        self.otrosDock.addWidget(self.traza_Widget)

        self.pointtimer = QtCore.QTimer()
        self.pointtimer.timeout.connect(self.updatePoint)
        self.timer_inicio = ptime.time()
        self.pointtimer.start(self.tiempo)

    def updatePoint(self):
        points = np.zeros(int((apdrate*(self.tiempo / 10**3))))
        points2 = points
        points[:] = np.random.rand(len(points))  # self.pointtask.read(N)
        points2[:] = np.random.rand(len(points2))  # self.pointtask.read(N)

        sig = np.mean(points) + np.log(self.ptr1+1)**2 + points[0]
        if self.ptr1 > 150:
            sig = self.ptr1**5
#        self.timeaxis.append((self.tiempo * 10**-3)*self.ptr1)
#        self.data1.append(sig)
        self.timeaxis[self.ptr1] = (self.tiempo * 10**-3)*self.ptr1
        self.data1[self.ptr1] = sig
        self.ptr1 += 1
        if self.ptr1 >= self.data1.shape[0]:
            tmpdata = self.data1
            self.data1 = np.empty(self.data1.shape[0] * 2)
            self.data1[:tmpdata.shape[0]] = tmpdata
            tmptime = self.timeaxis
            self.timeaxis = np.empty(self.timeaxis.shape[0] * 2)
            self.timeaxis[:tmptime.shape[0]] = tmptime

        self.curve.setData(self.timeaxis[:self.ptr1], self.data1[:self.ptr1],
                           pen=pg.mkPen('r', width=1),
                           shadowPen=pg.mkPen('b', width=3))
#        self.curve.setPos(-self.ptr1, 0)

        m = np.mean(self.data1[:self.ptr1])
        m1 = np.max(self.data1[:self.ptr1])
        self.PointLabel.setText("<strong>{:.3}|{:.3}".format(
                                           float(m), float(m1)))
#        self.p7.addLine(x=None, y=m, pen=pg.mkPen('y', width=1))
        self.line.setData(self.timeaxis[:self.ptr1],
                          np.ones(len(self.timeaxis[:self.ptr1])) * m,
                          pen=pg.mkPen('c', width=2))

        self.timeaxis2 = np.roll(self.timeaxis2, -1)
        self.timeaxis2[-1] = (self.tiempo * 10**-3) * self.ptr1
        self.data2 = np.roll(self.data2, -1)             # (see also: np.roll)
        self.data2[-1] = sig
#        self.curve2.setData(self.timeaxis2, self.data2)
        M = 300  # tengo que cambiar mas cosas para que esto ande
        self.curve2.setData(np.linspace(0, 3, M), self.data2)
        self.curve2.setPos(self.timeaxis2[0], 0)
        m2 = np.mean(self.data2)
        self.line2.setData(self.timeaxis2,
                           np.ones(M) * m2, pen=pg.mkPen('y', width=2))

        if self.ptr1 < M:
            medio = np.mean(self.data1[:self.ptr1])
            if self.ptr1 < 11:
                medio2 = np.mean(self.data1[:self.ptr1])
            else:
                medio2 = np.mean(self.data1[:self.ptr1-10])
        else:
            medio = np.mean(self.data1[self.ptr1-M:self.ptr1])
            medio2 = np.mean(self.data1[self.ptr1-M-10:self.ptr1-10])

        self.line1.setData(self.timeaxis2,
                           np.ones(M) * medio, pen=pg.mkPen('g', width=2))
        self.line12.setData(self.timeaxis2[:-10],
                            np.ones(M-10) * medio2, pen=pg.mkPen('y', width=2))

#        self.PointLabel.setText("<strong>{:.2}|{:.2}".format(
#                                float(m), float(medio)))
#        print(medio, medio2)
        self.PointLabel.setText("<strong>{:.3}|{:.3}".format(
                                float(medio), float(medio2)))
        if ptime.time() - self.timer_inicio > float(self.ScanWidget.tmaxEdit.text()):
            print("se paso el tiempo!!")
        if medio > medio2*float(self.umbralEdit.text()):
            self.PointLabel.setStyleSheet(" background-color: orange")
#            if not self.main.grid_traza_control:
#                print("medio=", np.round(medio))
#                self.save_traza()
#                self.stop()
#                self.close_win()
#                self.main.grid_traza_control = True
##                self.main.Signal1.emit()
        if not self.main.grid_traza_control:
            if medio > medio2*float(self.umbralEdit.text()) or ptime.time() - self.timer_inicio > float(self.ScanWidget.tmaxEdit.text()):
                print("medio=", np.round(medio))
                self.save_traza()
                self.stop()
                self.close_win()
                self.main.grid_traza_control = True



        else:
            self.PointLabel.setStyleSheet(" background-color: ")

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

# %%  FIN

if __name__ == '__main__':

    app = QtGui.QApplication([])
#    win = ScanWidget(device)
    win = MainWindow()
    win.show()

    app.exec_()
#    sys.exit(app.exec_())
