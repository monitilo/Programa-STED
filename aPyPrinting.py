﻿# %%
""" Programa para Printign!!"""

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
from scipy import optimize

import re
import tools

import viewbox_tools

import nidaqmx

device = nidaqmx.system.System.local().devices['Dev1']
# z =  1.683
convFactors = {'x': 25, 'y': 25, 'z': 25}  # TODO: CAMBIAR!!!!!
# la calibracion es 1 µm = 40 mV en x,y (galvos);
# en z, 0.17 µm = 0.1 V  ==> 1 µm = 0.58 V
# 1.68 um = 1 V ==> 1 um = 0.59V  # asi que promedie, y lo puse a ojo.
minVolt = {'x': -10, 'y': -10, 'z': 0}
maxVolt = {'x': 10, 'y': 10, 'z': 10}
resolucionDAQ = 0.0003 * 2 * convFactors['x']
# V => µm; uso el doble para no errarle
activeChannels = ["x", "y", "z"]
AOchans = [0, 1, 2]  # , 2]  # x,y,z  # TODO: agregar z
detectModes = ['APD red', 'APD yellow', 'both APDs', 'PMT']
# detectModes[1:n] son los apd's; detectMode[-1] es el PMT y [-2] otros.
COchans = [0, 1]  # apd rojo y verde  # TODO: ya no uso contadores
PMTchan = 1  # TODO: pero uso varios "pmt" (son fotodiodos(pd))
scanModes = ['ramp scan', 'step scan', 'full frec ramp', "slalom"]
PDchans = [0,1,2]  # elegir aca las salidas del PD de cada color
#shutters = ["red", "STED", "yellow"]  # digitals out channesl [0, 1, 2]
shutters = ['532 (verde)', '640 (rojo)', '405 (azul)']  # salida 1,2,3

apdrate = 10**5

PD_channels = {shutters[0]: 0, shutters[1]: 1, shutters[2]: 2}
# %% Main Window
class MainWindow(QtGui.QMainWindow):
#    def closeEvent(self, event):
#        reply = QtGui.QMessageBox.question(self, 'Quit', 'Are u Sure to Quit?',
#                                           QtGui.QMessageBox.No |
#                                           QtGui.QMessageBox.Yes)
#        if reply == QtGui.QMessageBox.Yes:
#            print("YES")
#            event.accept()
#            self.close()
#            self.liveviewStop()
#        else:
#            event.ignore()
#            print("NOOOO")

    def newCall(self):
        print('New')

    def openCall(self):
        namebien = (self.form_widget.NameDirValue.text()).replace("/", "\\")
        os.startfile(namebien)
#        os.startfile(self.file_path)
        print('Open: ', self.file_path)

    def exitCall(self):
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
            print("direccion elegida: \n", self.file_path, "\n")
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
                print("Carpeta creada!")
            else:
                print("Ya existe esa carpeta")
            self.file_path = newpath
            self.form_widget.NameDirValue.setText(self.file_path)
            self.form_widget.NameDirValue.setStyleSheet(" background-color: ;")

    def save_docks(self):
        self.form_widget.state = self.form_widget.dockArea.saveState()

    def load_docks(self):
        self.form_widget.dockArea.restoreState(self.form_widget.state)

    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.a = 0
        self.file_path = os.path.abspath("")
#        self.setMinimumSize(QtCore.QSize(500, 500))
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
                                          '&Restore Docks', self)
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

        fileMenu2 = menuBar.addMenu('&Docks confih')
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


        self.umbralEdit = self.form_widget.umbralEdit
        self.grid_traza_control = True


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

        self.lock_focus_action = QtGui.QAction(self)
        QtGui.QShortcut(
            QtGui.QKeySequence('ctrl+f'), self, self.focus_lock_focus)

    # Cosas para la rutina de imprimir. Grid

    # umbral
        self.umbralLabel = QtGui.QLabel('Umbral')
        self.umbralEdit = QtGui.QLineEdit('10')
        self.umbralEdit.setFixedWidth(40)
        self.umbralEdit.setToolTip('promedios de valores nuevo/anteriores ')
        self.umbralLabel.setToolTip('promedios de valores nuevo/anteriores ')

    # Tiempo de espera maximo
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
        self.grid_laser.activated.connect(
                                    lambda: self.color_menu(self.grid_laser))
        self.color_menu(self.grid_laser)
        grid_laser_label = QtGui.QLabel('<strong> Print Laser')

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
        self.go_ref_button.clicked.connect(self.go_reference)
        self.go_ref_button.setStyleSheet(
                "QPushButton:pressed { background-color: blue; }")
        self.go_ref_button.setToolTip('Va a la referencia seteada')
        self.go_ref_button.setFixedWidth(80)

    # set reference button.
        self.set_ref_button = QtGui.QPushButton('set reference')
        self.set_ref_button.setCheckable(False)
        self.set_ref_button.clicked.connect(self.set_reference)
        self.set_ref_button.setStyleSheet(
                "QPushButton:pressed { background-color: blue; }")
        self.set_ref_button.setToolTip('setea la referencia')
        self.set_ref_button.setFixedWidth(150)

        self.scan_check = QtGui.QCheckBox('scan?')
        self.scan_check.clicked.connect(self.scan_change)
        self.scan_check.setStyleSheet("color: green; ")
        self.scan_change()

    # particulas totales
        self.particulasLabel = QtGui.QLabel('Cantidad de puntos')
        self.particulasEdit = QtGui.QLabel('0')
        self.particulasEdit.setFixedWidth(40)
        self.particulasEdit.setToolTip('Cantidad de particulas totales a imprimir')
        self.particulasLabel.setToolTip('Cantidad de particulas totales a imprimir')
        self.particulasEdit.setStyleSheet(
                                        " background-color: rgb(200,200,200)")
    # Indice actual
        self.indice_impresionLabel = QtGui.QLabel('Indice de impresion')
        self.indice_impresionEdit = QtGui.QLabel('0')
        self.indice_impresionEdit.setFixedWidth(40)
        self.indice_impresionEdit.setStyleSheet(
                                        " background-color: rgb(200,200,200)")

    # La grid con las cosas de printing. Mas abajo entra en el dock
        self.grid_print = QtGui.QWidget()
        grid_print_layout = QtGui.QGridLayout()
        self.grid_print.setLayout(grid_print_layout)
        grid_print_layout.addWidget(self.cargar_archivo_button,   0, 1, 2, 1)
        grid_print_layout.addWidget(self.imprimir_button,         0, 2, 2, 1)
        grid_print_layout.addWidget(self.next_button,             2, 2, 2, 1)
        grid_print_layout.addWidget(self.go_ref_button,           2, 1)
        grid_print_layout.addWidget(self.set_ref_button,          3, 1)
        grid_print_layout.addWidget(grid_laser_label,             0, 3, 1, 2)
        grid_print_layout.addWidget(self.grid_laser,              1, 3, 1, 2)
        grid_print_layout.addWidget(self.umbralLabel,             3, 3)
        grid_print_layout.addWidget(self.umbralEdit,              4, 3)
        grid_print_layout.addWidget(self.tmaxLabel,               3, 4)
        grid_print_layout.addWidget(self.tmaxEdit,                4, 4)
        grid_print_layout.addWidget(self.scan_check,              4, 2)
        grid_print_layout.addWidget(self.particulasLabel,         0, 5)
        grid_print_layout.addWidget(self.particulasEdit,          1, 5)
        grid_print_layout.addWidget(self.indice_impresionLabel,             2, 5)
        grid_print_layout.addWidget(self.indice_impresionEdit,              3, 5)


    # Cosas para la parte del foco

    # Defino el tipo de laser que quiero para hacer foco
        self.focus_laser = QtGui.QComboBox()
        self.focus_laser.addItems(shutters)
        self.focus_laser.setCurrentIndex(2)
        self.focus_laser.setToolTip('Elijo el shuter para HACER FOCO')
        self.focus_laser.setFixedWidth(80)
        self.focus_laser.activated.connect(
                                    lambda: self.color_menu(self.focus_laser))
        self.color_menu(self.focus_laser)
        focus_laser_label = QtGui.QLabel('<strong> Focus Laser')

    # Boton para Lockear el foco
        self.focus_lock_button = QtGui.QPushButton('Lock Focus')
        self.focus_lock_button.setCheckable(False)
        self.focus_lock_button.clicked.connect(self.focus_lock_focus)
        self.focus_lock_button.setToolTip('guarda el patron en el z actual')
        self.focus_lock_button.setStyleSheet(
                "QPushButton { background-color: rgb(254,100,100) ; }"
                "QPushButton:pressed { background-color: blue; }")


    # Boton de Autocorrelacion, con el foco ya lockeado
        self.focus_autocorr_button = QtGui.QPushButton('Autocorrelacion')
        self.focus_autocorr_button.setCheckable(False)
        self.focus_autocorr_button.clicked.connect(self.focus_autocorr)
        self.focus_autocorr_button.setToolTip('guarda el patron nel z actual')

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
        grid_focus_layout.addWidget(focus_laser_label,            2, 2)
        grid_focus_layout.addWidget(self.focus_laser,             3, 2)

    # particles to autofocus
        self.autofocLabel = QtGui.QLabel('Particles after autofocus')
        self.autofocEdit = QtGui.QLineEdit('10')
        self.autofocEdit.setFixedWidth(40)
        self.autofocEdit.setToolTip('Cantida de impresiones hasta autofoquear')

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
        self.preescan_laser.activated.connect(
                                lambda: self.color_menu(self.preescan_laser))
        self.color_menu(self.preescan_laser)

    # Defino el tipo de laser que quiero para imprimir
        self.dimerscan_laser = QtGui.QComboBox()
        self.dimerscan_laser.addItems(shutters)
        self.dimerscan_laser.setCurrentIndex(2)
        self.dimerscan_laser.setToolTip('Elijo el shuter para escanear el dimero ')
        self.dimerscan_laser.setFixedWidth(80)
        self.dimerscan_laser.activated.connect(
                                lambda: self.color_menu(self.dimerscan_laser))
        self.color_menu(self.dimerscan_laser)

    # particulas totales
        self.dimero_totalLabel = QtGui.QLabel('Dimeros totales')
        self.dimero_totalEdit = QtGui.QLabel('0')
        self.dimero_totalEdit.setFixedWidth(40)
        self.dimero_totalEdit.setToolTip('Cantidad de particulas totales a imprimir')
    # Indice actual
        self.indice_dimeroLabel = QtGui.QLabel('Indice dimero')
        self.indice_dimeroEdit = QtGui.QLabel('0')
        self.indice_dimeroEdit.setFixedWidth(40)
        self.indice_dimeroEdit.setStyleSheet(
                                        " background-color: rgb(200,200,200)")

    # Posicion a imprimir el dimero
        self.dimero_posxLabel = QtGui.QLabel('Dx [µm]')
        self.dimero_posxEdit = QtGui.QLineEdit('10')
        self.dimero_posxEdit.setFixedWidth(40)
        self.dimero_posxEdit.setToolTip('distancia en x donde imprimir.')
        self.dimero_posyLabel = QtGui.QLabel('Dy [µm]')
        self.dimero_posyEdit = QtGui.QLineEdit('0')
        self.dimero_posyEdit.setFixedWidth(40)
        self.dimero_posyEdit.setToolTip('distancia en y donde imprimir')

    # En otra grid poner las cosas de crecimiento/Dimeros
        self.grid_grow = QtGui.QWidget()

        grid_grow = QtGui.QGridLayout()
        self.grid_grow.setLayout(grid_grow)
        grid_grow.addWidget(self.dimeros_button,       1, 0)
        grid_grow.addWidget(self.dimeros_next_button,  1, 1)
        grid_grow.addWidget(self.t_waitLabel,          4, 1)
        grid_grow.addWidget(self.t_waitEdit,           5, 1)

        grid_grow.addWidget(self.dimero_posxLabel,     2, 1)
        grid_grow.addWidget(self.dimero_posxEdit,      3, 1)
        grid_grow.addWidget(self.dimero_posyLabel,     2, 2)
        grid_grow.addWidget(self.dimero_posyEdit,      3, 2)
        
        grid_grow.addWidget(QtGui.QLabel('Pre scan Laser'),   4, 0)
        grid_grow.addWidget(QtGui.QLabel('Dimer scan Laser'),  4, 4)
        grid_grow.addWidget(self.preescan_laser,   5, 0)
        grid_grow.addWidget(self.dimerscan_laser,  5, 4)
        grid_grow.addWidget(self.indice_dimeroLabel,             1, 4)
        grid_grow.addWidget(self.indice_dimeroEdit,              2, 4)

        grid_grow.addWidget(QtGui.QLabel(''),          2, 0)
        grid_grow.addWidget(QtGui.QLabel(''),          6, 0)

    # Go to maximun
        self.read_pos_button = QtGui.QPushButton("Read")
        self.read_pos_button.setCheckable(False)
        self.read_pos_button.clicked.connect(self.read_pos)
        self.read_pos_button.setToolTip('Lee la posicion actual')
        self.read_pos_Label = QtGui.QLabel('Posicion medida')

    # Valores de refecencai
        self.xrefLabel = QtGui.QLabel('6')
        self.yrefLabel = QtGui.QLabel('6')
        self.zrefLabel = QtGui.QLabel('6')

        self.grid_reference = QtGui.QWidget()
        grid_reference = QtGui.QGridLayout()
        self.grid_reference.setLayout(grid_reference)
        grid_reference.addWidget(QtGui.QLabel(''),          0, 0)
        grid_reference.addWidget(QtGui.QLabel(''),          4, 0)
        grid_reference.addWidget(QtGui.QLabel(''),          5, 0)
        grid_reference.addWidget(self.xrefLabel,            1, 1)
        grid_reference.addWidget(self.yrefLabel,            2, 1)
        grid_reference.addWidget(self.zrefLabel,            3, 1)
        grid_reference.addWidget(QtGui.QLabel('x ref ='),   1, 0)
        grid_reference.addWidget(QtGui.QLabel('y ref ='),   2, 0)
        grid_reference.addWidget(QtGui.QLabel('z ref ='),   3, 0)

        
# --- FIN COSAS PRINTING

        imageWidget = pg.GraphicsLayoutWidget()
        self.vb = imageWidget.addViewBox(row=1, col=1)

        self.point_graph_Gauss = pg.ScatterPlotItem(size=10,
                                                    symbol='o', color='m')
        self.point_graph_CM = pg.ScatterPlotItem(size=10,
                                                 symbol='+', color='m')

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
        tamaño = 110
        self.edit_save.setFixedWidth(tamaño)
        self.saveimageButton.setFixedWidth(tamaño)

        self.file_path = os.path.abspath("")
        self.NameDirValue = QtGui.QLabel('')
        self.NameDirValue.setText(self.file_path)
        self.NameDirValue.setStyleSheet(" background-color: red; ")

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
        self.shuttersignal = np.zeros(len(shutters), dtype='bool')
#        self.shuttersignal = [False, False, False]
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
#        self.shutter0button = QtGui.QCheckBox('shutter Red')
#        self.shutter0button.clicked.connect(self.shutter0)
#        self.shutter1button = QtGui.QCheckBox('shutter STED')
#        self.shutter1button.clicked.connect(self.shutter1)
#        self.shutter2button = QtGui.QCheckBox('shutter Yellow')
#        self.shutter2button.clicked.connect(self.shutter2)
#
#        self.shutter0button.setToolTip('Open/close Red Shutter')
#        self.shutter1button.setToolTip('Open/close STED Shutter')
#        self.shutter2button.setToolTip('Open/close Yellow Shutter')

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
        self.PointButton.setToolTip('continuously measures the APDs (Ctrl+T)')

        self.PiontAction = QtGui.QAction(self)
        QtGui.QShortcut(
            QtGui.QKeySequence('Ctrl+T'), self, self.PointStart)

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

        self.actualizar = QtGui.QLineEdit('0.5')

        self.scanMode.activated.connect(self.SlalomMode)

        self.presetsMode.activated.connect(self.PreparePresets)

    # Defino el tipo de laser que quiero para imprimir
        self.scan_laser = QtGui.QComboBox()
        self.scan_laser.addItems(shutters)
        self.scan_laser.setCurrentIndex(0)
        self.scan_laser.setToolTip('Elijo el shuter para scanear')
        self.scan_laser.setFixedWidth(80)
        self.scan_laser.activated.connect(
                                    lambda: self.color_menu(self.scan_laser))
        self.color_menu(self.scan_laser)
        scan_laser = QtGui.QLabel('<strong> Scan Laser')

    # Defino el tipo de laser que quiero para imprimir
        self.traza_laser = QtGui.QComboBox()
        self.traza_laser.addItems(shutters)
        self.traza_laser.setCurrentIndex(0)
        self.traza_laser.setToolTip('Elijo el shuter para las trazas')
        self.traza_laser.setFixedWidth(80)
        self.traza_laser.activated.connect(
                                    lambda: self.color_menu(self.traza_laser))
        self.color_menu(self.traza_laser)
        traza_laser = QtGui.QLabel('<strong> Trazas Laser')

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
#        subgrid.addWidget(self.shutter0button,      0, 1)
#        subgrid.addWidget(self.shutter2button,      1, 1)
#        subgrid.addWidget(self.shutter1button,      2, 1)
#        subgrid.addWidget(QtGui.QLabel('      '),   0, 1)
#        subgrid.addWidget(QtGui.QLabel('      '),   1, 1)
        subgrid.addWidget(scan_laser,               0, 1)
        subgrid.addWidget(self.scan_laser,          1, 1)
        subgrid.addWidget(QtGui.QLabel('      '),   2, 1)
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
#        subgrid.addWidget(self.maxcountsLabel,     15, 1)
#        subgrid.addWidget(self.maxcountsEdit,      16, 1, 2, 1)

    # Columna 2
#        subgrid2.addWidget(self.NameDirButton,       0, 2)
#        subgrid2.addWidget(self.OpenButton,          1, 2)
#        subgrid2.addWidget(self.create_day_Button,   2, 2)
#        subgrid2.addWidget(self.triggerLabel,        4, 2)
#        subgrid2.addWidget(self.triggerEdit,         5, 2)
#        subgrid2.addWidget(self.added_points_Label,   6, 2)
#        subgrid2.addWidget(self.added_points_Edit,    7, 2)
#        subgrid2.addWidget(self.vueltaLabel,         8, 2)
#        subgrid2.addWidget(self.vueltaEdit,          9, 2)
        subgrid2.addWidget(traza_laser,              0, 2)
        subgrid2.addWidget(self.traza_laser,         1, 2)
#        subgrid2.addWidget(QtGui.QLabel(""),         1, 2)
#        subgrid2.addWidget(QtGui.QLabel(""),         2, 2)
        subgrid2.addWidget(self.PointButton,         2, 2)
        subgrid2.addWidget(self.PointLabel,          3, 2)
        subgrid2.addWidget(self.detectMode,          4, 2)
#        subgrid2.addWidget(QtGui.QLabel(""),         4, 2)
        subgrid2.addWidget(QtGui.QLabel(""),         5, 2)
        subgrid2.addWidget(QtGui.QLabel("x/y scan"),   6, 2)
        subgrid2.addWidget(QtGui.QLabel("x/z scan"),   7, 2)
        subgrid2.addWidget(QtGui.QLabel("z/y scan"),   8, 2)
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
        subgrid3.addWidget(QtGui.QLabel(""),          7, 3)
        subgrid3.addWidget(QtGui.QLabel(""),          8, 3)
#        subgrid3.addWidget(QtGui.QLabel(""),          9, 3)

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
        self.xLabel = QtGui.QLabel('0.0')
#            "<strong>x = {0:.2f} µm</strong>".format(self.x))
        self.xLabel.setTextFormat(QtCore.Qt.RichText)
        self.xname = QtGui.QLabel("<strong>x =")
        self.xname.setTextFormat(QtCore.Qt.RichText)
        self.xUpButton = QtGui.QPushButton("(+x) ►")  # →
        self.xUpButton.pressed.connect(
                       lambda: self.move("x", float(self.StepEdit.text())))
        self.xDownButton = QtGui.QPushButton("◄ (-x)")  # ←
        self.xDownButton.pressed.connect(
                       lambda: self.move("x", -float(self.StepEdit.text())))
        self.xStepEdit = QtGui.QLineEdit("1.0")  # estaban en 0.05<
#        self.xStepUnit = QtGui.QLabel(" µm")
        self.xUp2Button = QtGui.QPushButton("► x ►")  # →
        self.xUp2Button.pressed.connect(
                       lambda: self.move("x", 10*float(self.StepEdit.text())))
        self.xDown2Button = QtGui.QPushButton("◄ x ◄")  # ←
        self.xDown2Button.pressed.connect(
                       lambda: self.move("x", -10*float(self.StepEdit.text())))

        self.yLabel = QtGui.QLabel('0.0')
#            "<strong>y = {0:.2f} µm</strong>".format(self.y))
        self.yLabel.setTextFormat(QtCore.Qt.RichText)
        self.yname = QtGui.QLabel("<strong>y =")
        self.yname.setTextFormat(QtCore.Qt.RichText)
        self.yUpButton = QtGui.QPushButton("(+y) ▲")  # ↑
        self.yUpButton.pressed.connect(
                       lambda: self.move("y", float(self.StepEdit.text())))
        self.yDownButton = QtGui.QPushButton("(-y) ▼")  # ↓
        self.yDownButton.pressed.connect(
                       lambda: self.move("y", -float(self.StepEdit.text())))
        self.StepEdit = QtGui.QLineEdit("1.0")
#        self.yStepUnit = QtGui.QLabel(" µm")
        self.yUp2Button = QtGui.QPushButton("▲ y ▲")  # ↑
        self.yUp2Button.pressed.connect(
                       lambda: self.move("y", 10*float(self.StepEdit.text())))
        self.yDown2Button = QtGui.QPushButton("▼ y ▼")  # ↓
        self.yDown2Button.pressed.connect(
                       lambda: self.move("y", -10*float(self.StepEdit.text())))

        self.zLabel = QtGui.QLabel('10.0')
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
        self.zup2Button = QtGui.QPushButton("▲ z ▲")
        self.zup2Button.pressed.connect(
                       lambda: self.zMoveUp(10))
        self.zDown2Button = QtGui.QPushButton("▼ z ▼")
        self.zDown2Button.pressed.connect(
                       lambda: self.zMoveDown(10))

        tamaño = 30
        self.xLabel.setFixedWidth(tamaño)
        self.yLabel.setFixedWidth(tamaño)
        self.zLabel.setFixedWidth(tamaño)
        tamaño = 50
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

        layout.addWidget(self.yname,       2, 0)
        layout.addWidget(self.yLabel,      2, 1)
        layout.addWidget(self.yUpButton,   1, 5, 3, 1)
        layout.addWidget(self.yDownButton, 3, 5, 2, 1)
        layout.addWidget(QtGui.QLabel("step x/y [µm] "), 4, 6, 1, 2)
        layout.addWidget(self.StepEdit,   5, 6)
        layout.addWidget(self.yUp2Button,   0, 5, 2, 1)
        layout.addWidget(self.yDown2Button, 4, 5, 2, 1)

        layout.addWidget(self.zname,       4, 0)
        layout.addWidget(self.zLabel,      4, 1)
        layout.addWidget(self.zup2Button,   0, 9, 2, 1)
        layout.addWidget(self.zUpButton,   1, 9, 3, 1)
        layout.addWidget(self.zDownButton, 3, 9, 2, 1)
        layout.addWidget(self.zDown2Button, 4, 9, 2, 1)
        layout.addWidget(QtGui.QLabel("step z [µm] "), 4, 10)
        layout.addWidget(self.zStepEdit,   5, 10)

        layout.addWidget(self.NameDirValue, 8, 0, 1, 7)
        layout.addWidget(self.read_pos_button, 0, 0, 1, 2)
#        Hline =QtGui.QLabel("________________________________________________________________________________________________")
#        Hline.setFixedWidth(300)
#        layout.addWidget(Hline,7, 0,1,7)

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
        tamaño = 50
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
        layout3.addWidget(self.goCMButton, 2, 4, 1, 2)
        layout3.addWidget(self.Gausscheck, 2, 1, 1, 2)

# ---- fin positioner part----------



# ----DOCK cosas, mas comodo!
        self.state = None
        hbox = QtGui.QHBoxLayout(self)
        dockArea = DockArea()

        viewDock = Dock('viewbox', size=(50, 45))
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

        grid_reference_Dock = Dock('Reference pos', size=(1, 1))
        grid_reference_Dock.addWidget(self.grid_reference)
        dockArea.addDock(grid_reference_Dock, 'left', posDock)


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

#        self.imageWidget = imageWidget

        # self.startRutine()
        # TODO: que lea de algun lado la posicion y la setee como start x,y,z

    # Agrego un atajo para que empieze tocando Ctrl+a
        self.liveviewAction = QtGui.QAction(self)
#        self.liveviewAction.setShortcut('Ctrl+a')
        QtGui.QShortcut(
            QtGui.QKeySequence('Ctrl+a'), self, self.liveviewKey)
#        self.liveviewAction.triggered.connect(self.liveviewKey)
#        self.liveviewAction.setEnabled(False)

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
            self.vueltaEdit.setStyleSheet(" background-color: ")

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
        self.maxcountsEdit.setStyleSheet(" background-color: ")


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
            self.maxcountsEdit.setStyleSheet(" background-color: ")
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
        self.grid_scan_control = True  # es parte del flujo en grid_start
        print("-----------------------------------------------------------")

    def scan_openshutter(self):
        """ abre el shutter que se va a utilizar para imprimir"""
        for i in range(len(shutters)):
            if self.scan_laser.currentText() == shutters[i]:
                self.openShutter(shutters[i])
                self.scan_shutterabierto = shutters[i]


#    def startingSteps(self):

# %% Starting Ramps
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
        self.scan_openshutter()  # abre el shutter elegido
#        self.Presets()  # abre los shutters que sean (STED)

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

        self.actualizar.setText("{}".format(str(ptime.time()-self.tic)))

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

#        try:  No necesito hacer el try, como mucho hace las cuentas con ceros
#            if self.pixelsoffL == 0:
#                self.counts2[0] = self.APD2[Napd-1] - self.APD2[0]
#            else:
#                self.counts2[0] = self.APD2[(Napd*(1+self.pixelsoffL))-1]
#                 -self.APD2[(Napd*(1+self.pixelsoffL-1))-1]
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
                AOchans2 = AOchans
            else:
                AOchans2 = AOchans[:2]
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
            AOchans2 = AOchans[:2]
            for n in range(len(AOchans2)):
                self.aotask.ao_channels.add_ao_voltage_chan(
                    physical_channel='Dev1/ao%s' % AOchans2[n],
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
        """ el triger con contadores es distinto (asi son los APD)"""
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
            # print("Aotask no estaba abierto")
            pass
        try:
            self.APD1task.stop()  # Apd
            self.APD1task.close()
        except:
            pass
            # print("APD1task no estaba abierto")
        try:
            self.APD2task.stop()  # Apd
            self.APD2task.close()
        except:
            pass
            # print("APD2task no estaba abierto")
        try:
            self.PMTtask.stop()  # PMT
            self.PMTtask.close()
        except:
            pass
            # print("PMTtask no estaba abierto")
        try:
            self.triggertask.stop()  # trigger, antes dotask
            self.triggertask.close()
        except:
            pass
            # print("Triggertask no estaba abierto")
#        try:
#            self.pointtask.stop()
#            self.pointtask.close()
#        except:
#            pass
#            # print("pointtasktask no estaba abierto")
#        try:
#            self.pointtask2.stop()
#            self.pointtask2.close()
#            # print("pointask 2no estaba abierto")
#        except:
#            pass
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
        self.triggerAPD = False  # separo los canales en partes
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
        self.moveZ(algo*float(getattr(self, 'z' + "StepEdit").text()))
        self.zDownButton.setEnabled(True)
        self.zDownButton.setStyleSheet(
            "QPushButton { background-color: }")
        self.zStepEdit.setStyleSheet(" background-color: ")

    def zMoveDown(self, algo=1):
        PosZ = self.initialPosition[2]
        if PosZ < algo*float(getattr(self, 'z' + "StepEdit").text()):
            print("OJO!, te vas a Z's negativos")
            self.zStepEdit.setStyleSheet(" background-color: red; ")
#            setStyleSheet("color: rgb(255, 0, 255);")
        else:
            self.moveZ(-algo*float(getattr(self, 'z' + "StepEdit").text()))
            self.zStepEdit.setStyleSheet(" background-color: ")
            if self.initialPosition[2] == 0:  # para no ir a z negativo
                self.zDownButton.setStyleSheet(
                    "QPushButton { background-color: orange; }")
        if PosZ == 0:  # para no ira z negativo
            self.zDownButton.setStyleSheet(
                "QPushButton { background-color: red; }"
                "QPushButton:pressed { background-color: blue; }")
            self.zDownButton.setEnabled(False)

# TODO incluir el eje z a todo
    def moveZ(self, dist):
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

            N = abs(int(dist*200))
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
              float(self.yLabel.text()), float(self.zLabel.text()))

        startX = float(self.xLabel.text())
        startY = float(self.yLabel.text())
        self.moveto((float(self.CMxValue.text()) + startX) - rango2,
                    (float(self.CMyValue.text()) + startY) - rango2,
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

# ---goto. Para ir a una posicion especifica

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

            if float(self.zLabel.text()) == 0:  # para no ir a z negativo
                self.zDownButton.setStyleSheet(
                    "QPushButton { background-color: red; }"
                    "QPushButton:pressed { background-color: blue; }")
                self.zDownButton.setEnabled(False)
            else:
                self.zDownButton.setStyleSheet(
                    "QPushButton { background-color: }")
                self.zDownButton.setEnabled(True)

            self.paramChanged()

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
        for i in range(len(shutters)):
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
        try:
            self.shuttertask = nidaqmx.Task("shutter")
            self.shuttertask.do_channels.add_do_chan(
                lines="Dev1/port0/line0:2", name_to_assign_to_lines='shutters',
                line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
            self.shuttering = True
        except:
            pass
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
            AOchans2 = AOchans[:2]
            with nidaqmx.Task("aotask") as aotask:
                # self.aotask = nidaqmx.Task('aotask')
                for n in range(len(AOchans2)):
                    aotask.ao_channels.add_ao_voltage_chan(
                        physical_channel='Dev1/ao%s' % AOchans2[n],
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
        fig.colorbar(p)
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
            (height, x, y, width_x, width_y) = self.params
            xg = int(np.floor(x))  # self.GaussxValue
            yg = int(np.floor(y))  # self.GaussyValue
#            X2 = np.transpose(X)
#            Y2 = np.transpose(Y)
            resol = 2
            xsum, ysum = 0, 0
            for i in range(resol):
                for j in range(resol):
                    ax.text(X[xg+i, yg+j], Y[xg+i, yg+j], "Ga", color='m')
#                    ax.text(X2[xc+i, yc+j], Y2[xc+i, yc+j], "Ga", color='m')
                    xsum = X[xg+i, yg+j] + xsum
                    ysum = Y[xg+i, yg+j] + ysum
            xmean = xsum / (resol**2)
            ymean = ysum / (resol**2)
            ax.text(xmean, ymean, "✔", color='r')
            ax.set_title("Centro en x={:.3f}, y={:.3f}".format(xmean, ymean))
            plt.text(0.95, 0.05, """
                    x : %.1f
                    y : %.1f """ % (X[xg, yg], Y[xg, yg]),
                     fontsize=16, horizontalalignment='right',
                     verticalalignment='bottom', transform=ax.transAxes)
        plt.show()
        toc = ptime.time()
        print("\n tiempo Plotlive", toc-tic, "\n")

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
        if self.GaussPlot:
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

# %%--- SaveFrame ---
    def save_name_update(self):
        self.edit_Name = str(self.edit_save.text())
        self.NameNumber = 0

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
        self.data = np.transpose(self.image)  # np.flip(np.flip(self.image,0),1
        params = fitgaussian(self.data)
        self.fit = gaussian(*params)
        self.params = params

        new_params = fitgaussian(self.image)
        (height, x, y, width_x, width_y) = new_params

        Normal = self.scanRange / self.numberofPixels  # Normalizo
        xx = x*Normal
        yy = y*Normal

        if 0 < xx < self.scanRange and 0 < yy < self.scanRange:
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
#        self.GaussxValue.setText(str(xx))
#        self.GaussyValue.setText(str(yy))
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
#        self.CMxValue.setText(str(xcm*Normal))
#        self.CMyValue.setText(str(ycm*Normal))
        self.CMxValue.setText("{:.2}".format(xcm*Normal))
        self.CMyValue.setText("{:.2}".format(ycm*Normal))

        self.point_graph_CM.setData([xcm], [ycm])
        self.vb.addItem(self.point_graph_CM)

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
            try:
                self.roi.disconnect()
            except: pass
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
                                 0.5, np.ceil(np.max(self.image))+2,
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
            size = (int(self.numberofPixels / 2), int(self.numberofPixels / 2))
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
            self.otrosDock.addWidget(self.HistoWidget)
        # lo conecto a algo que cambie en cada loop para que actualize solo
            self.actualizar.textChanged.connect(updatehistogram)
            updatehistogram()

        else:
            self.actualizar.textChanged.disconnect()
            self.vb.removeItem(self.roihist)
            self.roihist.hide()
#            self.HistoWidget.deleteLater()
#            self.roihist.sigRegionChanged.disconnect()


# %% Roi lineal
    def ROIlinear(self):
        larg = self.numberofPixels/1.5+10

        def updatelineal():
            array = self.linearROI.getArrayRegion(self.image, self.img)
            self.curve.setData(array)

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
        print(len(self.grid_x), len(self.grid_y))
        self.particulasEdit.setText(str(len(self.grid_x)))
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
        self.i_global = 1
        self.indice_impresionEdit.setText(str(self.i_global))

    def grid_start(self):
        """funcion que empieza el programa de imprimir una grilla
        (u otra cosa)"""
        self.grid_timer_traza = QtCore.QTimer()
        self.grid_timer_traza.timeout.connect(self.grid_detect_traza)

        self.grid_timer_scan = QtCore.QTimer()
        self.grid_timer_scan.timeout.connect(self.grid_detect_scan)

        self.grid_continue()

    def grid_continue(self):
        self.grid_move()
        self.grid_autofoco()
        self.grid_openshutter()
        self.grid_traza()

    def grid_move(self):
        """ se mueve siguiendo las coordenadas que lee del archivo"""
        self.PiezoOpenStep()
        startX = float(self.xLabel.text())
        startY = float(self.yLabel.text())
        self.grid_openshutter()
        self.aotask.write(np.array(
                [self.grid_x[self.i_global] + startX / convFactors['x'],
                 self.grid_y[self.i_global] + startY / convFactors['y']]),
                auto_start=True)
        print("me muevo",
              self.grid_x[self.i_global] + startX,
              self.grid_y[self.i_global] + startY)


    def grid_autofoco(self):
        print("aa")
        multifoco = np.arange(0,
                              int(self.particulasEdit.text())-1,
                              int(self.autofocEdit.text()))

        if self.i_global in multifoco:
            print("Estoy haciendo foco en el i=", self.i_global)
            time.sleep(2)
            self.focus_autocorr()

    def grid_openshutter(self):
        """ abre el shutter que se va a utilizar para imprimir"""
        for i in range(len(shutters)):
            if self.grid_laser.currentText() == shutters[i]:
                self.openShutter(shutters[i])
                self.grid_shutterabierto = shutters[i]

    def grid_traza(self):
        """ Abre la ventana nueva y mide la traza,
        preparado para detectar eventos de impresion"""
        self.main.grid_traza_control = False
        self.grid_timer_traza.start(10)  # no se que tiempo poner
        self.doit()

    def grid_detect_traza(self):
        """ Espera hasta detectar el evento de impresion.
        grid_timer_traza connect here"""
        if self.main.grid_traza_control:
            self.grid_timer_traza.stop()
#            self.grid_detect()
            self.grid_scan_signal()

    def grid_scan_signal(self):
        self.grid_scan_control = False
        self.grid_timer_scan.start(10)  # no se que tiempo poner
        self.grid_scan()

    def grid_detect_scan(self):
        if self.grid_scan_control:
            self.grid_timer_scan.stop()
            self.grid_detect()

    def grid_detect(self):
        """ Cuando detecta un evento de impresion, entra aca.
        Esta funcion define el paso siguiente.
        Puede ser: hacer autofoco, un scan de la PSF, o simplemente seguir """
        self.closeShutter(self.grid_shutterabierto)
#        time.sleep(1)

        Nmax = int(self.particulasEdit.text())-1  # self.Nmax  cantidad total de particulas
#        if self.scan_check.isChecked():
#            self.grid_scan()

        print(" i global ", self.i_global, "?")

        if self.i_global >= Nmax:
            self.main.file_path = self.old_folder
            self.NameDirValue.setText(self.old_folder)
            self.NameDirValue.setStyleSheet(" background-color: ; ")
#        self.moveto("back to origin")
            self.go_reference()
#            print("TERMINÓ LA GRILLA")
            self.indice_impresionEdit.setText(str(self.i_global+1))
            QtGui.QMessageBox.question(self,
                                       'Fin',
                                       'FIN!\
                                       \n fin',
                                       QtGui.QMessageBox.Ok)
        else:
            self.i_global += 1
            self.grid_continue()
#            self.grid_move()

    def grid_scan(self):
        """ Hace un confocal de la particula"""
#        time.sleep(2)
        print("grid scan")
        if self.scan_check.isChecked():
            self.liveviewButton.setChecked(True)
            self.liveview()


    def move_z(self, dist):
        """moves the position along the Z axis a distance dist."""
#        time.sleep(0.1)
        dist = dist
        print("me muevo a z", dist)
        with nidaqmx.Task("Ztask") as Ztask:
#            self.Ztask = nidaqmx.Task('Ztask')
            # Following loop creates the voltage channels
            n = 2
            Ztask.ao_channels.add_ao_voltage_chan(
                physical_channel='Dev1/ao{}'.format(n),
                name_to_assign_to_channel='chan_%s' % activeChannels[n],
                min_val=minVolt[activeChannels[n]],
                max_val=maxVolt[activeChannels[n]])

            N = abs(int(dist*100))
        # read initial position for all channels
            toc = ptime.time()
            rampz = np.linspace(float(self.zLabel.text()), dist, N)
            for i in range(N):
                Ztask.write([rampz[i] / (convFactors['z'])], auto_start=True)
#            Ztask.wait_until_done()
            print("se mueve en", np.round(ptime.time() - toc, 4), "segs")
        # update position text
            self.zLabel.setText("{}".format(np.around(float(rampz[-1]), 2)))

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
        for i in range(len(shutters)):
            if self.focus_laser.currentText() == shutters[i]:
                self.openShutter(shutters[i])
                self.focus_shutterabierto = shutters[i]

    def read_PD(self, color):
        """ Read de photodiode of the selecter 'color' """
#        channel = {shutters[0]: 0, shutters[1]: 1, shutters[2]: 2}
#        time.sleep(0.1)
        print("abre canal pmt")  # , channel)
        with nidaqmx.Task("PDtask") as PDtask:
#            self.PDtask = nidaqmx.Task('PDtask')
            PDtask.ai_channels.add_ai_voltage_chan(
                physical_channel='Dev1/ai{}'.format(PD_channels[color]),
                name_to_assign_to_channel='chan_PD')
            z_profile = PDtask.read()
#        read = np.random.rand(10)[0]*50
        return z_profile

    def focus_lock_focus(self):
        """ guarda el patron de intensidades, barriendo z en el foco actual"""
        self.Npasos = int(int(self.numberofPixelsEdit.text())/10)  # algun numero de pasos a definir (50 dice en algun lado)
        z_start = float(self.zLabel.text()) - (self.scanRange/2)
        z_end = float(self.zLabel.text()) + (self.scanRange/2)  # initialPosition[2]
        print("zstart=", z_start,"z end", z_end)
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
        self.move_z(float(self.zLabel.text()))
        self.focus_lock_button.setStyleSheet(
                "QPushButton { background-color: ; }"
                "QPushButton:pressed { background-color: blue; }")
#focus_lock_focus_rampas
    def focus_lock_focus_rampas(self):
        """ guarda el patron de intensidades, barriendo z en el foco actual"""
        Npasos = int(int(self.numberofPixelsEdit.text())/10)  # algun numero de pasos a definir (50 dice en algun lado)
        z_antes = float(self.zLabel.text())
        z_start = float(self.zLabel.text()) - (self.scanRange/2)
        z_end = float(self.zLabel.text()) + (self.scanRange/2)  # initialPosition[2]
        self.z_vector = np.linspace(z_start, z_end, Npasos)
        self.z_profile = np.zeros((Npasos))
#        self.focus_openshutter()
        self.move_z((z_start))
#        self.focus_openshutter()
        self.channel_z(self.sampleRate, Npasos)
        self.channel_PD_todos(self.sampleRate, Npasos)
        self.channel_triger(self.ztask, self.PDtask)

        self.ztask.write((self.z_vector / convFactors['z']),
                                                      auto_start = False)

        self.start_move_and_read(self.ztask,
                                 self.PDtask,
                                 (self.focus_laser.currentText()))
#        self.PDtimer_focus.start(10)  # no necesito usar un timer
        self.z_profile = self.PDtask.read(Npasos)

    # TODO: hacerlo con una rampa; averiguar cuanto tarda labview
        self.closeShutter((self.focus_laser.currentText()))
        self.channels_close()
        print("Foco lockeado. Tengo el z_profile")
        self.locked_focus = True

        self.move_z((z_antes))
        self.focus_lock_button.setStyleSheet(
                "QPushButton { background-color: ; }"
                "QPushButton:pressed { background-color: blue; }")

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
            self.focus_openshutter()
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
            self.closeShutter(self.focus_shutterabierto)
            j_final = (np.where(maxcorr == np.max(maxcorr))[0][0])
            z_max = np.max(self.new_profile[j_final, :])
            donde_z_max = np.where(self.new_profile[j_final, :] == z_max)

            plt.plot(self.new_profile[j_final, :], 'o-')
            plt.show()
            print(j_final, z_vector_corr[j_final, donde_z_max])

        else:
            print("No esta Lockeado el foco")

    def read_pos(self):
        """lee las entradas analogicas que manda la platina y se donde estoy"""
        self.getInitPos()
        print("read pos")
        print("similar a getInitPos (mas arriba)^^")

    def go_reference(self):
        print("arranco en", float(self.xLabel.text()),
              float(self.yLabel.text()), float(self.zLabel.text()))

        self.moveto(float(self.xrefLabel.text()),
                    float(self.yrefLabel.text()),
                    float(self.zrefLabel.text()))

        print("termino en", float(self.xLabel.text()),
              float(self.yLabel.text()), float(self.zLabel.text()))

    def set_reference(self):
#        self.read_pos()
        self.xrefLabel.setText(str(self.xLabel.text()))
        self.yrefLabel.setText(str(self.yLabel.text()))
        self.zrefLabel.setText(str(self.zLabel.text()))

# para saber si esta en potencia alta o baja
    def power_change(self):
        if self.power_check.isChecked():
            self.power_check.setText('Potencia \n BAJA')
            self.power_check.setStyleSheet("color: rgb(12, 183, 242); ")
        else:
            self.power_check.setText('Potencia \n ALTA')
            self.power_check.setStyleSheet("color: rgb(155, 064, 032); ")

    def scan_change(self):
        if self.scan_check.isChecked():
            self.scan_check.setText('scan? = SI')
            self.scan_check.setStyleSheet("color: orange; ")
        else:
            self.scan_check.setText('scan? = NO')
            self.scan_check.setStyleSheet("color: blue; ")

# Con esta funcion me encargo de que los menus tengan colores
    def color_menu(self, QComboBox):
        """ le pongo color a los menus"""
        if QComboBox.currentText() == shutters[0]:  # verde
            QComboBox.setStyleSheet("QComboBox{color: rgb(0,128,0);}\n")
        elif QComboBox .currentText() == shutters[1]:  # rojo
            QComboBox.setStyleSheet("QComboBox{color: rgb(255,0,0);}\n")
        elif QComboBox .currentText() == shutters[2]: # azul
            QComboBox.setStyleSheet("QComboBox{color: rgb(0,0,255);}\n")

# %% mejorando los channels

    def channel_xy(self, rate=0, samps_per_chan=0):
        
        # Create the channels
            self.xytask = nidaqmx.Task('xytask')
            AOchans2 = AOchans[:2]
        # Following loop creates the voltage channels
            for n in range(len(AOchans2)):
                self.xytask.ao_channels.add_ao_voltage_chan(
                    physical_channel='Dev1/ao%s' % AOchans2[n],
                    name_to_assign_to_channel='chan_%s' % activeChannels[n],
                    min_val=minVolt[activeChannels[n]],
                    max_val=maxVolt[activeChannels[n]])
            if rate !=0 and samps_per_chan != 0:
#            self.piezoramp = True
                self.xytask.timing.cfg_samp_clk_timing(
                    rate=rate,  # self.sampleRate
                    # source=r'100kHzTimeBase',
                    sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                    samps_per_chan=samps_per_chan)  # len(self.totalrampx)

    def channel_z(self, rate=0, samps_per_chan=0):
        # Create the channels
            self.ztask = nidaqmx.Task('ztask')
        # Following loop creates the voltage channels
            n=2
            self.ztask.ao_channels.add_ao_voltage_chan(
                physical_channel='Dev1/ao%s' % AOchans[n],
                name_to_assign_to_channel='chan_%s' % activeChannels[n],
                min_val=minVolt[activeChannels[n]],
                max_val=maxVolt[activeChannels[n]])
            if rate !=0 and samps_per_chan != 0:
#            self.piezoramp = True
                self.ztask.timing.cfg_samp_clk_timing(
                    rate=rate,  # self.sampleRate
                    # source=r'100kHzTimeBase',
                    sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                    samps_per_chan=samps_per_chan)  # len(self.totalrampx)

    def channel_PD(self, color=shutters[0], rate=0, samps_per_chan=0):
        """ en color va alguna de los valores de shutters"""
#            self.PMTon = True
        self.PDtask = nidaqmx.Task('PMTtask')
        self.PDtask.ai_channels.add_ai_voltage_chan(
            physical_channel='Dev1/ai{}'.format(PD_channels[color]),
            name_to_assign_to_channel='chan_PMT')
        if rate !=0 and samps_per_chan != 0:
            self.PDtask.timing.cfg_samp_clk_timing(
                    rate=rate,
                    sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                    samps_per_chan=samps_per_chan)

    def channel_PD_todos(self, rate=0, samps_per_chan=0):
        """ en color va alguna de los valores de shutters"""
#            self.PMTon = True

        self.PDtask = nidaqmx.Task('PMTtask')
        for n in range(len(PDchans)):
            self.PDtask.ai_channels.add_ai_voltage_chan(
                    physical_channel='Dev1/ai{}'.format(PDchans[n]),
                    name_to_assign_to_channel='chan_PD{}'.format(PDchans[n]))

        if rate !=0 and samps_per_chan != 0:
            self.PDtask.timing.cfg_samp_clk_timing(
                    rate=rate,
                    sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                    samps_per_chan=samps_per_chan)

    def channel_triger(self, task1, task2, rate=10**5, samples_long=1):
        self.triggertask = nidaqmx.Task('TriggerPDtask')
    # Create the signal trigger
        num = samples_long  # int(self.triggerEdit.text())
        trigger2 = [True, True, False]
        # trigger2 = np.tile(trigger, self.numberofPixels)
        self.trigger = np.concatenate((np.zeros(num, dtype="bool"),
                                       trigger2))

    # Configure the digital channels to trigger the synchronization signal
        self.triggertask.do_channels.add_do_chan(
            lines="Dev1/port0/line6", name_to_assign_to_lines='chan6',
            line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)

        self.triggertask.timing.cfg_samp_clk_timing(
                     rate=rate,  # muestras por segundo
                     sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                     # source='100kHzTimebase',
                     active_edge=nidaqmx.constants.Edge.RISING,
                     samps_per_chan=len(self.trigger))
    # Configure a start trigger to synchronizate the measure and movement
        triggerchannelname = "PFI4"
        task1.triggers.start_trigger.cfg_dig_edge_start_trig(
                                            trigger_source=triggerchannelname)
        task2.triggers.start_trigger.cfg_dig_edge_start_trig(
                                            trigger_source=triggerchannelname)
#        self.triggerPMT = True

    def vector_to_move(self):
        self.xytask.write(np.array(
            [self.totalrampx / convFactors['x'],
             self.totalrampy / convFactors['y']]), auto_start=False)

    def start_move_and_read(self, task1, task2, color=shutters[0]):
        """ Send the signals to the NiDaq,
        but only start when the trigger is on """

        task1.start()
        task2.start()
        print("ya arranca...")
        self.openShutter(color)  # abre el shutter elegido

        self.triggertask.write(self.trigger, auto_start=True)

    def channels_close(self):
        try:
            self.xytask.stop()
            self.xytask.close()
        except: pass
        try:
            self.ztask.stop()
            self.ztask.close()
        except: pass
        try:
            self.PDtask.stop()
            self.PDtask.close()
        except: pass
        try:
            self.triggertask.stop()
            self.triggertask.close()
        except: pass

# %% Point scan , que ahora es traza

    def PointStart(self):
        self.done()
        self.doit()
        print("Trazando...")

    def PointScanStop(self):
        self.w.pointtimer.stop()
#        self.pointtimer.stop()
# #        self.pointtask.stop()
# #        self.pointtask.close()
# #        self.pointtask2.stop()
# #        self.pointtask2.close()
        print("fin traza")

    def doit(self):
        print("Opening a new popup window...")
        self.w = MyPopup_traza(self.main, self)
        self.w.setGeometry(QtCore.QRect(750, 50, 450, 600))
        self.w.show()


class MyPopup_traza(QtGui.QWidget):
    """ new class to create a new window for the trace menu"""

    def closeEvent(self, event):
        self.stop()
        print("Paró y cerró la traza")

    def __init__(self, main, ScanWidget, *args, **kwargs):
        QtGui.QWidget.__init__(self)
        super().__init__(*args, **kwargs)
        self.main = main
        self.ScanWidget = ScanWidget  # call ScanWidget
        self.traza_Widget2 = pg.GraphicsLayoutWidget()
        self.running = False
        grid = QtGui.QGridLayout()
        self.setLayout(grid)

        self.p6 = self.traza_Widget2.addPlot(row=2, col=1, title="Traza")
        self.p6.showGrid(x=True, y=True)
        self.curve = self.p6.plot(open='y')
        self.line = self.p6.plot(open='y')
        self.line1 = self.p6.plot(open='y')
        self.line2 = self.p6.plot(open='y')

    #  buttons: play button
        self.play_pause_Button = QtGui.QPushButton('► Play / Pause || (F1)')
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
#        self.umbralLabel = self.ScanWidget.umbralLabel  # QtGui.QLabel('Umbral'
        self.umbralEdit = self.ScanWidget.umbralEdit  # QtGui.QLineEdit('10')
        self.umbralEdit.setFixedWidth(40)
        self.umbralEdit.setToolTip('promedios de valores nuevo/anteriores ')

        self.PointLabel = QtGui.QLabel('<strong>0.00|0.00')
        grid.addWidget(self.traza_Widget2,      0, 0, 1, 7)
        grid.addWidget(self.play_pause_Button,  1, 0)
        grid.addWidget(self.stop_Button,        1, 1)
#        grid.addWidget(self.umbralLabel,        1, 3)
#        grid.addWidget(self.umbralEdit,         1, 4)
        grid.addWidget(self.PointLabel,         1, 5)
        grid.addWidget(self.save_Button,        1, 6)
        self.setWindowTitle("Traza. (ESC lo cierra bien)")
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

    def close_win(self):
        self.stop()
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
            self.traza_openshutter()
            self.timer_inicio = ptime.time()
            if self.running:
                self.pointtimer.start(self.tiempo)
            else:
                self.PointScan()
        else:
            print("pause")
            self.ScanWidget.closeShutter(self.traza_shutterabierto)
            self.pointtimer.stop()
            # self.pause_Button.setStyleSheet(
            #        "QPushButton { background-color: red; }")

    def stop(self):
        print("stop")
        self.ScanWidget.closeShutter(self.traza_shutterabierto)
        try:
            self.pointtimer.stop()
        except IOError as e:
            print("I/O error({0}): {1}".format(e.errno, e.strerror))
        self.running = False
        self.play_pause_Button.setChecked(False)
        try:
            self.pointtask.stop()
            self.pointtask.close()
        except:  # pass
            print("pointtasktask no estaba abierto")
        try:
            self.pointtask2.stop()
            self.pointtask2.close()
        except:  # pass
            print("pointtasktask2 no estaba abierto")

    def traza_openshutter(self):
        """ abre el shutter que se va a utilizar para imprimir"""
        for i in range(len(shutters)):
            if self.ScanWidget.traza_laser.currentText() == shutters[i]:
                self.ScanWidget.openShutter(shutters[i])
                self.traza_shutterabierto = shutters[i]

    def save_traza(self, imprimiendo=False):
        try:
            print("va a aguardar")
            # filepath = self.file_path
            filepath = self.main.file_path
            timestr = time.strftime("%d%m%Y-%H%M%S")
            if imprimiendo:
                timestr = str("Particula-") + str(self.ScanWidget.i_global)
                self.ScanWidget.edit_save.setText(str(timestr))
            name = str(filepath + "/" + timestr + "-Traza" + ".txt")
            print("va a abrir el name")
            f = open(name, "w")
            np.savetxt(name,
                       np.transpose([self.timeaxis[:self.ptr1],
                                     self.data1[:self.ptr1]]),
                       header="{} y umbral={:.3}".format(
                        timestr, float(self.umbralEdit.text())))
            print("va a cerrarlo")
            f.close()
            print("\n Guardo la Traza")
        except IOError as e:
            print("I/O error({0}): {1}".format(e.errno, e.strerror))

#        fig, ax = plt.subplots()
#        plt.plot(self.timeaxis[:self.ptr1], self.data1[:self.ptr1])
#        ax.set_xlabel('Tiempo (s) (puede fallar)')
#        ax.set_ylabel('Intensity (V)')
#        plt.show()

    def PointScan(self):
        self.running = True
        self.tiempo = 1  # ms  # refresca el numero cada este tiempo
        self.Napd = int(np.round(apdrate * self.tiempo/10**3))
        print(self.Napd)
        self.points = np.zeros(self.Napd)
#        int(np.round((apdrate * (self.tiempo/10**3)))))
        self.points2 = np.copy(self.points)

        self.pointtask = nidaqmx.Task('pointtask')
        # Configure the counter channel to read the APD
        self.pointtask.ci_channels.add_ci_count_edges_chan(
                            counter='Dev1/ctr{}'.format(COchans[0]),
                            name_to_assign_to_channel=u'Line_counter',
                            initial_count=0)

        self.pointtask.timing.cfg_samp_clk_timing(
          rate=apdrate,
          sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
          source=r'100kHzTimebase',  # 1000k
          samps_per_chan=len(self.points))

        self.pointtask2 = nidaqmx.Task('pointtask2')
        # Configure the counter channel to read the APD
        self.pointtask2.ci_channels.add_ci_count_edges_chan(
                            counter='Dev1/ctr{}'.format(COchans[1]),
                            name_to_assign_to_channel=u'Line_counter',
                            initial_count=0)
        self.pointtask2.timing.cfg_samp_clk_timing(
          rate=apdrate,
          sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
          source=r'100kHzTimebase',  # 1000k
          samps_per_chan=len(self.points))

        self.ptr1 = 0
        self.timeaxis = np.empty(100)
        self.data1 = np.empty(100)
#        self.data2 = np.empty(100)
    # Quiero saber cuanto tarda para que coincidan los tiempos
        self.tiemporeal = self.tiempo
        tic = ptime.time()
        self.updatePoint()
        tiic = ptime.time()
        self.tiemporeal = (tiic-tic)*2
        print("tiempo propuesto=", self.tiempo*10**3, "ms")
        print("tiempo real=", self.tiemporeal*10**3, "ms")

        self.ptr1 = 0
        self.timeaxis = np.empty(100)
        self.data1 = np.empty(100)
#        self.data2 = np.empty(100)

        self.traza_openshutter()
        self.timer_inicio = ptime.time()
        self.pointtimer = QtCore.QTimer()
        self.pointtimer.timeout.connect(self.updatePoint)
        self.pointtimer.start(self.tiemporeal)

    def updatePoint(self):
        tic = ptime.time()
        N = len(self.points)
        self.points[:] = self.pointtask.read(N)
        self.points2[:] = self.pointtask2.read(N)
        tiic = ptime.time()
#        if self.ptr1 ==0:
#            self.tiemporeal = tiic-tic
        m = np.max(self.points)  # mean
        m2 = np.mean(self.points2)
#        #print("valor traza", m)
        self.PointLabel.setText("<strong>{0:.2e}|{0:.2e}".format(
                                           float(m), float(m2)))
#        sig2 = np.mean(self.points2)
        self.timeaxis[self.ptr1] = self.tiemporeal * self.ptr1  # *self.tiempo
        self.data1[self.ptr1] = m
        self.ptr1 += 1
        if self.ptr1 >= self.data1.shape[0]:
            tmpdata1 = self.data1
            self.data1 = np.empty(self.data1.shape[0] * 2)
            self.data1[:tmpdata1.shape[0]] = tmpdata1
            tmptime = self.timeaxis
            self.timeaxis = np.empty(self.timeaxis.shape[0] * 2)
            self.timeaxis[:tmptime.shape[0]] = tmptime
#            tmpdata2 = self.data2
#            self.data2 = np.empty(self.data2.shape[0] * 2)
#            self.data2[:tmpdata2.shape[0]] = tmpdata2
        tac = ptime.time()
#        self.timeaxis.append((self.tiempo * 10**-3)*self.ptr1)
#        self.data1.append(m)
#        self.ptr1 += 1
#        self.curve.setData(self.timeaxis, self.data1)
        self.curve.setData(self.timeaxis[:self.ptr1], self.data1[:self.ptr1],
                           pen=pg.mkPen('r', width=1),
                           shadowPen=pg.mkPen('b', width=3))

        mediototal = np.mean(self.data1[:self.ptr1])
        self.line.setData(self.timeaxis[:self.ptr1],
                          np.ones(len(self.timeaxis[:self.ptr1])) * mediototal,
                          pen=pg.mkPen('c', width=1))
        tec = ptime.time()
        M = 30
        M2 = 5
        if self.ptr1 < M:
            mediochico = np.mean(self.data1[:self.ptr1])
            self.timeaxis2 = self.timeaxis[:self.ptr1]
            MMM = self.ptr1
            if self.ptr1 < M2:
                mediochico2 = np.mean(self.data1[:self.ptr1])
#                MM2 = 0
            else:
                mediochico2 = np.mean(self.data1[:self.ptr1-M2])
#                MM2 = M2
        else:
            mediochico = np.mean(self.data1[self.ptr1-M:self.ptr1])
            self.timeaxis2 = self.timeaxis[self.ptr1-M:self.ptr1]
            MMM = M
            mediochico2 = np.mean(self.data1[self.ptr1-M-M2:self.ptr1-M2])

        tuc = ptime.time()
        self.line1.setData(self.timeaxis2,
                           np.ones(MMM) * mediochico,
                           pen=pg.mkPen('g', width=2))
        self.line2.setData(self.timeaxis2[:],
                           np.ones(MMM) * mediochico2,
                           pen=pg.mkPen('y', width=2))

        self.PointLabel.setText("<strong>{:.3}|{:.3}".format(
                                float(mediochico), float(mediochico2)))
#        print(mediochico, mediochico2)

#        if ptime.time() - self.timer_inicio > float(self.ScanWidget.tmaxEdit.text()):
#            print("se paso el tiempo!!")

        if mediochico >= mediochico2*float(self.umbralEdit.text()):
            self.PointLabel.setStyleSheet(" background-color: orange")
        else:
            self.PointLabel.setStyleSheet(" background-color: ")
        try:
            if self.timer_inicio ==0:
                self.timer_inicio =0
        except:
            self.timer_inicio = ptime.time()
    # Este if not es el que define si se esta corriendo una grilla
        if not self.main.grid_traza_control:
            if mediochico > mediochico2*float(self.umbralEdit.text()) or ptime.time() - self.timer_inicio > float(self.ScanWidget.tmaxEdit.text()):
                print("medio=", np.round(mediochico))
                self.save_traza(True)
                self.stop()
                self.close_win()
                self.main.grid_traza_control = True

        toc = ptime.time()
        print("\ntiempo Total", np.round((toc-tic)*10**3,3), "(ms)")
        print("tiempo alargando vectores", np.round((tac-tiic)*10**3,3), "(ms)")
        print("tiempo del medio", np.round((tec-tac)*10**3,3), "(ms)")
        print("tiempo armar promedios varios", np.round((tuc-tec)*10**3,3), "(ms)")
        print("tiempo plotear y escribir orange", np.round((toc-tuc)*10**3,3), "(ms)")
        print("tiemporeal", np.round((self.tiemporeal)*10**3,3), "(ms)")
        print("tiempo leyendo apd", np.round((tiic-tic)*10**3,3), "\n")



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
#win = ScanWidget(device)
win = MainWindow()
win.show()

app.exec_()
