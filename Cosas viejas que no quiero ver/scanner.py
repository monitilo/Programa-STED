# -*- coding: utf-8 -*-
"""
Created on Wed Mar 30 10:32:36 2016

@authors: Luciano Masullo, Andreas Bodén, Shusei Masuda, Federico Barabas,
    Aurelién Barbotin.
"""

import os
import numpy as np
import time
import re
import configparser

import pyqtgraph as pg
from pyqtgraph.dockarea import Dock, DockArea
from PyQt4 import QtGui, QtCore

import matplotlib.pyplot as plt
import collections
import nidaqmx

import control.guitools as guitools

from cv2 import rectangle, goodFeaturesToTrack, moments

# These dictionnaries contain values specific to the different axis of our
# piezo motors.
# They are the movements in µm induced by a command of 1V
convFactors = {'x': 4.06, 'y': 3.9, 'z': 10}

# Minimum and maximum voltages for the different piezos
minVolt = {'x': -10, 'y': -10, 'z': 0}
maxVolt = {'x': 10, 'y': 10, 'z': 10}


class Positionner(QtGui.QWidget):
    """This class communicates with the different analog outputs of the nidaq
    card. When not scanning, it drives the 3 axis x, y and z.

    :param ScanWidget main: main scan GUI"""

    def __init__(self, main):
        super().__init__()

        self.scanWidget = main
        self.focusWgt = self.scanWidget.focusWgt

        # Position of the different devices in V
        self.x = 0.00
        self.y = 0.00
        self.z = 0.00

        # Parameters for the ramp (driving signal for the different channels)
        self.rampTime = 100  # Time for each ramp in ms
        self.sampleRate = 10**2  # 10**5
        self.nSamples = int(self.rampTime * 10**-3 * self.sampleRate)

        # This boolean is set to False when tempesta is scanning to prevent
        # this positionner to access the analog output channels
        self.isActive = True
        self.activeChannels = ["x", "y", "z"]
        self.AOchans = [0, 1, 2]     # Order corresponds to self.channelOrder

        self.aotask = nidaqmx.Task("positionnerTask")
        # Following loop creates the voltage channels
        for n in self.AOchans:
            self.aotask.ao_channels.add_ao_voltage_chan(
                physical_channel='Dev1/ao%s' % n,
                name_to_assign_to_channel=self.activeChannels[n],
                min_val=minVolt[self.activeChannels[n]],
                max_val=maxVolt[self.activeChannels[n]])

        self.aotask.timing.cfg_samp_clk_timing(
            rate=self.sampleRate,
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=self.nSamples)

        # Axes control
        self.xLabel = QtGui.QLabel(
            "<strong>x = {0:.2f} µm</strong>".format(self.x))
        self.xLabel.setTextFormat(QtCore.Qt.RichText)
        self.xUpButton = QtGui.QPushButton("+")
        self.xUpButton.pressed.connect(self.xMoveUp)
        self.xDownButton = QtGui.QPushButton("-")
        self.xDownButton.pressed.connect(self.xMoveDown)
        self.xStepEdit = QtGui.QLineEdit("1")  # estaban en 0.05<
        self.xStepUnit = QtGui.QLabel(" µm")

        self.yLabel = QtGui.QLabel(
            "<strong>y = {0:.2f} µm</strong>".format(self.y))
        self.yLabel.setTextFormat(QtCore.Qt.RichText)
        self.yUpButton = QtGui.QPushButton("+")
        self.yUpButton.pressed.connect(self.yMoveUp)
        self.yDownButton = QtGui.QPushButton("-")
        self.yDownButton.pressed.connect(self.yMoveDown)
        self.yStepEdit = QtGui.QLineEdit("1")
        self.yStepUnit = QtGui.QLabel(" µm")

        self.zLabel = QtGui.QLabel(
            "<strong>z = {0:.2f} µm</strong>".format(self.z))
        self.zLabel.setTextFormat(QtCore.Qt.RichText)
        self.zUpButton = QtGui.QPushButton("+")
        self.zUpButton.pressed.connect(self.zMoveUp)
        self.zDownButton = QtGui.QPushButton("-")
        self.zDownButton.pressed.connect(self.zMoveDown)
        self.zStepEdit = QtGui.QLineEdit("1")
        self.zStepUnit = QtGui.QLabel(" µm")

        layout = QtGui.QGridLayout()
        self.setLayout(layout)
        layout.addWidget(self.xLabel, 1, 0)
        layout.addWidget(self.xUpButton, 1, 1)
        layout.addWidget(self.xDownButton, 1, 2)
        layout.addWidget(QtGui.QLabel("Step"), 1, 3)
        layout.addWidget(self.xStepEdit, 1, 4)
        layout.addWidget(self.xStepUnit, 1, 5)
        layout.addWidget(self.yLabel, 2, 0)
        layout.addWidget(self.yUpButton, 2, 1)
        layout.addWidget(self.yDownButton, 2, 2)
        layout.addWidget(QtGui.QLabel("Step"), 2, 3)
        layout.addWidget(self.yStepEdit, 2, 4)
        layout.addWidget(self.yStepUnit, 2, 5)
        layout.addWidget(self.zLabel, 3, 0)
        layout.addWidget(self.zUpButton, 3, 1)
        layout.addWidget(self.zDownButton, 3, 2)
        layout.addWidget(QtGui.QLabel("Step"), 3, 3)
        layout.addWidget(self.zStepEdit, 3, 4)
        layout.addWidget(self.zStepUnit, 3, 5)

    def move(self, axis, dist):
        """moves the position along the axis specified a distance dist."""

        # read initial position for all channels
        texts = [getattr(self, ax + "Label").text()
                 for ax in self.activeChannels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]
        initPos = np.array(initPos, dtype=float)[:, np.newaxis]
        fullPos = np.repeat(initPos, self.nSamples, axis=1)

        # make position ramp for moving axis
        ramp = makeRamp(0, dist, self.nSamples)
        fullPos[self.activeChannels.index(axis)] += ramp

        # convert um to V and send signal to piezo
#        factors = np.array([i for i in convFactors.values()])[:, np.newaxis]

        """ Esta linea generaba un vector con 3 componentesque en cada corrida se
 acomodan distinto, es culpa del diccionario, lo escribo distinto
 (linea 146 se va--> 150 entra)"""

        factors = np.array([convFactors['x'], convFactors['y'],
                           convFactors['z']])[:, np.newaxis]
        fullSignal = fullPos/factors
        self.aotask.write(fullSignal, auto_start=True)
        self.aotask.wait_until_done()
        self.aotask.stop()

        # update position text
        newPos = fullPos[self.activeChannels.index(axis)][-1]
        newText = "<strong>" + axis + " = {0:.2f} µm</strong>".format(newPos)
        getattr(self, axis + "Label").setText(newText)

    def xMoveUp(self):
        self.move('x', float(getattr(self, 'x' + "StepEdit").text()))

    def xMoveDown(self):
        self.move('x', -float(getattr(self, 'x' + "StepEdit").text()))

    def yMoveUp(self):
        self.move('y', float(getattr(self, 'y' + "StepEdit").text()))

    def yMoveDown(self):
        self.move('y', -float(getattr(self, 'y' + "StepEdit").text()))

    def zMoveUp(self):
        self.move('z', float(getattr(self, 'z' + "StepEdit").text()))

    def zMoveDown(self):
        self.move('z', -float(getattr(self, 'z' + "StepEdit").text()))

    def resetChannels(self, channels):
        """Method called when the analog output channels need to be used by
        another resource, typically for scanning. Deactivates the Positionner
        when it is active and reactives it when it is not, typically after a
        scan.

        :param dict channels: the channels which are used or released by
        another object. The positionner does not touch the other channels"""
        if(self.isActive):
            self.aotask.stop()
            self.aotask.close()
            del self.aotask
            totalChannels = ["x", "y", "z"]
            self.aotask = nidaqmx.Task("positionnerTask")

            # returns a list containing the axis not in use
            self.activeChannels = [
                x for x in totalChannels if x not in channels]

            try:
                axis = self.activeChannels[0]
                n = self.AOchans[self.activeChannels.index(axis)]
                channel = "Dev1/ao%s" % n
                self.aotask.ao_channels.add_ao_voltage_chan(
                    physical_channel=channel, name_to_assign_to_channel=axis,
                    min_val=minVolt[axis], max_val=maxVolt[axis])
            except IndexError:
                pass
            self.isActive = False

        else:
            # Restarting the analog channels
            self.aotask.stop()
            self.aotask.close()
            del self.aotask
            self.aotask = nidaqmx.Task("positionnerTask")

            totalChannels = ["x", "y", "z"]
            self.activeChannels = totalChannels
            for axis in totalChannels:
                n = self.AOchans[self.activeChannels.index(axis)]
                channel = "Dev1/ao%s" % n
                self.aotask.ao_channels.add_ao_voltage_chan(
                    physical_channel=channel, name_to_assign_to_channel=axis,
                    min_val=minVolt[axis], max_val=maxVolt[axis])

            self.aotask.timing.cfg_samp_clk_timing(
                rate=self.sampleRate,
                sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                samps_per_chan=self.nSamples)
            self.aotask.start()
            self.isActive = True

        for axis in self.activeChannels:
            newText = "<strong>" + axis + " = {0:.2f} µm</strong>".format(0)
            getattr(self, axis + "Label").setText(newText)

    def closeEvent(self, *args, **kwargs):
        if(self.isActive):
            # Resets the sliders, which will reset each channel to 0
            self.aotask.wait_until_done(timeout=2)
            self.aotask.stop()
            self.aotask.close()


def saveScan(scanWid):

        config = configparser.ConfigParser()
        config.optionxform = str

        config['pxParValues'] = scanWid.pxParValues
        config['scanParValues'] = scanWid.scanParValues
        config['Modes'] = {'scanMode': scanWid.scanMode.currentText(),
                           'scan_or_not': scanWid.scanRadio.isChecked()}
        fileName = QtGui.QFileDialog.getSaveFileName(scanWid, 'Save scan',
                                                     scanWid.scanDir)
        if fileName == '':
            return

        with open(fileName, 'w') as configfile:
            config.write(configfile)


def loadScan(scanWid):

    config = configparser.ConfigParser()
    config.optionxform = str

    fileName = QtGui.QFileDialog.getOpenFileName(scanWid, 'Load scan',
                                                 scanWid.scanDir)
    if fileName == '':
        return

    config.read(fileName)

    for key in scanWid.pxParValues:
        scanWid.pxParValues[key] = float(config._sections['pxParValues'][key])
        scanWid.pxParameters[key].setText(
            str(1000*float(config._sections['pxParValues'][key])))

    for key in scanWid.scanParValues:
        value = config._sections['scanParValues'][key]
        scanWid.scanParValues[key] = float(value)
        if key == 'seqTime':
            scanWid.scanPar[key].setText(
                str(1000*float(config._sections['scanParValues'][key])))
        else:
            scanWid.scanPar[key].setText(
                config._sections['scanParValues'][key])

    scanOrNot = (config._sections['Modes']['scan_or_not'] == 'True')
    scanWid.setScanOrNot(scanOrNot)
    if scanOrNot:
        scanWid.scanRadio.setChecked(True)
    else:
        scanWid.contLaserPulsesRadio.setChecked(True)

    scanMode = config._sections['Modes']['scanMode']
    scanWid.setScanMode(scanMode)
    scanWid.scanMode.setCurrentIndex(scanWid.scanMode.findText(scanMode))

    scanWid.updateScan(scanWid.allDevices)
    scanWid.graph.update()

# ---Agregado por german-----------------------------


class ConfocalWidget(QtGui.QMainWindow):
    ''' Me arme la interface exactamente igual que ScanWidget,
    para poder modificar cosas, mientras tengo en otra solapa el que anda.'''
    def __init__(self, device, main, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.scanInLiveviewWar = QtGui.QMessageBox()
        self.scanInLiveviewWar.setInformativeText(
            "You need to be in liveview to scan")

        self.digModWarning = QtGui.QMessageBox()
        self.digModWarning.setInformativeText(
            "You need to be in digital laser modulation and external "
            "frame-trigger acquisition mode")

        self.nidaq = device
        self.main = main
        self.focusWgt = main.FocusLockWidget
        self.focusLocked = self.focusWgt.locked

        # The port order in the NIDAQ follows this same order.
        # We chose to follow the temporal sequence order
        self.allDevices = ['405', '488', '473', 'CAM']
        self.channelOrder = ['x', 'y', 'z']

        self.saveScanBtn = QtGui.QPushButton('Save Scan')

        self.scanDir = os.path.join(self.main.controlFolder, 'scans')

        if not os.path.exists(self.scanDir):
            os.makedirs(self.scanDir)

        def saveScanFcn(): return saveScan(self)
        self.saveScanBtn.clicked.connect(saveScanFcn)
        self.loadScanBtn = QtGui.QPushButton('Load Scan')

        def loadScanFcn(): return loadScan(self)
        self.loadScanBtn.clicked.connect(loadScanFcn)

        self.sampleRateEdit = QtGui.QLineEdit()

        self.sizeXPar = QtGui.QLineEdit('2')
        self.sizeXPar.textChanged.connect(
            lambda: self.scanParameterChanged('sizeX'))
        self.sizeYPar = QtGui.QLineEdit('2')
        self.sizeYPar.textChanged.connect(
            lambda: self.scanParameterChanged('sizeY'))
        self.sizeZPar = QtGui.QLineEdit('10')
        self.sizeZPar.textChanged.connect(
            lambda: self.scanParameterChanged('sizeZ'))
        self.seqTimePar = QtGui.QLineEdit('10')     # ms
        self.seqTimePar.textChanged.connect(
            lambda: self.scanParameterChanged('seqTime'))
        self.nrFramesPar = QtGui.QLabel()
        self.scanDuration = 0
        self.scanDurationLabel = QtGui.QLabel(str(self.scanDuration))
        self.stepSizeXYPar = QtGui.QLineEdit('1')
        self.stepSizeXYPar.textChanged.connect(
            lambda: self.scanParameterChanged('stepSizeXY'))
        self.NumberpixPar = QtGui.QLineEdit('64')
        self.NumberpixPar.textChanged.connect(
            lambda: self.scanParameterChanged('Number of pixels'))  # Ger
        self.stepSizeZPar = QtGui.QLineEdit('1')
        self.stepSizeZPar.textChanged.connect(
            lambda: self.scanParameterChanged('stepSizeZ'))
        self.sampleRate = 100000

        self.scanMode = QtGui.QComboBox()
        self.scanModes = ['step scan', 'otro scan', 'viejo scan']
        self.scanMode.addItems(self.scanModes)
        self.scanMode.currentIndexChanged.connect(
            lambda: self.setScanMode(self.scanMode.currentText()))

        self.primScanDim = QtGui.QComboBox()
        self.scanDims = ['x', 'y']
        self.primScanDim.addItems(self.scanDims)
        self.primScanDim.currentIndexChanged.connect(
            lambda: self.setPrimScanDim(self.primScanDim.currentText()))

        self.scanPar = {
                'sizeX': self.sizeXPar,
                'sizeY': self.sizeYPar,
                'sizeZ': self.sizeZPar,
                'seqTime': self.seqTimePar,
                'stepSizeXY': self.stepSizeXYPar,
                'Number of pixels': self.NumberpixPar,  # Ger
                'stepSizeZ': self.stepSizeZPar
                }

        self.scanParValues = {
                'sizeX': float(self.sizeXPar.text()),
                'sizeY': float(self.sizeYPar.text()),
                'sizeZ': float(self.sizeZPar.text()),
                'seqTime': 0.001*float(self.seqTimePar.text()),
                'stepSizeXY': float(self.stepSizeXYPar.text()),
                'Number of pixels': int(self.NumberpixPar.text()),  # Ger
                'stepSizeZ': float(self.stepSizeZPar.text())
                }

        self.start405Par = QtGui.QLineEdit('0')
        self.start405Par.textChanged.connect(
            lambda: self.pxParameterChanged('start405'))
        self.start488Par = QtGui.QLineEdit('0')
        self.start488Par.textChanged.connect(
            lambda: self.pxParameterChanged('start488'))
        self.start473Par = QtGui.QLineEdit('0')
        self.start473Par.textChanged.connect(
            lambda: self.pxParameterChanged('start473'))
        self.startCAMPar = QtGui.QLineEdit('0')
        self.startCAMPar.textChanged.connect(
            lambda: self.pxParameterChanged('startCAM'))

        self.end405Par = QtGui.QLineEdit('0')
        self.end405Par.textChanged.connect(
            lambda: self.pxParameterChanged('end405'))
        self.end488Par = QtGui.QLineEdit('0')
        self.end488Par.textChanged.connect(
            lambda: self.pxParameterChanged('end488'))
        self.end473Par = QtGui.QLineEdit('0')
        self.end473Par.textChanged.connect(
            lambda: self.pxParameterChanged('end473'))
        self.endCAMPar = QtGui.QLineEdit('0')
        self.endCAMPar.textChanged.connect(
            lambda: self.pxParameterChanged('endCAM'))

        self.pxParameters = {'start405': self.start405Par,
                             'start488': self.start488Par,
                             'start473': self.start473Par,
                             'startCAM': self.startCAMPar,
                             'end405': self.end405Par,
                             'end488': self.end488Par,
                             'end473': self.end473Par,
                             'endCAM': self.endCAMPar}

        self.pxParValues = {'start405': 0.001*float(self.start405Par.text()),
                            'start488': 0.001*float(self.start488Par.text()),
                            'start473': 0.001*float(self.start473Par.text()),
                            'startCAM': 0.001*float(self.startCAMPar.text()),
                            'end405': 0.001*float(self.end405Par.text()),
                            'end488': 0.001*float(self.end488Par.text()),
                            'end473': 0.001*float(self.end473Par.text()),
                            'endCAM': 0.001*float(self.endCAMPar.text())}

        self.stageScan = StageScan(self.sampleRate)
        self.pxCycle = PixelCycle(self.sampleRate)
        self.graph = GraphFrame(self.pxCycle)
        self.graph.plot.getAxis('bottom').setScale(1000/self.sampleRate)
        self.graph.setFixedHeight(100)
        self.updateScan(self.allDevices)
        self.scanParameterChanged('seqTime')

        self.multiScanWgt = LuchoScanWidget(self)  # MultipleScanWidget(self)

        self.scanRadio = QtGui.QRadioButton('Scann')
        self.scanRadio.clicked.connect(lambda: self.setScanOrNot(True))
        self.scanRadio.setChecked(True)
        self.contLaserPulsesRadio = QtGui.QRadioButton('Cont. Laser Pulses')
        self.contLaserPulsesRadio.clicked.connect(
            lambda: self.setScanOrNot(False))

        self.scanButton = QtGui.QPushButton('OtroConfoscan')
        self.scanning = False
        self.scanButton.clicked.connect(self.scanOrAbort)
        self.previewButton = QtGui.QPushButton('Plot scan path')
        self.previewButton.setSizePolicy(QtGui.QSizePolicy.Preferred,
                                         QtGui.QSizePolicy.Expanding)
        self.previewButton.clicked.connect(self.previewScan)
        self.continuousCheck = QtGui.QCheckBox('Repeat')

        self.cwidget = QtGui.QWidget()
        self.setCentralWidget(self.cwidget)
        grid = QtGui.QGridLayout()
        self.cwidget.setLayout(grid)

        grid.addWidget(self.loadScanBtn, 0, 0)
        grid.addWidget(self.saveScanBtn, 0, 1)
        grid.addWidget(self.scanRadio, 0, 2)
        grid.addWidget(self.contLaserPulsesRadio, 0, 3)
        grid.addWidget(self.scanButton, 0, 4, 1, 2)
        grid.addWidget(self.continuousCheck, 0, 6)

        grid.addWidget(QtGui.QLabel('Size X (µm):'), 2, 0)
        grid.addWidget(self.sizeXPar, 2, 1)
        grid.addWidget(QtGui.QLabel('Size Y (µm):'), 3, 0)
        grid.addWidget(self.sizeYPar, 3, 1)
        grid.addWidget(QtGui.QLabel('Size Z (µm):'), 4, 0)
        grid.addWidget(self.sizeZPar, 4, 1)
        grid.addWidget(QtGui.QLabel('Step XY (µm):'), 2, 2)
        grid.addWidget(self.stepSizeXYPar, 2, 3)
        grid.addWidget(QtGui.QLabel('Number of pixels:'), 3, 2)  # Ger
        grid.addWidget(self.NumberpixPar, 3, 3)
        grid.addWidget(QtGui.QLabel('Step Z (µm):'), 4, 2)
        grid.addWidget(self.stepSizeZPar, 4, 3)

        grid.addWidget(QtGui.QLabel('Mode:'), 2, 4)
        grid.addWidget(self.scanMode, 2, 5)
        grid.addWidget(QtGui.QLabel('Primary dimension:'), 3, 4)
        grid.addWidget(self.primScanDim, 3, 5)
        grid.addWidget(QtGui.QLabel('Number of frames:'), 4, 4)
        grid.addWidget(self.nrFramesPar, 4, 5)
        grid.addWidget(self.previewButton, 2, 6, 3, 2)

        grid.addWidget(QtGui.QLabel('Dwell time (ms):'), 7, 0)
        grid.addWidget(self.seqTimePar, 7, 1)
        grid.addWidget(QtGui.QLabel('Total time (s):'), 7, 2)
        grid.addWidget(self.scanDurationLabel, 7, 3)
        grid.addWidget(QtGui.QLabel('Start (ms):'), 8, 1)
        grid.addWidget(QtGui.QLabel('End (ms):'), 8, 2)
        grid.addWidget(QtGui.QLabel('405:'), 9, 0)
        grid.addWidget(self.start405Par, 9, 1)
        grid.addWidget(self.end405Par, 9, 2)
        grid.addWidget(QtGui.QLabel('488:'), 10, 0)
        grid.addWidget(self.start488Par, 10, 1)
        grid.addWidget(self.end488Par, 10, 2)
        grid.addWidget(QtGui.QLabel('473:'), 11, 0)
        grid.addWidget(self.start473Par, 11, 1)
        grid.addWidget(self.end473Par, 11, 2)
        grid.addWidget(QtGui.QLabel('Camera:'), 12, 0)
        grid.addWidget(self.startCAMPar, 12, 1)
        grid.addWidget(self.endCAMPar, 12, 2)
        grid.addWidget(self.graph, 8, 3, 5, 5)

        grid.addWidget(self.multiScanWgt, 13, 0, 4, 9)

        grid.setColumnMinimumWidth(6, 160)
        grid.setRowMinimumHeight(1, 10)
        grid.setRowMinimumHeight(6, 10)
        grid.setRowMinimumHeight(13, 10)

    @property
    def scanOrNot(self):
        return self._scanOrNot

    @scanOrNot.setter
    def scanOrNot(self, value):
        self.enableScanPars(value)
        self.scanButton.setCheckable(not value)

    def enableScanPars(self, value):
        self.sizeXPar.setEnabled(value)
        self.sizeYPar.setEnabled(value)
        self.stepSizeXYPar.setEnabled(value)
        self.NumberpixPar.setEnabled(value)  # Ger
        self.scanMode.setEnabled(value)
        self.primScanDim.setEnabled(value)
        if value:
            self.scanButton.setText('Scan')
        else:
            self.scanButton.setText('Run')

    def setScanOrNot(self, value):
        self.scanOrNot = value

    def setScanMode(self, mode):
        self.stageScan.setScanMode(mode)
        self.scanParameterChanged('scanMode')

    def setPrimScanDim(self, dim):
        self.stageScan.setPrimScanDim(dim)
        self.scanParameterChanged('primScanDim')

    def scanParameterChanged(self, p):
        if p not in ('scanMode', 'primScanDim'):
            if p == 'seqTime':
                # To get in seconds
                self.scanParValues[p] = 0.001*float(self.scanPar[p].text())
            else:
                self.scanParValues[p] = float(self.scanPar[p].text())

        if p == 'seqTime':
            self.updateScan(self.allDevices)
            self.graph.update(self.allDevices)

        self.stageScan.updateFrames(self.scanParValues)
        self.nrFramesPar.setText(str(self.stageScan.frames))

        self.scanDuration = self.stageScan.frames*self.scanParValues['seqTime']
        self.scanDurationLabel.setText(str(np.round(self.scanDuration, 2)))

    def pxParameterChanged(self, p):
        self.pxParValues[p] = 0.001*float(self.pxParameters[p].text())
        device = [p[-3] + p[-2] + p[-1]]
        self.pxCycle.update(device, self.pxParValues, self.stageScan.seqSamps)
        self.graph.update(device)

    def previewScan(self):
        self.updateScan(self.allDevices)
        fig = plt.figure()
        ax0 = fig.add_subplot(211)
        ax0.plot(self.stageScan.sigDict['x'] * convFactors['x'])
        ax0.plot(self.stageScan.sigDict['y'] * convFactors['y'])
        ax0.plot(self.stageScan.sigDict['z'] * convFactors['z'])
        ax0.plot(self.pxCycle.sigDict['CAM'])
        ax0.grid()
        ax0.set_xlabel('sample')
        ax0.set_ylabel('position [um]')  # usa um y no µm ¿?
        ax1 = fig.add_subplot(212)
        ax1.plot(self.stageScan.sigDict['x'] * convFactors['x'],
                 self.stageScan.sigDict['y'] * convFactors['y'])
        mx = max(self.scanParValues['sizeX'], self.scanParValues['sizeY'])
        ax1.margins(0.1*mx)
        ax1.axis('scaled')
        ax1.set_xlabel("x axis [µm]")
        ax1.set_ylabel("y axis [µm]")

        plt.show()

    def scanOrAbort(self):
        if not self.scanning:
            main = self.main
            lasers = main.laserWidgets
            if (lasers.DigCtrl.DigitalControlButton.isChecked() and
               main.trigsourceparam.value() == 'External "frame-trigger"'):
                self.prepAndRun()
            else:
                self.digModWarning.exec_()
        else:
            self.scanner.abort()

    def prepAndRun(self, continuous=False):
        ''' Only called if scanner is not running (See scanOrAbort function).
        '''
        if self.scanRadio.isChecked():
            self.stageScan.update(self.scanParValues)
            self.scanButton.setText('Wait')
            if not(continuous):
                self.main.piezoWidget.resetChannels(
                    self.stageScan.activeChannels[self.stageScan.scanMode])
            self.scanner = Otroscanner(
               self.nidaq, self.stageScan, self.pxCycle, self, continuous)
            self.scanner.finalizeDone.connect(self.finalizeDone)
            self.scanner.scanDone.connect(self.scanDone)
            self.scanning = True
            if self.focusLocked:
                self.focusWgt.unlockFocus()

            self.main.lvworkers[0].startRecording()

            self.scanner.runScan()

        elif self.scanButton.isChecked():
            self.lasercycle = LaserCycle(self.nidaq, self.pxCycle)
            self.scanButton.setText('Stop')
            self.lasercycle.run()

        else:
            self.lasercycle.stop()
            self.scanButton.setText('Run')
            del self.lasercycle

    def scanDone(self):
        self.scanButton.setEnabled(False)

        if not self.scanner.aborted:
            time.sleep(0.1)

            self.main.lvworkers[0].stopRecording()

            # Building scanning image in 2D or 3D
            if self.multiScanWgt.makeImgBox.isChecked():

                # Get data
                data = self.main.lvworkers[0].fRecorded

                # Send data to MultipleScanWidget and analyze it
                if self.stageScan.scanMode == 'step scan':
                    datashape = (len(data), *self.main.shapes[0][::-1])
                    data = np.reshape(data, datashape)
                    self.multiScanWgt.worker.set_images(data)
                    self.multiScanWgt.worker.find_fp()
                    self.multiScanWgt.worker.analyze()

                elif self.stageScan.scanMode == 'otro scan':
                    vScan = self.stageScan.scans['otro scan']
                    datashape = (vScan.stepsZ, -1, *self.main.shapes[0][::-1])
                    data = np.reshape(data, datashape)
                    stk = np.zeros((vScan.stepsZ, vScan.stepsY, vScan.stepsX))
                    i = 0
                    for image in data:
                        self.multiScanWgt.worker.set_images(image)
                        self.multiScanWgt.worker.find_fp()
                        self.multiScanWgt.worker.analyze()
                        stk[i] = self.multiScanWgt.worker.illumImgs[0]
                        i += 1

                    xAx = np.arange(0, vScan.stepsZ*vScan.stepSizeZ,
                                    vScan.stepSizeZ)
                    self.multiScanWgt.illumWgt3D.setImage(stk, xvals=xAx)

    def finalizeDone(self):
        if (not self.continuousCheck.isChecked()) or self.scanner.aborted:
            self.scanButton.setText('Confoscanl')
            self.scanButton.setEnabled(True)
            del self.scanner
            self.scanning = False
            if self.focusLocked:
                self.focusWgt.lockFocus()
            self.main.piezoWidget.resetChannels(
                self.stageScan.activeChannels[self.stageScan.scanMode])
        elif self.continuousCheck.isChecked():
            self.scanButton.setEnabled(True)
            self.prepAndRun(True)
        else:
            self.scanButton.setEnabled(True)
            self.prepAndRun()

    def updateScan(self, devices):
        self.stageScan.update(self.scanParValues)
        self.pxCycle.update(devices, self.pxParValues, self.stageScan.seqSamps)

    def closeEvent(self, *args, **kwargs):
        try:
            self.scanner.waiter.terminate()
        except BaseException:
            pass

# ---Sigue lo agregado----------------------------------------


""" comente los lvworkers para no tener que prender el live"""


class Otroscanner(QtCore.QObject):
    """This class plays the role of interface between the software and the
    hardware. It writes the different signals to the electronic cards and
    manages the timing of a scan.

    :param nidaqmx.Device device: NiDaq card
    :param StageScan stageScan: object containing the analog signals to drive
    the stage
    :param PixelCycle pxCycle: object containing the digital signals to
    drive the lasers at each pixel acquisition
    :param ScanWidget main: main scan GUI."""
    """yo trato de armar un escaneo punto por punto."""

    scanDone = QtCore.pyqtSignal()
    finalizeDone = QtCore.pyqtSignal()

    def __init__(self, device, stageScan, pxCycle, main, continuous=False,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.nidaq = device
        self.stageScan = stageScan
        self.pxCycle = pxCycle
        self.continuous = continuous

        self.sampsInScan = len(self.stageScan.sigDict['x'])
        self.main = main

        self.aotask = nidaqmx.Task('aotask')
        self.dotask = nidaqmx.Task('dotask')
        self.aitask = nidaqmx.Task('aitask')  # Ger
        self.ditask = nidaqmx.Task('ditask')  # Ger

        self.waiter = WaitThread(self.aotask)

        self.scanTimeW = QtGui.QMessageBox()
        self.scanTimeW.setInformativeText("Are you sure you want to continue?")
        self.scanTimeW.setStandardButtons(QtGui.QMessageBox.Yes |
                                          QtGui.QMessageBox.No)

        self.channelOrder = main.channelOrder
#        self.channelOrder = ['x', 'y', 'z']
        self.aborted = False

        self.focusWgt = self.main.focusWgt

        AOchans = [0, 1, 2]
        # Following loop creates the voltage channels
        for n in range(len(AOchans)):
            self.aotask.ao_channels.add_ao_voltage_chan(
                physical_channel='Dev1/ao%s' % AOchans[n],
                name_to_assign_to_channel='chan_%s' % self.channelOrder[n],
                min_val=minVolt[self.channelOrder[n]],
                max_val=maxVolt[self.channelOrder[n]])

        self.fullAOsig = np.array(
            [self.stageScan.sigDict[self.channelOrder[i]]
             for i in range(len(AOchans))])

        # Same as above but for the digital signals/devices
        devs = list(self.pxCycle.sigDict.keys())
        DOchans = range(0, 4)
        for d in DOchans:
            chanstring = 'Dev1/port0/line%s' % d
            self.dotask.do_channels.add_do_chan(
                lines=chanstring, name_to_assign_to_lines='chan%s' % devs[d],
                line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)

        self.fullDOsig = np.array(
            [self.pxCycle.sigDict[devs[i]] for i in DOchans])
#        self.dotask.do_channels.add_do_chan(  # se ocuparia del shutter
#            lines="Dev1/port0/line6", name_to_assign_to_lines='chan6',
#            line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)  # Ger
#        # Tengo que hacer que dotask accione el/los shutters.

        self.ditask.di_channels.add_di_chan(
            lines="Dev1/port0/line7", name_to_assign_to_lines='chan5',
            line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)  # Ger

        self.aitask.ai_channels.add_ai_voltage_chan(
            physical_channel="Dev1/ai7:6",
            min_val=-5, max_val=5)  # Ger

    def runScan(self):
        self.aborted = False

        if self.main.scanMode.currentText() == "step scan":
            self.StepScan()
#            LuchoScanWidget(self)
        if self.main.scanMode.currentText() == "viejo scan":
            self.OtroScan()
        if self.main.scanMode.currentText() == "otro scan":
            self.ViejoScan()

# --- StepScan---

    def StepScan(self):  # si step
        print("step:\n va x, sube y; vuelve x, sube y. itera")

        tpix = self.main.scanParValues['seqTime']
        tapd = tpix  # 10**-5
        apdrate = 9*10**6  # Lo que de el apd (o la entrada digital)
        Napd = int(np.round(apdrate * tapd))
#        self.sampleRate = 10**5
#        self.seqSamps = int(np.round(self.main.sampleRate*tpix))
        self.seqSamps = int(self.main.scanParValues['Number of pixels'])
        self.sampleRate = self.seqSamps / tpix  # No lo uso en ningun lado

        self.ditask.timing.cfg_samp_clk_timing(
          rate=apdrate, sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
          samps_per_chan=Napd)

        startX = startY = 0  # Buscar que tome el parametro del Positioner
        stepSize = self.main.scanParValues['stepSizeXY']
        sizeX = self.main.scanParValues['sizeX']
        sizeY = self.main.scanParValues['sizeY']
        stepsY = int(np.ceil(sizeY / stepSize))
        aidata = np.zeros((self.seqSamps, stepsY, 2))
        self.cuentas = np.zeros((stepsY, self.seqSamps))
        self.stepsX = int(np.ceil(sizeX / stepSize))
        self.stepsY = int(np.ceil(sizeY / stepSize))
        self.stepsZ = 1

        Samps = int(self.seqSamps / 2)
        idax = makeRamp(startX, sizeX, Samps)
        vueltax = makeRamp(sizeX, startX, Samps)
        primSig = np.concatenate((idax, vueltax))
        self.barridox = primSig / convFactors['x']
        iday = np.ones(Samps)*startY
        ida2y = np.ones(Samps) * (startY + stepSize)
        secSig = np.concatenate((iday, ida2y))
        self.barridoy = secSig / convFactors['y']
        self.barridoz = np.zeros(len(self.barridox))
        self.ejex = np.linspace(startX, sizeX, self.seqSamps)
        self.ejey = np.linspace(startY, sizeY, stepsY)

        for j in range(stepsY):
            tic = time.time()
            for i in range(self.seqSamps):
                self.aotask.write(
                    [self.barridox[i],
                     self.barridoy[i] + (2*stepSize*j) / convFactors['y'],
                     self.barridoz[i]], auto_start=True)

                APD = self.ditask.read(Napd)
                aidata[i, j, :] = self.aitask.read()
                aux = 0
                for c in range(Napd-1):
                    if APD[c] < APD[c+1]:
                        aux = aux + 1
                self.cuentas[j, i] = aux + 5*i+j  # solo para probar el grafico

            toc = time.time()
            print(toc-tic, "segundos")

        self.done()

        print("saque el plot viejo, trato de poner el dinamico")
        print("pero no me salio :(")
        print(self.seqSamps, "seqSamps\n", stepsY, "stepsY\n",
              self.sampleRate, "sampleRate")

# --PLOTS----------------------------------------------------------------
#        import matplotlib.pyplot as plt  # Ger
##        self.ConfocalWidget.updateScan(self.allDevices)
##        auxi = np.linspace(0, self.seqSamps, self.seqSamps)
#        data7 = aidata[:, 0, 0]
#        data6 = aidata[:, 0, 1]
#        for k in range(1, stepsY):  # self.seqSamps):
#            data7 = np.append(data7, aidata[:, k, 0], axis=0)
#            data6 = np.append(data6, aidata[:, k, 1], axis=0)
#        fig = plt.figure()
#        ax0 = fig.add_subplot(111)
#        ax0.plot(self.barridox, '-b', label="x")
#        ax0.plot(self.barridoy, '-g', label="y")
##        ax0.plot(self.stageScan.sigDict['z'], label="z")
#        ax0.plot(data7, '.--y', label="data7 ")
#        ax0.plot(data6, '.--r', label="data6 ")
#        ax0.plot(aidata[:, 0, 0], '.--k', label="data leida \" dev/ai7 \" ")
#        ax0.plot(aidata[:, 0, 1], '.--m', label="data leida \" dev/ai6 \" ")
##        ax0.plot(aidata[:, 1], '.-m', label="data leida \" dev/ai6 \" ")
##        ax0.plot(signal, '-c')
##        ax0.plot(didata, '.-c', label="data leida del digital ")
#        ax0.legend(bbox_to_anchor=(1.15, 1.15))
##        plt.axis([0, 40, -0.1, 1.1])
#        print(self.pxCycle.sampleRate, "sampleRate\n",
#              self.sampsInScan, "sampsInScan\n", Napd, "Napd\n",
#              self.seqSamps, "self.seqSamps")
##        ax0.plot(self.pxCycle.sigDict['CAM'], 'r')
#        ax0.grid()
#        ax0.set_xlabel('sample')
#        ax0.set_ylabel('Voltage (¿V?)')
#
#        plt.show()

        self.X, self.Y = np.meshgrid(self.ejex, self.ejey)
#        X, Y = np.meshgrid(self.stageScan.sigDict['x'], self.stageScan.sigDict['y'])

        fig, ax = plt.subplots()
        p = ax.pcolor(self.X, self.Y, self.cuentas, cmap=plt.cm.jet)  # , vmin=0)
        cb = fig.colorbar(p)
        ax.set_xlabel('x [um]')
        ax.set_ylabel('y [um]')
        plt.show()
# -- aaaaaaaaaaaaaaaaaaaaa-----------

# --- OtroScan-----------------------------------------------

    def OtroScan(self):  # si viejo
        print("viejo:\n va y vuelve x, sube y. itera")

        tpix = self.main.scanParValues['seqTime']
        apdrate = self.main.sampleRate  # 1000*10
        Napd = 10**3  # int(np.round(tpix*apdrate))
#        self.sampleRate = 10**5
        self.seqSamps = int(np.round(self.main.sampleRate*tpix))
        self.ditask.timing.cfg_samp_clk_timing(
          rate=apdrate, sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
          samps_per_chan=Napd)  # Ger

        stepSize = self.main.scanParValues['stepSizeXY']
        sizeY = self.main.scanParValues['sizeY']
        stepsY = int(np.ceil(sizeY / stepSize))
        aidata = np.zeros((self.seqSamps, stepsY, 2))
        cuentas = np.zeros((self.seqSamps, stepsY))

#        signal = np.zeros(Napd, dtype='bool')
#        for p in range(Napd):
#            r = np.random.rand(1)[0]
#            if 0.5 < r:
#                signal[p] = True
#        self.dotask.timing.cfg_samp_clk_timing(
#              rate=1000*100, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS)
#        #      samps_per_chan=Napd)
#        self.dotask.write(signal, auto_start=True)

        self.seqSamps = int(np.round(self.main.sampleRate*tpix))
        x0 = y0 = 0
        sizeX = self.main.scanParValues['sizeX']
        barridoLTR = np.linspace(x0, sizeX, int(np.round(self.seqSamps/2)))
        barridoRTL = np.linspace(sizeX, x0, int(np.round(self.seqSamps/2)))
        barridox = np.append(barridoLTR, barridoRTL, axis=0) / convFactors['x']
        barridoy = np.ones(self.seqSamps) * y0

        for j in range(stepsY):
            tic = time.time()
            for i in range(self.seqSamps):
                self.aotask.write(
                    [barridox[i],
                     barridoy[i] + (stepSize*j) / convFactors['y'],
                     0], auto_start=True)
#                self.dotask.write(signal, auto_start=True, timeout=10.0)
                APD = self.ditask.read(Napd)
                aidata[i, j, :] = self.aitask.read()
                aux = 0
                for c in range(Napd-1):
                    if APD[c] < APD[c+1]:
                        aux = aux + 1
                cuentas[i, j] = aux
            toc = time.time()
            print(toc-tic, "segundos")

        try:
            self.waiter.waitdoneSignal.disconnect(self.done)
        except TypeError:
            # This happens when the scan is aborted after the warning
            pass
        self.waiter.waitdoneSignal.connect(self.finalize)

#        self.aotask.start()
#        self.waiter.start()
        self.done()
# --PLOTS----------------------------------------------------------------
#        self.ConfocalWidget.updateScan(self.allDevices)
#        auxi = np.linspace(0, self.seqSamps, self.seqSamps)
        data7 = aidata[:, 0, 0]
        data6 = aidata[:, 0, 1]
        for k in range(1, stepsY):  # self.seqSamps):
            data7 = np.append(data7, aidata[:, k, 0], axis=0)
            data6 = np.append(data6, aidata[:, k, 1], axis=0)
        fig = plt.figure()
        ax0 = fig.add_subplot(111)
        ax0.plot(barridox, '-b', label="x")
        ax0.plot(barridoy, '-g', label="y")
#        ax0.plot(self.stageScan.sigDict['z'], label="z")
        ax0.plot(data7, '.--y', label="data7 ")
        ax0.plot(data6, '.--r', label="data6 ")
        ax0.plot(aidata[:, 0, 0], '.--k', label="data leida \" dev/ai7 \" ")
        ax0.plot(aidata[:, 0, 1], '.--m', label="data leida \" dev/ai6 \" ")
#        ax0.plot(aidata[:, 1], '.-m', label="data leida \" dev/ai6 \" ")
#        ax0.plot(signal, '-c')
#        ax0.plot(didata, '.-c', label="data leida del digital ")
        ax0.legend(bbox_to_anchor=(1.15, 1.15))
#        plt.axis([0, 40, -0.1, 1.1])
        print(self.pxCycle.sampleRate, "sampleRate\n",
              self.sampsInScan, "sampsInScan\n", Napd, "Napd")
#        ax0.plot(self.pxCycle.sigDict['CAM'], 'r')
        ax0.grid()
        ax0.set_xlabel('sample')
        ax0.set_ylabel('Voltage (¿V?)')

        plt.show()

#        X, Y = np.meshgrid(barridox, barridoy)
#        X, Y = np.meshgrid(self.stageScan.sigDict['x'], self.stageScan.sigDict['y'])
#
#        fig, ax = plt.subplots()
#        p = ax.pcolor(X, Y, cuentas, cmap=plt.cm.jet)  # , vmin=0)
#        cb = fig.colorbar(p)
#        ax.set_xlabel('x [um]')
#        ax.set_ylabel('y [um]')
#        plt.show()
# -- aaaaaaaaaaaaaaaaaaaaa-----------

# --- ViejoScan---
    def ViejoScan(self):  # si otro
        print("otro:\n tendria que hacer un grafico con el barrido viejo")

#        AOchans = [0, 1, 2]
#        self.fullAOsig = np.array(
#            [self.stageScan.sigDict[self.channelOrder[i]]
#             for i in range(len(AOchans))])

#        devs = list(self.pxCycle.sigDict.keys())
#        DOchans = range(0, 4)
#        self.fullDOsig = np.array(
#            [self.pxCycle.sigDict[devs[i]] for i in DOchans])

        """When doing unidirectional scan, the time needed for the stage to
        move back to the initial x needs to be filled with zeros/False.
        This time is now set to the time spanned by 1 sequence.
        Therefore, the digital signal is assambled as the repetition of the
        sequence for the whole scan in one row and then append zeros for 1
        sequence time. THIS IS NOW INCOMPATIBLE WITH VOLUMETRIC SCAN, maybe."""

        if self.stageScan.primScanDim == 'x':
            primSteps = self.stageScan.scans[self.stageScan.scanMode].stepsX
        else:
            primSteps = self.stageScan.scans[self.stageScan.scanMode].stepsY
        # Signal for a single line
        lineSig = np.tile(self.fullDOsig, primSteps)
        emptySig = np.zeros((4, int(self.stageScan.seqSamps)), dtype=bool)
        self.fullDOsig = np.concatenate((emptySig, lineSig, emptySig), axis=1)

        self.aotask.timing.cfg_samp_clk_timing(
            rate=self.stageScan.sampleRate,
            source=r'100kHzTimeBase',
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=self.sampsInScan)

        self.dotask.timing.cfg_samp_clk_timing(
            rate=self.pxCycle.sampleRate,
#            source=r'ao/SampleClock',
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=self.sampsInScan)

        self.aotask.write(self.fullAOsig, auto_start=False)
        self.dotask.write(self.fullDOsig, auto_start=False)

        self.aitask.timing.cfg_samp_clk_timing(
                rate=self.stageScan.sampleRate,
                source=r'100kHzTimeBase',
                sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                samps_per_chan=self.sampsInScan)  # Ger

#        self.ditask.timing.cfg_samp_clk_timing(
#            rate=self.pxCycle.sampleRate,
##            source=r'ao/SampleClock',
#            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
#            samps_per_chan=self.sampsInScan)  # Ger

        try:
            self.waiter.waitdoneSignal.disconnect(self.done)
        except TypeError:
            # This happens when the scan is aborted after the warning
            pass
        self.waiter.waitdoneSignal.connect(self.finalize)

        self.dotask.start()
        self.aotask.start()
        self.waiter.start()

        aidata = self.aitask.read(self.sampsInScan)
#        didata = self.ditask.read(self.sampsInScan)

        self.aitask.wait_until_done()
        self.dotask.wait_until_done()

# --aaa---------------------------------------------
#        self.ConfocalWidget.updateScan(self.allDevices)
        fig = plt.figure()
        ax0 = fig.add_subplot(111)
        ax0.plot(self.stageScan.sigDict['x'], '.-', label="x")
        # * convFactors['x'], label="x")
        ax0.plot(self.stageScan.sigDict['y'], '.-', label="y")
        # * convFactors['y'], label="y")
        ax0.plot(self.stageScan.sigDict['z'] * convFactors['z'], label="z")
        ax0.plot(aidata[0], '.-k', label="data leida \" dev/ai7 \" ")
        ax0.plot(aidata[1], '.-m', label="data leida \" dev/ai6 \" ")
#        ax0.plot(signal)
#        ax0.plot(didata, '.-c', label="data leida del digital ")
        ax0.legend(bbox_to_anchor=(1.15, 1.2))
#        plt.axis([0, 40, -0.1, 1.1])
        print(self.pxCycle.sampleRate, "sampleRate",
              self.sampsInScan, "sampsInScan")
#        ax0.plot(self.pxCycle.sigDict['CAM'], 'r')
        ax0.grid()
        ax0.set_xlabel('sample')
        ax0.set_ylabel('Voltage (V?)')  # ('position [µm]')  # Ger- cambie a µm

#        ax1 = fig.add_subplot(212)
#        ax1.plot(self.stageScan.sigDict['x'] * convFactors['x'],
#                 self.stageScan.sigDict['y'] * convFactors['y'])
#        mx = max(self.scanParValues['sizeX'], self.scanParValues['sizeY'])
#        ax1.margins(0.1*mx)
#        ax1.axis('scaled')
#        ax1.set_xlabel("x axis [µm]")
#        ax1.set_ylabel("y axis [µm]")

        plt.show()
# --aaa----------------------------------------------

    def abort(self):
        self.aborted = True
        self.waiter.stop()
        self.aotask.stop()
        self.dotask.stop()
        self.aitask.stop()  # Ger
        self.ditask.stop()  # Ger
        self.finalize()

    def finalize(self):
        self.scanDone.emit()
        # Apparently important, otherwise finalize is called again when next
        # waiting finishes.
        try:
            self.waiter.waitdoneSignal.disconnect(self.finalize)
        except TypeError:
            # This happens when the scan is aborted after the warning
            pass
        self.waiter.waitdoneSignal.connect(self.done)

        # Following code should correct channels mentioned in Buglist. Not
        # correct though, assumes channels are 0, 1 and 2.
        # TODO: Test abort (task function)
        writtenSamps = int(np.round(self.aotask.out_stream.curr_write_pos))
        chans = [0, 1, 2]
        dim = [self.channelOrder[i] for i in chans]
        finalSamps = [
            self.stageScan.sigDict[dim[i]][writtenSamps - 1] for i in chans]
        seqTime = self.main.scanParValues['seqTime']
        returnRamps = np.array(
            [makeRamp(finalSamps[i], 0, int(self.stageScan.sampleRate*seqTime))
             for i in chans])

        self.aotask.stop()
        self.aotask.timing.cfg_samp_clk_timing(
            rate=self.stageScan.sampleRate,
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=self.stageScan.sampleRate)

        self.aotask.write(returnRamps, auto_start=True)
        self.waiter.start()

    def done(self):
        self.aotask.stop()
        self.aotask.close()
        self.dotask.stop()
        self.dotask.close()
        self.aitask.stop()  # Ger
        self.aitask.close()  # Ger
        self.ditask.stop()  # Ger
        self.ditask.close()  # Ger
        self.nidaq.reset_device()
        self.finalizeDone.emit()

# ---Termina lo Agregado por german-----------------------------


class ScanWidget(QtGui.QMainWindow):
    ''' This class is intended as a widget in the bigger GUI, Thus all the
    commented parameters etc. It contain an instance of stageScan and
    pixel_scan which in turn harbour the analog and digital signals
    respectively.
    The function run starts the communication with the Nidaq through the
    Scanner object. This object was initially written as a QThread object but
    is not right now.
    As seen in the commened lines of run() I also tried running in a QThread
    created in run().
    The rest of the functions contain mostly GUI related code.'''
    def __init__(self, device, main, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.scanInLiveviewWar = QtGui.QMessageBox()
        self.scanInLiveviewWar.setInformativeText(
            "You need to be in liveview to scan")

        self.digModWarning = QtGui.QMessageBox()
        self.digModWarning.setInformativeText(
            "You need to be in digital laser modulation and external "
            "frame-trigger acquisition mode")

        self.nidaq = device
        self.main = main
        self.focusWgt = main.FocusLockWidget
        self.focusLocked = self.focusWgt.locked

        # The port order in the NIDAQ follows this same order.
        # We chose to follow the temporal sequence order
        self.allDevices = ['405', '488', '473', 'CAM']
        self.channelOrder = ['x', 'y', 'z']

        self.saveScanBtn = QtGui.QPushButton('Save Scan')

        self.scanDir = os.path.join(self.main.controlFolder, 'scans')

        if not os.path.exists(self.scanDir):
            os.makedirs(self.scanDir)

        def saveScanFcn(): return saveScan(self)
        self.saveScanBtn.clicked.connect(saveScanFcn)
        self.loadScanBtn = QtGui.QPushButton('Load Scan')

        def loadScanFcn(): return loadScan(self)
        self.loadScanBtn.clicked.connect(loadScanFcn)

        self.sampleRateEdit = QtGui.QLineEdit()

        self.sizeXPar = QtGui.QLineEdit('2')
        self.sizeXPar.textChanged.connect(
            lambda: self.scanParameterChanged('sizeX'))
        self.sizeYPar = QtGui.QLineEdit('2')
        self.sizeYPar.textChanged.connect(
            lambda: self.scanParameterChanged('sizeY'))
        self.sizeZPar = QtGui.QLineEdit('10')
        self.sizeZPar.textChanged.connect(
            lambda: self.scanParameterChanged('sizeZ'))
        self.seqTimePar = QtGui.QLineEdit('10')     # ms
        self.seqTimePar.textChanged.connect(
            lambda: self.scanParameterChanged('seqTime'))
        self.nrFramesPar = QtGui.QLabel()
        self.scanDuration = 0
        self.scanDurationLabel = QtGui.QLabel(str(self.scanDuration))
        self.stepSizeXYPar = QtGui.QLineEdit('0.1')
        self.stepSizeXYPar.textChanged.connect(
            lambda: self.scanParameterChanged('stepSizeXY'))
        self.stepSizeZPar = QtGui.QLineEdit('1')
        self.stepSizeZPar.textChanged.connect(
            lambda: self.scanParameterChanged('stepSizeZ'))
        self.sampleRate = 100000

        self.scanMode = QtGui.QComboBox()
        self.scanModes = ['FOV scan', 'VOL scan', 'Line scan']
        self.scanMode.addItems(self.scanModes)
        self.scanMode.currentIndexChanged.connect(
            lambda: self.setScanMode(self.scanMode.currentText()))

        self.primScanDim = QtGui.QComboBox()
        self.scanDims = ['x', 'y']
        self.primScanDim.addItems(self.scanDims)
        self.primScanDim.currentIndexChanged.connect(
            lambda: self.setPrimScanDim(self.primScanDim.currentText()))

        self.scanPar = {'sizeX': self.sizeXPar,
                        'sizeY': self.sizeYPar,
                        'sizeZ': self.sizeZPar,
                        'seqTime': self.seqTimePar,
                        'stepSizeXY': self.stepSizeXYPar,
                        'stepSizeZ': self.stepSizeZPar}

        self.scanParValues = {'sizeX': float(self.sizeXPar.text()),
                              'sizeY': float(self.sizeYPar.text()),
                              'sizeZ': float(self.sizeZPar.text()),
                              'seqTime': 0.001*float(self.seqTimePar.text()),
                              'stepSizeXY': float(self.stepSizeXYPar.text()),
                              'stepSizeZ': float(self.stepSizeZPar.text())}

        self.start405Par = QtGui.QLineEdit('0')
        self.start405Par.textChanged.connect(
            lambda: self.pxParameterChanged('start405'))
        self.start488Par = QtGui.QLineEdit('0')
        self.start488Par.textChanged.connect(
            lambda: self.pxParameterChanged('start488'))
        self.start473Par = QtGui.QLineEdit('0')
        self.start473Par.textChanged.connect(
            lambda: self.pxParameterChanged('start473'))
        self.startCAMPar = QtGui.QLineEdit('0')
        self.startCAMPar.textChanged.connect(
            lambda: self.pxParameterChanged('startCAM'))

        self.end405Par = QtGui.QLineEdit('0')
        self.end405Par.textChanged.connect(
            lambda: self.pxParameterChanged('end405'))
        self.end488Par = QtGui.QLineEdit('0')
        self.end488Par.textChanged.connect(
            lambda: self.pxParameterChanged('end488'))
        self.end473Par = QtGui.QLineEdit('0')
        self.end473Par.textChanged.connect(
            lambda: self.pxParameterChanged('end473'))
        self.endCAMPar = QtGui.QLineEdit('0')
        self.endCAMPar.textChanged.connect(
            lambda: self.pxParameterChanged('endCAM'))

        self.pxParameters = {'start405': self.start405Par,
                             'start488': self.start488Par,
                             'start473': self.start473Par,
                             'startCAM': self.startCAMPar,
                             'end405': self.end405Par,
                             'end488': self.end488Par,
                             'end473': self.end473Par,
                             'endCAM': self.endCAMPar}

        self.pxParValues = {'start405': 0.001*float(self.start405Par.text()),
                            'start488': 0.001*float(self.start488Par.text()),
                            'start473': 0.001*float(self.start473Par.text()),
                            'startCAM': 0.001*float(self.startCAMPar.text()),
                            'end405': 0.001*float(self.end405Par.text()),
                            'end488': 0.001*float(self.end488Par.text()),
                            'end473': 0.001*float(self.end473Par.text()),
                            'endCAM': 0.001*float(self.endCAMPar.text())}

        self.stageScan = StageScan(self.sampleRate)
        self.pxCycle = PixelCycle(self.sampleRate)
        self.graph = GraphFrame(self.pxCycle)
        self.graph.plot.getAxis('bottom').setScale(1000/self.sampleRate)
        self.graph.setFixedHeight(100)
        self.updateScan(self.allDevices)
        self.scanParameterChanged('seqTime')

        self.multiScanWgt = MultipleScanWidget(self)

        self.scanRadio = QtGui.QRadioButton('Scan')
        self.scanRadio.clicked.connect(lambda: self.setScanOrNot(True))
        self.scanRadio.setChecked(True)
        self.contLaserPulsesRadio = QtGui.QRadioButton('Cont. Laser Pulses')
        self.contLaserPulsesRadio.clicked.connect(
            lambda: self.setScanOrNot(False))

        self.scanButton = QtGui.QPushButton('Scan')
        self.scanning = False
        self.scanButton.clicked.connect(self.scanOrAbort)
        self.previewButton = QtGui.QPushButton('Plot scan path')
        self.previewButton.setSizePolicy(QtGui.QSizePolicy.Preferred,
                                         QtGui.QSizePolicy.Expanding)
        self.previewButton.clicked.connect(self.previewScan)
        self.continuousCheck = QtGui.QCheckBox('Repeat')

        self.cwidget = QtGui.QWidget()
        self.setCentralWidget(self.cwidget)
        grid = QtGui.QGridLayout()
        self.cwidget.setLayout(grid)

        grid.addWidget(self.loadScanBtn, 0, 0)
        grid.addWidget(self.saveScanBtn, 0, 1)
        grid.addWidget(self.scanRadio, 0, 2)
        grid.addWidget(self.contLaserPulsesRadio, 0, 3)
        grid.addWidget(self.scanButton, 0, 4, 1, 2)
        grid.addWidget(self.continuousCheck, 0, 6)

        grid.addWidget(QtGui.QLabel('Size X (µm):'), 2, 0)
        grid.addWidget(self.sizeXPar, 2, 1)
        grid.addWidget(QtGui.QLabel('Size Y (µm):'), 3, 0)
        grid.addWidget(self.sizeYPar, 3, 1)
        grid.addWidget(QtGui.QLabel('Size Z (µm):'), 4, 0)
        grid.addWidget(self.sizeZPar, 4, 1)
        grid.addWidget(QtGui.QLabel('Step XY (µm):'), 2, 2)
        grid.addWidget(self.stepSizeXYPar, 2, 3)
        grid.addWidget(QtGui.QLabel('Step Z (µm):'), 4, 2)
        grid.addWidget(self.stepSizeZPar, 4, 3)

        grid.addWidget(QtGui.QLabel('Mode:'), 2, 4)
        grid.addWidget(self.scanMode, 2, 5)
        grid.addWidget(QtGui.QLabel('Primary dimension:'), 3, 4)
        grid.addWidget(self.primScanDim, 3, 5)
        grid.addWidget(QtGui.QLabel('Number of frames:'), 4, 4)
        grid.addWidget(self.nrFramesPar, 4, 5)
        grid.addWidget(self.previewButton, 2, 6, 3, 2)

        grid.addWidget(QtGui.QLabel('Dwell time (ms):'), 7, 0)
        grid.addWidget(self.seqTimePar, 7, 1)
        grid.addWidget(QtGui.QLabel('Total time (s):'), 7, 2)
        grid.addWidget(self.scanDurationLabel, 7, 3)
        grid.addWidget(QtGui.QLabel('Start (ms):'), 8, 1)
        grid.addWidget(QtGui.QLabel('End (ms):'), 8, 2)
        grid.addWidget(QtGui.QLabel('405:'), 9, 0)
        grid.addWidget(self.start405Par, 9, 1)
        grid.addWidget(self.end405Par, 9, 2)
        grid.addWidget(QtGui.QLabel('488:'), 10, 0)
        grid.addWidget(self.start488Par, 10, 1)
        grid.addWidget(self.end488Par, 10, 2)
        grid.addWidget(QtGui.QLabel('473:'), 11, 0)
        grid.addWidget(self.start473Par, 11, 1)
        grid.addWidget(self.end473Par, 11, 2)
        grid.addWidget(QtGui.QLabel('Camera:'), 12, 0)
        grid.addWidget(self.startCAMPar, 12, 1)
        grid.addWidget(self.endCAMPar, 12, 2)
        grid.addWidget(self.graph, 8, 3, 5, 5)

        grid.addWidget(self.multiScanWgt, 13, 0, 4, 9)

        grid.setColumnMinimumWidth(6, 160)
        grid.setRowMinimumHeight(1, 10)
        grid.setRowMinimumHeight(6, 10)
        grid.setRowMinimumHeight(13, 10)

    @property
    def scanOrNot(self):
        return self._scanOrNot

    @scanOrNot.setter
    def scanOrNot(self, value):
        self.enableScanPars(value)
        self.scanButton.setCheckable(not value)

    def enableScanPars(self, value):
        self.sizeXPar.setEnabled(value)
        self.sizeYPar.setEnabled(value)
        self.stepSizeXYPar.setEnabled(value)
        self.scanMode.setEnabled(value)
        self.primScanDim.setEnabled(value)
        if value:
            self.scanButton.setText('Scan')
        else:
            self.scanButton.setText('Run')

    def setScanOrNot(self, value):
        self.scanOrNot = value

    def setScanMode(self, mode):
        self.stageScan.setScanMode(mode)
        self.scanParameterChanged('scanMode')

    def setPrimScanDim(self, dim):
        self.stageScan.setPrimScanDim(dim)
        self.scanParameterChanged('primScanDim')

    def scanParameterChanged(self, p):
        if p not in ('scanMode', 'primScanDim'):
            if p == 'seqTime':
                # To get in seconds
                self.scanParValues[p] = 0.001*float(self.scanPar[p].text())
            else:
                self.scanParValues[p] = float(self.scanPar[p].text())

        if p == 'seqTime':
            self.updateScan(self.allDevices)
            self.graph.update(self.allDevices)

        self.stageScan.updateFrames(self.scanParValues)
        self.nrFramesPar.setText(str(self.stageScan.frames))

        self.scanDuration = self.stageScan.frames*self.scanParValues['seqTime']
        self.scanDurationLabel.setText(str(np.round(self.scanDuration, 2)))

    def pxParameterChanged(self, p):
        self.pxParValues[p] = 0.001*float(self.pxParameters[p].text())
        device = [p[-3] + p[-2] + p[-1]]
        self.pxCycle.update(device, self.pxParValues, self.stageScan.seqSamps)
        self.graph.update(device)

    def previewScan(self):
        self.updateScan(self.allDevices)
        fig = plt.figure()
        ax0 = fig.add_subplot(211)
        ax0.plot(self.stageScan.sigDict['x'] * convFactors['x'])
        ax0.plot(self.stageScan.sigDict['y'] * convFactors['y'])
        ax0.plot(self.stageScan.sigDict['z'] * convFactors['z'])
        ax0.plot(self.pxCycle.sigDict['CAM'])
        ax0.grid()
        ax0.set_xlabel('sample')
        ax0.set_ylabel('position [um]')  # Ger- usa um y no µm solo aca
        ax1 = fig.add_subplot(212)
        ax1.plot(self.stageScan.sigDict['x'] * convFactors['x'],
                 self.stageScan.sigDict['y'] * convFactors['y'])
        mx = max(self.scanParValues['sizeX'], self.scanParValues['sizeY'])
        ax1.margins(0.1*mx)
        ax1.axis('scaled')
        ax1.set_xlabel("x axis [µm]")
        ax1.set_ylabel("y axis [µm]")

        plt.show()

    def scanOrAbort(self):
        if not self.scanning:
            main = self.main
            lasers = main.laserWidgets
            if (lasers.DigCtrl.DigitalControlButton.isChecked() and
               main.trigsourceparam.value() == 'External "frame-trigger"'):
                self.prepAndRun()
            else:
                self.digModWarning.exec_()
        else:
            self.scanner.abort()

    def prepAndRun(self, continuous=False):
        ''' Only called if scanner is not running (See scanOrAbort function).
        '''
        if self.scanRadio.isChecked():
            self.stageScan.update(self.scanParValues)
            self.scanButton.setText('Abort')
            if not(continuous):
                self.main.piezoWidget.resetChannels(
                    self.stageScan.activeChannels[self.stageScan.scanMode])
            self.scanner = Scanner(self.nidaq, self.stageScan, self.pxCycle,
                                   self, continuous)
            self.scanner.finalizeDone.connect(self.finalizeDone)
            self.scanner.scanDone.connect(self.scanDone)
            self.scanning = True
            if self.focusLocked:
                self.focusWgt.unlockFocus()

            self.main.lvworkers[0].startRecording()

            self.scanner.runScan()

        elif self.scanButton.isChecked():
            self.lasercycle = LaserCycle(self.nidaq, self.pxCycle)
            self.scanButton.setText('Stop')
            self.lasercycle.run()

        else:
            self.lasercycle.stop()
            self.scanButton.setText('Run')
            del self.lasercycle

    def scanDone(self):
        self.scanButton.setEnabled(False)

        if not self.scanner.aborted:
            time.sleep(0.1)

            self.main.lvworkers[0].stopRecording()

            # Building scanning image in 2D or 3D
            if self.multiScanWgt.makeImgBox.isChecked():

                # Get data
                data = self.main.lvworkers[0].fRecorded

                # Send data to MultipleScanWidget and analyze it
                if self.stageScan.scanMode == 'FOV scan':
                    datashape = (len(data), *self.main.shapes[0][::-1])
                    data = np.reshape(data, datashape)
                    self.multiScanWgt.worker.set_images(data)
                    self.multiScanWgt.worker.find_fp()
                    self.multiScanWgt.worker.analyze()

                elif self.stageScan.scanMode == 'VOL scan':
                    vScan = self.stageScan.scans['VOL scan']
                    datashape = (vScan.stepsZ, -1, *self.main.shapes[0][::-1])
                    data = np.reshape(data, datashape)
                    stk = np.zeros((vScan.stepsZ, vScan.stepsY, vScan.stepsX))
                    i = 0
                    for image in data:
                        self.multiScanWgt.worker.set_images(image)
                        self.multiScanWgt.worker.find_fp()
                        self.multiScanWgt.worker.analyze()
                        stk[i] = self.multiScanWgt.worker.illumImgs[0]
                        i += 1

                    xAx = np.arange(0, vScan.stepsZ*vScan.stepSizeZ,
                                    vScan.stepSizeZ)
                    self.multiScanWgt.illumWgt3D.setImage(stk, xvals=xAx)

    def finalizeDone(self):
        if (not self.continuousCheck.isChecked()) or self.scanner.aborted:
            self.scanButton.setText('Scan')
            self.scanButton.setEnabled(True)
            del self.scanner
            self.scanning = False
            if self.focusLocked:
                self.focusWgt.lockFocus()
            self.main.piezoWidget.resetChannels(
                self.stageScan.activeChannels[self.stageScan.scanMode])
        elif self.continuousCheck.isChecked():
            self.scanButton.setEnabled(True)
            self.prepAndRun(True)
        else:
            self.scanButton.setEnabled(True)
            self.prepAndRun()

    def updateScan(self, devices):
        self.stageScan.update(self.scanParValues)
        self.pxCycle.update(devices, self.pxParValues, self.stageScan.seqSamps)

    def closeEvent(self, *args, **kwargs):
        try:
            self.scanner.waiter.terminate()
        except BaseException:
            pass


class WaitThread(QtCore.QThread):
    waitdoneSignal = QtCore.pyqtSignal()

    def __init__(self, task):
        super().__init__()
        self.task = task
        self.wait = True

    def run(self):
        if self.wait:
            self.task.wait_until_done(nidaqmx.constants.WAIT_INFINITELY)
        self.wait = True
        self.waitdoneSignal.emit()

    def stop(self):
        self.wait = False


class Scanner(QtCore.QObject):
    """This class plays the role of interface between the software and the
    hardware. It writes the different signals to the electronic cards and
    manages the timing of a scan.

    :param nidaqmx.Device device: NiDaq card
    :param StageScan stageScan: object containing the analog signals to drive
    the stage
    :param PixelCycle pxCycle: object containing the digital signals to
    drive the lasers at each pixel acquisition
    :param ScanWidget main: main scan GUI."""

    scanDone = QtCore.pyqtSignal()
    finalizeDone = QtCore.pyqtSignal()

    def __init__(self, device, stageScan, pxCycle, main, continuous=False,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.nidaq = device
        self.stageScan = stageScan
        self.pxCycle = pxCycle
        self.continuous = continuous

        self.sampsInScan = len(self.stageScan.sigDict['x'])
        self.main = main

        self.aotask = nidaqmx.Task('aotask')
        self.dotask = nidaqmx.Task('dotask')
        self.waiter = WaitThread(self.aotask)

        self.scanTimeW = QtGui.QMessageBox()
        self.scanTimeW.setInformativeText("Are you sure you want to continue?")
        self.scanTimeW.setStandardButtons(QtGui.QMessageBox.Yes |
                                          QtGui.QMessageBox.No)
        self.channelOrder = main.channelOrder

        self.aborted = False

        self.focusWgt = self.main.focusWgt

        AOchans = [0, 1, 2]
        # Following loop creates the voltage channels
        for n in range(len(AOchans)):
            self.aotask.ao_channels.add_ao_voltage_chan(
                physical_channel='Dev1/ao%s' % AOchans[n],
                name_to_assign_to_channel='chan_%s' % self.channelOrder[n],
                min_val=minVolt[self.channelOrder[n]],
                max_val=maxVolt[self.channelOrder[n]])

        self.fullAOsig = np.array(
            [self.stageScan.sigDict[self.channelOrder[i]]
             for i in range(len(AOchans))])

        # Same as above but for the digital signals/devices
        devs = list(self.pxCycle.sigDict.keys())
        DOchans = range(0, 4)
        for d in DOchans:
            chanstring = 'Dev1/port0/line%s' % d
            self.dotask.do_channels.add_do_chan(
                lines=chanstring, name_to_assign_to_lines='chan%s' % devs[d])

        fullDOsig = np.array(
            [self.pxCycle.sigDict[devs[i]] for i in DOchans])

        """When doing unidirectional scan, the time needed for the stage to
        move back to the initial x needs to be filled with zeros/False.
        This time is now set to the time spanned by 1 sequence.
        Therefore, the digital signal is assambled as the repetition of the
        sequence for the whole scan in one row and then append zeros for 1
        sequence time. THIS IS NOW INCOMPATIBLE WITH VOLUMETRIC SCAN, maybe."""
        if self.stageScan.primScanDim == 'x':
            primSteps = self.stageScan.scans[self.stageScan.scanMode].stepsX
        else:
            primSteps = self.stageScan.scans[self.stageScan.scanMode].stepsY
        # Signal for a single line
        lineSig = np.tile(fullDOsig, primSteps)
        emptySig = np.zeros((4, int(self.stageScan.seqSamps)), dtype=bool)
        self.fullDOsig = np.concatenate((emptySig, lineSig, emptySig), axis=1)

    def runScan(self):
        self.aborted = False

        self.aotask.timing.cfg_samp_clk_timing(
            rate=self.stageScan.sampleRate,
            source=r'100kHzTimeBase',
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=self.sampsInScan)
        self.dotask.timing.cfg_samp_clk_timing(
            rate=self.pxCycle.sampleRate,
            source=r'ao/SampleClock',
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=self.sampsInScan)
        self.aotask.write(self.fullAOsig, auto_start=False)
        self.dotask.write(self.fullDOsig, auto_start=False)

        try:
            self.waiter.waitdoneSignal.disconnect(self.done)
        except TypeError:
            # This happens when the scan is aborted after the warning
            pass
        self.waiter.waitdoneSignal.connect(self.finalize)

        self.dotask.start()
        self.aotask.start()
        self.waiter.start()

    def abort(self):
        self.aborted = True
        self.waiter.stop()
        self.aotask.stop()
        self.dotask.stop()
        self.finalize()

    def finalize(self):
        self.scanDone.emit()
        # Apparently important, otherwise finalize is called again when next
        # waiting finishes.
        try:
            self.waiter.waitdoneSignal.disconnect(self.finalize)
        except TypeError:
            # This happens when the scan is aborted after the warning
            pass
        self.waiter.waitdoneSignal.connect(self.done)

        # Following code should correct channels mentioned in Buglist. Not
        # correct though, assumes channels are 0, 1 and 2.
        # TODO: Test abort (task function)
        writtenSamps = int(np.round(self.aotask.out_stream.curr_write_pos))
        chans = [0, 1, 2]
        dim = [self.channelOrder[i] for i in chans]
        finalSamps = [
            self.stageScan.sigDict[dim[i]][writtenSamps - 1] for i in chans]
        seqTime = self.main.scanParValues['seqTime']
        returnRamps = np.array(
            [makeRamp(finalSamps[i], 0, int(self.stageScan.sampleRate*seqTime))
             for i in chans])

        self.aotask.stop()
        self.aotask.timing.cfg_samp_clk_timing(
            rate=self.stageScan.sampleRate,
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=self.stageScan.sampleRate)

        self.aotask.write(returnRamps, auto_start=True)
        self.waiter.start()

    def done(self):
        self.aotask.stop()
        self.aotask.close()
        self.dotask.stop()
        self.dotask.close()
        self.nidaq.reset_device()
        self.finalizeDone.emit()


class MultipleScanWidget(QtGui.QFrame):

    def __init__(self, main):
        super().__init__()

        self.main = main

        illumPlotsDockArea = DockArea()
        # trato de poner otra solapa con el livescan
#        self.Luchoscan = LuchoScanWidget()
#        lucDock = Dock("Lucho scanning")
#        lucDock.addWidget(self.Luchoscan)  # Ger

        # make illumination image widget
        self.illumWgt = IllumImageWidget()
        fovDock = Dock("2D scanning")
        fovDock.addWidget(self.illumWgt)

        self.illumWgt3D = pg.ImageView()
        pos, rgba = zip(*guitools.cmapToColormap(plt.get_cmap('inferno')))
        self.illumWgt3D.setColorMap(pg.ColorMap(pos, rgba))
        for tick in self.illumWgt3D.ui.histogram.gradient.ticks:
            tick.hide()
        volDock = Dock("3D scanning")
        volDock.addWidget(self.illumWgt3D)

        illumPlotsDockArea.addDock(volDock)
        illumPlotsDockArea.addDock(fovDock, 'above', volDock)
#        illumPlotsDockArea.addDock(lucDock, 'above', fovDock)  # Ger
#        # Anda pero no me entra en el espacio. prefuero sacar lo viejo

        self.makeImgBox = QtGui.QCheckBox('Build scan image')

        # Crosshair
        self.crosshair = guitools.Crosshair(self.illumWgt.vb)
        self.crossButton = QtGui.QPushButton('Crosshair')
        self.crossButton.setCheckable(True)
        self.crossButton.pressed.connect(self.crosshair.toggle)

        # make worker
        self.worker = MultiScanWorker(self, self.main)

        # make other GUI components
        self.analysis_btn = QtGui.QPushButton('Analyze')
        self.analysis_btn.clicked.connect(self.worker.analyze)
        self.analysis_btn.setSizePolicy(QtGui.QSizePolicy.Preferred,
                                        QtGui.QSizePolicy.Expanding)
        self.show_beads_btn = QtGui.QPushButton('Show beads')
        self.show_beads_btn.clicked.connect(self.worker.find_fp)
        self.quality_label = QtGui.QLabel('Quality level of points')
        self.quality_edit = QtGui.QLineEdit('0.05')
        self.quality_edit.editingFinished.connect(self.worker.find_fp)
        self.win_size_label = QtGui.QLabel('Window size [px]')
        self.win_size_edit = QtGui.QLineEdit('10')
        self.win_size_edit.editingFinished.connect(self.worker.find_fp)

        self.beads_label = QtGui.QLabel('Bead number')
        self.beadsBox = QtGui.QComboBox()
        self.beadsBox.activated.connect(self.change_illum_image)
        self.change_beads_button = QtGui.QPushButton('Change')
        self.change_beads_button.clicked.connect(self.nextBead)
        self.overlayBox = QtGui.QComboBox()
        self.overlayBox.activated.connect(self.worker.overlay)
        self.overlay_check = QtGui.QCheckBox('Overlay')
        self.overlay_check.stateChanged.connect(self.worker.overlay)
        self.clear_btn = QtGui.QPushButton('Clear')
        self.clear_btn.clicked.connect(self.clear)

        grid = QtGui.QGridLayout()
        self.setLayout(grid)

        grid.addWidget(self.crossButton, 0, 0)
        grid.addWidget(self.makeImgBox, 0, 1)
        grid.addWidget(illumPlotsDockArea, 1, 0, 1, 8)

        grid.addWidget(self.quality_label, 2, 0)
        grid.addWidget(self.quality_edit, 2, 1)
        grid.addWidget(self.win_size_label, 3, 0)
        grid.addWidget(self.win_size_edit, 3, 1)
        grid.addWidget(self.show_beads_btn, 2, 2)
        grid.addWidget(self.analysis_btn, 3, 2)

        grid.addWidget(self.beads_label, 2, 4)
        grid.addWidget(self.beadsBox, 2, 5)
        grid.addWidget(self.change_beads_button, 3, 4, 1, 2)
        grid.addWidget(self.overlay_check, 2, 6)
        grid.addWidget(self.overlayBox, 2, 7)
        grid.addWidget(self.clear_btn, 3, 6, 1, 2)

        grid.setColumnMinimumWidth(3, 100)

    def change_illum_image(self):
        self.worker.delete_label()
        curr_ind = self.beadsBox.currentIndex()
        self.illumWgt.update(self.worker.illumImgs[curr_ind])
        self.illumWgt.vb.autoRange()
        if self.overlay_check.isChecked():
            self.illumWgt.updateBack(self.worker.illumImgs_back[curr_ind])
        if curr_ind == len(self.worker.illumImgs) - 1:
            self.worker.showLargeViewLabel()

    def nextBead(self):
        self.worker.delete_label()
        curr_ind = self.beadsBox.currentIndex()
        if len(self.worker.illumImgs) == curr_ind + 1:
            next_ind = 0
        else:
            next_ind = curr_ind + 1
        self.illumWgt.update(self.worker.illumImgs[next_ind])
        self.beadsBox.setCurrentIndex(next_ind)
        if self.overlay_check.isChecked():
            self.illumWgt.updateBack(self.worker.illumImgs_back[next_ind])
        if next_ind == len(self.worker.illumImgs) - 1:
            self.worker.showLargeViewLabel()
        self.illumWgt.vb.autoRange()

    def clear(self):
        self.worker.illumImgsStocked = []
        self.overlayBox.clear()


class MultiScanWorker(QtCore.QObject):

    def __init__(self, main_wgt, mainScanWid):
        super().__init__()

        self.main = main_wgt
        self.mainScanWid = mainScanWid
        self.illumImgs = []
        self.illumImgsStocked = []
        self.labels = []

        # corner detection parameter of Shi-Tomasi
        self.featureParams = dict(maxCorners=100, qualityLevel=0.1,
                                  minDistance=7, blockSize=7)

    def set_images(self, images):
        stageScan = self.mainScanWid.scanner.stageScan
        self.primScanDim = stageScan.primScanDim
        if self.primScanDim == 'x':
            self.steps = [stageScan.scans[stageScan.scanMode].stepsY,
                          stageScan.scans[stageScan.scanMode].stepsX]
        else:
            self.steps = [stageScan.scans[stageScan.scanMode].stepsX,
                          stageScan.scans[stageScan.scanMode].stepsY]
        self.images = images

    def find_fp(self):
        self.main.illumWgt.delete_back()

        # find feature points
        ql = float(self.main.quality_edit.text())
        self.featureParams['qualityLevel'] = ql
        self.radius = int(self.main.win_size_edit.text())
        self.nor_const = 255 / (np.max(self.images))

        self.fFrame = (self.images[1] * self.nor_const).astype(np.uint8)
        self.lFrame = (self.images[-1] * self.nor_const).astype(np.uint8)
        fps_f = goodFeaturesToTrack(
            self.fFrame, mask=None, **self.featureParams)
        fps_f = np.array([point[0] for point in fps_f])
        self.fps_f = fps_f[fps_f[:, 0].argsort()]
        fps_l = goodFeaturesToTrack(
            self.lFrame, mask=None, **self.featureParams)
        self.fps_l = np.array([point[0] for point in fps_l])

        # make frame for visualizing feature point detection
        self.frameView = (self.fFrame + self.lFrame) / 2

        # draw feature points image
        self.delete_label()
        self.centers = []   # center points between first FPs and last FPs
        self.fps_ll = []    # FPs of last frame that match ones of fist frame
        for i, fp_f in enumerate(self.fps_f):
            distances = [np.linalg.norm(fp_l - fp_f) for fp_l in self.fps_l]
            ind = np.argmin(distances)
            self.fps_ll.append(self.fps_l[ind])
            center = (fp_f + self.fps_l[ind]) / 2
            self.centers.append(center)
            # draw calculating window
            rectangle(self.frameView,
                      (int(center[0]-self.radius), int(center[1]-self.radius)),
                      (int(center[0]+self.radius), int(center[1]+self.radius)),
                      255, 1)
            # make labels for each window
            label = pg.TextItem()
            label.setPos(center[0] + self.radius, center[1] + self.radius)
            label.setText(str(i))
            self.labels.append(label)
            self.main.illumWgt.vb.addItem(label)
        self.main.illumWgt.update(self.frameView.T, invert=False)
        self.main.illumWgt.vb.autoRange()

    def analyze(self):
        self.main.beadsBox.clear()
        self.illumImgs = []

        self.delete_label()

        data_mean = []      # means of calculating window for each images
        cps_f = []          # center points of beads in first frame
        cps_l = []          # center points of beads in last frame
        for i in range(len(self.centers)):
            data_mean.append([])
            # record the center point of gravity
            cps_f.append(self.find_cp(
                self.fFrame, self.fps_f[i].astype(np.uint16), self.radius))
            cps_l.append(self.find_cp(
                self.lFrame, self.fps_ll[i].astype(np.uint16), self.radius))

            # calculate the mean of calculating window
            for image in self.images:
                mean = self.meanROI(
                    image, self.centers[i].astype(np.uint16), self.radius)
                data_mean[i].append(mean)

        # reconstruct the illumination image
        for i in range(len(data_mean)):
            data_r = np.reshape(data_mean[i], self.steps)
            if self.primScanDim == 'x':
                data_r = data_r.T
            self.illumImgs.append(data_r)
            self.main.beadsBox.addItem(str(i))

        # stock images for overlaying
        self.illumImgsStocked.append(self.illumImgs)
        self.main.overlayBox.addItem(str(self.main.overlayBox.count()))

        # make large field of view of illumination image
        # expand beads image
        dif = []
        for i in range(len(cps_f)):
            dif_x = np.abs(cps_f[i][0] - cps_l[i][0])
            dif_y = np.abs(cps_f[i][1] - cps_l[i][1])
            dif.append(max(dif_x, dif_y))
        rate = max(self.steps) / np.average(dif)
        imgLarge = np.zeros((int(self.fFrame.shape[0]*rate),
                             int(self.fFrame.shape[1]*rate))).T

        self.points_large = []  # start and end points of illumination image
        for point, illum_image in zip(self.fps_f, self.illumImgs):
            px = imgLarge.shape[1] - (point[1] * rate).astype(int)
            py = imgLarge.shape[0] - (point[0] * rate).astype(int)
            if self.primScanDim == 'x':
                pxe = min(px+self.steps[0], imgLarge.shape[1])
                pye = min(py+self.steps[1], imgLarge.shape[0])
            else:
                pxe = min(px+self.steps[1], imgLarge.shape[1])
                pye = min(py+self.steps[0], imgLarge.shape[0])
            imgLarge[py:pye, px:pxe] = illum_image[0:pye-py, 0:pxe-px]
            self.points_large.append([px, py, pxe, pye])
        self.illumImgs.append(imgLarge)

        # update illumination image
        self.main.illumWgt.update(imgLarge)
        self.showLargeViewLabel()
        self.main.beadsBox.addItem('Large FOV')
        self.main.beadsBox.setCurrentIndex(len(self.illumImgs) - 1)
        self.main.illumWgt.vb.autoRange()

        # do not display large view if bead is only one
        if len(self.illumImgs) == 2:
            self.main.nextBead()

    def overlay(self):
        ind = self.main.overlayBox.currentIndex()
        self.illumImgs_back = []     # illumination images for overlay

        # overlay previous image to current image
        if self.main.overlay_check.isChecked():

            # process the large field of view
            illumImgLargePre = np.zeros(self.illumImgs[-1].shape)
            for i, point in enumerate(self.points_large):
                px, py, pxe, pye = point
                illumImgPre = self.illumImgsStocked[ind][i]
                illumImgLargePre[py:pye, px:pxe] = illumImgPre[:pye-py,
                                                               :pxe-px]

            # process each image
            for i in range(len(self.illumImgs) - 1):
                illumImgPre = self.illumImgsStocked[ind][i]
                self.illumImgs_back.append(illumImgPre)

            self.illumImgs_back.append(illumImgLargePre)

            # update the background image
            img = self.illumImgs_back[self.main.beadsBox.currentIndex()]
            self.main.illumWgt.updateBack(img)

        else:
            self.illumImgs_back.clear()
            self.main.illumWgt.delete_back()

    def delete_label(self):
        # delete beads label
        if len(self.labels) != 0:
            for label in self.labels:
                self.main.illumWgt.vb.removeItem(label)
            self.labels.clear()

    def showLargeViewLabel(self):
        for i, point in enumerate(self.points_large):
            px, py, pxe, pye = point
            label = pg.TextItem()
            label.setPos(py, px)
            label.setText(str(i))
            self.labels.append(label)
            self.main.illumWgt.vb.addItem(label)

    @staticmethod
    def meanROI(array, p, r):
        xs = max(p[0] - r, 0)
        xe = min(p[0] + r, array.shape[1])
        ys = max(p[1] - r, 0)
        ye = min(p[1] + r, array.shape[0])
        roi = array[ys: ye, xs: xe]
        return np.average(roi)

    @staticmethod
    def find_cp(array, point, r):
        xs = max(point[0] - r, 0)
        xe = min(point[0] + r, array.shape[1])
        ys = max(point[1] - r, 0)
        ye = min(point[1] + r, array.shape[0])
        roi = array[ys: ye, xs: xe]
        M = moments(roi, False)
        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])
        return [int(cx + point[0] - r), int(cy + point[1] - r)]


class IllumImageWidget(pg.GraphicsLayoutWidget):

    def __init__(self):
        super().__init__()

        self.vb = self.addViewBox(row=1, col=1)
        self.vb.setAspectLocked(True)
        self.vb.enableAutoRange()

        self.img = pg.ImageItem()
        self.vb.addItem(self.img)
        self.hist = pg.HistogramLUTItem(image=self.img)
        self.hist.vb.setLimits(yMin=0, yMax=66000)
        redsColormap = pg.ColorMap([0, 1], [(0, 0, 0), (255, 0, 0)])
        self.hist.gradient.setColorMap(redsColormap)
        for tick in self.hist.gradient.ticks:
            tick.hide()
        self.addItem(self.hist, row=1, col=2)

        self.imgBack = pg.ImageItem()
        self.vb.addItem(self.imgBack)
        self.imgBack.setZValue(10)
        self.imgBack.setOpacity(0.5)
        self.histBack = pg.HistogramLUTItem(image=self.imgBack)
        self.histBack.vb.setLimits(yMin=0, yMax=66000)
        pos, rgba = zip(*guitools.cmapToColormap(plt.get_cmap('viridis')))
        greensColormap = pg.ColorMap(pos, rgba)
        self.histBack.gradient.setColorMap(greensColormap)
        for tick in self.histBack.gradient.ticks:
            tick.hide()
        self.addItem(self.histBack, row=1, col=3)

        self.first = True
        self.firstBack = True

    def update(self, img, invert=True):
        self.img.setImage(img, autoLevels=self.first)
        if invert:
            self.vb.invertX(True)
            self.vb.invertY(True)
        else:
            self.vb.invertX(False)
            self.vb.invertY(False)
        if self.first:
            self.hist.setLevels(*guitools.bestLimits(img))
        self.first = False

    def updateBack(self, img):
        self.imgBack.setImage(img, autoLevels=self.firstBack)
        if self.first:
            self.histBack.setLevels(*guitools.bestLimits(img))
        self.firstBack = False

    def delete_back(self):
        self.imgBack.clear()
        self.firstBack = True


class LaserCycle():

    def __init__(self, device, pxCycle):
        self.nidaq = device
        self.pxCycle = pxCycle

    def run(self):
        self.dotask = nidaqmx.Task('dotaskLaser')

        devs = list(self.pxCycle.sigDict.keys())
        DOchans = range(0, 4)
        for d in DOchans:
            chanstring = 'Dev1/port0/line%s' % d
            self.dotask.do_channels.add_do_chan(
                lines=chanstring, name_to_assign_to_lines='chan%s' % devs[d])

        DOchans = [0, 1, 2, 3]
        fullDOsig = np.array(
            [self.pxCycle.sigDict[devs[i]] for i in DOchans])

        self.dotask.timing.cfg_samp_clk_timing(
           source=r'100kHzTimeBase',
           rate=self.pxCycle.sampleRate,
           sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS)

        self.dotask.write(fullDOsig, auto_start=False)

        self.dotask.start()

    def stop(self):
        self.dotask.stop()
        self.dotask.close()
        del self.dotask
        self.nidaq.reset_device()


class StageScan():
    '''Contains the analog signals in sig_dict. The update function takes the
    parameter_values and updates the signals accordingly.'''
    def __init__(self, sampleRate):
        self.scanMode = 'FOV scan'
        self.primScanDim = 'x'
        self.sigDict = {'x': [], 'y': [], 'z': []}
        self.sampleRate = sampleRate
        self.seqSamps = None
        self.FOVscan = FOVscan(self.sampleRate)
        self.VOLscan = VOLscan(self.sampleRate)
        self.lineScan = LineScan(self.sampleRate)
        self.scans = {'FOV scan': self.FOVscan,
                      'VOL scan': self.VOLscan,
                      'Line scan': self.lineScan}
        self.activeChannels = {'Line scan': ['x'],
                               'FOV scan':  ['x', 'y'],
                               'VOL scan':  ['x', 'y', 'z']}
        self.frames = 0

    def setScanMode(self, mode):
        self.scanMode = mode

    def setPrimScanDim(self, dim):
        self.primScanDim = dim

    def updateFrames(self, parValues):
        self.scans[self.scanMode].updateFrames(parValues)
        self.frames = self.scans[self.scanMode].frames

    def update(self, parValues):
        self.scans[self.scanMode].update(parValues, self.primScanDim)
        self.sigDict = self.scans[self.scanMode].sigDict
        self.seqSamps = self.scans[self.scanMode].seqSamps
        self.frames = self.scans[self.scanMode].frames


class LineScan():

    def __init__(self, sampleRate):
        self.sigDict = {'x': [], 'y': [], 'z': []}
        self.sampleRate = sampleRate
        self.corrStepSize = None
        self.seqSamps = None
        self.frames = 0

    def updateFrames(self, parValues):
        sizeY = parValues['sizeY'] / convFactors['y']
        stepSize = parValues['stepSizeXY'] / convFactors['y']
        stepsY = int(np.ceil(sizeY / stepSize))
        # +1 because nr of frames per line is one more than nr of steps
        self.frames = stepsY + 1

    def update(self, parValues, primScanDim):
        '''Create signals.
        First, distances are converted to voltages.'''
        startY = 0
        sizeY = parValues['sizeY'] / convFactors['y']
        seqSamps = np.round(self.sampleRate * parValues['seqTime'])
        stepSize = parValues['stepSizeXY'] / convFactors['y']
        self.stepsX = 0
        self.stepsY = int(np.ceil(sizeY / stepSize))
        self.stepsZ = 1
        # Step size compatible with width
        self.corrStepSize = sizeY / self.stepsY
        self.seqSamps = int(seqSamps)

        ramp = makeRamp(startY, sizeY, self.stepsY * self.seqSamps)
        self.sigDict[primScanDim] = 1.14 * ramp
        for key in self.sigDict:
            if not key[0] == primScanDim:
                self.sigDict[key] = np.zeros(len(ramp))


class FOVscan():

    def __init__(self, sampleRate):
        self.sigDict = {'x': [], 'y': [], 'z': []}
        self.sampleRate = sampleRate
        self.corrStepSize = None
        self.seqSamps = None
        self.frames = 0

    def updateFrames(self, parValues):
        '''Update signals according to parameters.
        Note that rounding floats to ints may cause actual scan to differ
        slightly from expected scan. Maybe either limit input parameters to
        numbers that "fit each other" or find other solution, eg step size has
        to be width divided by an integer. Maybe not a problem ???'''
        stepSizeX = parValues['stepSizeXY']
        stepSizeY = parValues['stepSizeXY']
        sizeX = parValues['sizeX']
        sizeY = parValues['sizeY']
        stepsX = int(np.ceil(sizeX / stepSizeX))
        stepsY = int(np.ceil(sizeY / stepSizeY))
        # +1 because nr of frames per line is one more than nr of steps
        self.frames = stepsY * stepsX

    def update(self, parValues, primScanDim):
        '''Create signals.
        Signals are first created in units of distance and converted to voltage
        at the end.'''
        # Create signals
        startX = startY = 0
        sizeX = parValues['sizeX']
        sizeY = parValues['sizeY']
        stepSizeX = parValues['stepSizeXY']
        stepSizeY = parValues['stepSizeXY']
        self.seqSamps = int(np.round(self.sampleRate*parValues['seqTime']))
        self.stepsX = int(np.ceil(sizeX / stepSizeX))
        self.stepsY = int(np.ceil(sizeY / stepSizeY))
        self.stepsZ = 1
        # Step size compatible with width
        self.corrStepSize = sizeX / self.stepsX

        if primScanDim == 'x':
            self.makePrimDimSig('x', startX, sizeX, self.stepsX, self.stepsY)
            self.makeSecDimSig('y', startY, sizeY, self.stepsY, self.stepsX)
        elif primScanDim == 'y':
            self.makePrimDimSig('y', startY, sizeY, self.stepsY, self.stepsX)
            self.makeSecDimSig('x', startX, sizeX, self.stepsX, self.stepsY)

        self.sigDict['z'] = np.zeros(len(self.sigDict['x']))

    def makePrimDimSig(self, dim, start, size, steps, otherSteps):
        rowSamps = steps * self.seqSamps
        LTRramp = makeRamp(start, size, rowSamps)
        # Fast return to startX
        RTLramp = makeRamp(size, start, self.seqSamps)
        LTRramp = np.concatenate((start*np.ones(self.seqSamps), LTRramp))
        LTRTLramp = np.concatenate((LTRramp, RTLramp))
        primSig = np.tile(LTRTLramp, otherSteps)
        self.sigDict[dim] = primSig / convFactors[dim]

    def makeSecDimSig(self, dim, start, size, steps, otherSteps):
        # y axis scan signal
        colSamps = steps * self.seqSamps
        Yramp = makeRamp(start, size, colSamps)
        Yramps = np.split(Yramp, steps)
        constant = np.ones((otherSteps + 1)*self.seqSamps)
        Sig = np.array([np.concatenate((i[0]*constant, i)) for i in Yramps])
        secSig = Sig.ravel()
        self.sigDict[dim] = secSig / convFactors[dim]


class VOLscan():

    def __init__(self, sampleRate):
        self.sigDict = {'x': [], 'y': [], 'z': []}
        self.sampleRate = sampleRate
        self.corrStepSize = None
        self.seqSamps = None
        self.frames = 0
        self.stepsX = 0
        self.stepsY = 0
        self.stepsZ = 0

    def updateFrames(self, parValues):
        '''Update signals according to parameters.
        Note that rounding floats to ints may cause actual scan to differ
        slightly from expected scan. Maybe either limit input parameters to
        numbers that "fit each other" or find other solution, eg step size has
        to be width divided by an integer. Maybe not a problem ???'''
        stepSizeX = parValues['stepSizeXY']
        stepSizeY = parValues['stepSizeXY']
        self.stepSizeZ = parValues['stepSizeZ']
        sizeX = parValues['sizeX']
        sizeY = parValues['sizeY']
        sizeZ = parValues['sizeZ']
        stepsX = int(np.ceil(sizeX / stepSizeX))
        stepsY = int(np.ceil(sizeY / stepSizeY))
        stepsZ = int(np.ceil(sizeZ / self.stepSizeZ))
        # +1 because nr of frames per line is one more than nr of steps
        self.frames = stepsY * stepsX * stepsZ

    def update(self, parValues, primScanDim):
        '''Create signals.
        Signals are first created in units of distance and converted to voltage
        at the end.'''
        # Create signals
        startX = startY = startZ = 0
        sizeX = parValues['sizeX']
        sizeY = parValues['sizeY']
        sizeZ = parValues['sizeZ']
        stepSizeX = parValues['stepSizeXY']
        stepSizeY = parValues['stepSizeXY']
        self.stepSizeZ = parValues['stepSizeZ']
        self.seqSamps = int(np.round(self.sampleRate*parValues['seqTime']))
        self.stepsX = int(np.ceil(sizeX / stepSizeX))
        self.stepsY = int(np.ceil(sizeY / stepSizeY))
        self.stepsZ = int(np.ceil(sizeZ / self.stepSizeZ))
        # Step size compatible with width
        self.corrStepSize = sizeX / self.stepsX

        if primScanDim == 'x':
            self.makePrimDimSig(
                'x', startX, sizeX, self.stepsX, [self.stepsY, self.stepsZ])
            self.makeSecDimSig(
                'y', startY, sizeY, self.stepsY, [self.stepsX, self.stepsZ])
            self.makeThiDimSig(
                'z', startZ, sizeZ, self.stepsZ, [self.stepsX, self.stepsY])
        elif primScanDim == 'y':
            self.makePrimDimSig(
                'y', startY, sizeY, self.stepsY, [self.stepsX, self.stepsZ])
            self.makeSecDimSig(
                'x', startX, sizeX, self.stepsX, [self.stepsY, self.stepsZ])
            self.makeThiDimSig(
                'z', startZ, sizeZ, self.stepsZ, [self.stepsY, self.stepsX])

    def makePrimDimSig(self, dim, start, size, steps, otherSteps):
        rowSamps = steps * self.seqSamps
        LTRramp = makeRamp(start, size, rowSamps)
        # Fast return to startX
        RTLramp = makeRamp(size, start, self.seqSamps)
        LTRramp = np.concatenate((start*np.ones(self.seqSamps), LTRramp))
        LTRTLramp = np.concatenate((LTRramp, RTLramp))
        numSig = otherSteps[0] * otherSteps[1]
        primSig = np.tile(LTRTLramp, numSig)
        self.sigDict[dim] = primSig / convFactors[dim]

    def makeSecDimSig(self, dim, start, size, steps, otherSteps):
        colSamps = steps * self.seqSamps
        ramp = makeRamp(start, size, colSamps)
        ramps = np.split(ramp, steps)
        ramps = ramps[0:len(ramps)-1]
        wait = otherSteps[0] + 1
        constant = np.ones(wait * self.seqSamps)
        sig = np.array([np.concatenate((i, i[-1]*constant)) for i in ramps])
        sig = sig.ravel()
        returnRamp = makeRamp(sig[-1], start, self.seqSamps)
        sig = np.concatenate((constant*0, sig, returnRamp))
        numSig = otherSteps[1]
        secSig = np.tile(sig, numSig)
        self.sigDict[dim] = secSig / convFactors[dim]

    def makeThiDimSig(self, dim, start, size, steps, otherSteps):
        colSamps = steps * self.seqSamps
        ramp = makeRamp(start, size, colSamps)
        ramps = np.split(ramp, steps)
        ramps = ramps[0:len(ramps)-1]
        wait = (otherSteps[0]+2) * otherSteps[1] - 1
        constant = np.ones(wait*self.seqSamps)
        sig = np.array([np.concatenate((i, i[-1]*constant)) for i in ramps])
        sig = sig.ravel()
        returnRamp = makeRamp(sig[-1], start, self.seqSamps)
        sig = np.concatenate((constant*0, sig, returnRamp))
        thiSig = sig
        self.sigDict[dim] = thiSig / convFactors[dim]


class PixelCycle():
    ''' Contains the digital signals for the pixel cycle. The update function
    takes a parameter_values dict and updates the signal accordingly.'''
    def __init__(self, sampleRate):
        self.sigDict = collections.OrderedDict(
            [('405', []), ('488', []), ('473', []), ('CAM', [])])
        self.sampleRate = sampleRate
        self.cycleSamps = None

    def update(self, devices, parValues, cycleSamps):
        self.cycleSamps = cycleSamps
        for device in devices:
            signal = np.zeros(cycleSamps, dtype='bool')
            start_name = 'start' + device
            end_name = 'end' + device
            start_pos = parValues[start_name] * self.sampleRate
            start_pos = int(min(start_pos, cycleSamps - 1))
            end_pos = parValues[end_name] * self.sampleRate
            end_pos = int(min(end_pos, cycleSamps))
            signal[range(start_pos, end_pos)] = True
            self.sigDict[device] = signal


class GraphFrame(pg.GraphicsWindow):
    """Creates the plot that plots the preview of the pulses.
    Fcn update() updates the plot of "device" with signal "signal"."""
    def __init__(self, pxCycle, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.pxCycle = pxCycle
        self.plot = self.addPlot(row=1, col=0)
        self.plot.setYRange(0, 1)
        self.plot.showGrid(x=False, y=False)
        self.plotSigDict = {'405': self.plot.plot(pen=pg.mkPen(130, 0, 200)),
                            '488': self.plot.plot(pen=pg.mkPen(0, 247, 255)),
                            '473': self.plot.plot(pen=pg.mkPen(0, 183, 255)),
                            'CAM': self.plot.plot(pen='w')}

    def update(self, devices=None):
        if devices is None:
            devices = self.plotSigDict

        for device in devices:
            signal = self.pxCycle.sigDict[device]
            self.plotSigDict[device].setData(signal)


def makeRamp(start, end, samples):
    return np.linspace(start, end, num=samples)


def smoothRamp(start, end, samples):
    x = np.linspace(start, end, num=samples, endpoint=True)
    signal = start + (end - start) * 0.5*(1 - np.cos(x * np.pi))
    return signal

# --- Barrido dinamico de lucho ---


class LuchoScanWidget(QtGui.QFrame):

    def __init__(self, device, *args, **kwargs):  # agregue device

        super().__init__(*args, **kwargs)

        self.nidaq = device  # esto creo que tiene que ir

        imageWidget = pg.GraphicsLayoutWidget()
        self.vb = imageWidget.addViewBox(row=1, col=1)

        # LiveView Button

        self.liveviewButton = QtGui.QPushButton('confocal LIVEVIEW')
        self.liveviewButton.setCheckable(True)
        self.liveviewButton.clicked.connect(self.liveview)
#        self.liveviewButton.clicked.connect(self.channelsOpen)

        # Defino el tipo de Scan que quiero

        self.scanMode = QtGui.QComboBox()
        self.scanModes = ['step scan', 'otro scan', 'tempesta scan']
        self.scanMode.addItems(self.scanModes)
        self.scanMode.currentIndexChanged.connect(
            lambda: self.setScanMode(self.scanMode.currentText()))

        def setScanMode(self, mode):
            self.stageScan.setScanMode(mode)
            self.scanParameterChanged('scanMode')

        # Scanning parameters

        self.initialPositionLabel = QtGui.QLabel('Initial Pos [x0 y0] (µm)')
        self.initialPositionEdit = QtGui.QLineEdit('0.1 0.1')
        self.scanRangeLabel = QtGui.QLabel('Scan range (µm)')
        self.scanRangeEdit = QtGui.QLineEdit('3')
        self.pixelTimeLabel = QtGui.QLabel('Pixel time (µs)')
        self.pixelTimeEdit = QtGui.QLineEdit('500')
        self.numberofPixelsLabel = QtGui.QLabel('Number of pixels')
        self.numberofPixelsEdit = QtGui.QLineEdit('16')
        self.pixelSizeLabel = QtGui.QLabel('Pixel size (nm)')
        self.pixelSizeValue = QtGui.QLabel('')

        self.timeTotalLabel = QtGui.QLabel('tiempo total del escaneo ()')
        self.timeTotalValue = QtGui.QLabel('')

        self.numberofPixelsEdit.textChanged.connect(self.paramChanged)
        self.scanRangeEdit.textChanged.connect(self.paramChanged)
        self.pixelTimeEdit.textChanged.connect(self.paramChanged)
        self.initialPositionEdit.textChanged.connect(self.paramChanged)

        self.paramChanged()

        print(self.Napd, "Napd\n", self.pixelTime, "pixeltime\n")
        self.paramWidget = QtGui.QWidget()

        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        grid.addWidget(imageWidget, 0, 0)
        grid.addWidget(self.paramWidget, 0, 1)

        subgrid = QtGui.QGridLayout()
        self.paramWidget.setLayout(subgrid)
        subgrid.addWidget(self.liveviewButton, 10, 1)
        subgrid.addWidget(self.scanMode, 12, 1)
        subgrid.addWidget(self.initialPositionLabel, 0, 1)
        subgrid.addWidget(self.initialPositionEdit, 1, 1)
        subgrid.addWidget(self.scanRangeLabel, 2, 1)
        subgrid.addWidget(self.scanRangeEdit, 3, 1)
        subgrid.addWidget(self.pixelTimeLabel, 4, 1)
        subgrid.addWidget(self.pixelTimeEdit, 5, 1)
        subgrid.addWidget(self.numberofPixelsLabel, 6, 1)
        subgrid.addWidget(self.numberofPixelsEdit, 7, 1)
        subgrid.addWidget(self.pixelSizeLabel, 8, 1)
        subgrid.addWidget(self.pixelSizeValue, 9, 1)
        subgrid.addWidget(self.timeTotalLabel, 13, 1)
        subgrid.addWidget(self.timeTotalValue, 14, 1)

        self.paramWidget.setFixedHeight(300)

        self.vb.setMouseMode(pg.ViewBox.RectMode)
        self.img = pg.ImageItem()
        self.img.translate(-0.5, -0.5)
        self.vb.addItem(self.img)
        self.vb.setAspectLocked(True)
        imageWidget.setAspectLocked(True)
        self.hist = pg.HistogramLUTItem(image=self.img)
        self.hist.gradient.loadPreset('thermal')
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

    def paramChanged(self):

        self.scanRange = float(self.scanRangeEdit.text())
        self.numberofPixels = int(self.numberofPixelsEdit.text())
        self.pixelTime = float(self.pixelTimeEdit.text()) / 100000  # segs
        self.initialPosition = np.array(
                        self.initialPositionEdit.text().split(' '))

        self.pixelSize = self.scanRange/self.numberofPixels

        self.pixelSizeValue.setText('{}'.format(np.around(
                                        1000 * self.pixelSize, 2)))  # en nm

        self.timeTotalValue.setText('{}'.format(np.around(
                        self.numberofPixels**2 * self.pixelTime, 2)))

        self.linetime = (1 / 1000) * float(self.pixelTimeEdit.text()) * float(
                                        self.numberofPixelsEdit.text())
        print(self.linetime)

        size = (self.numberofPixels, self.numberofPixels)

        self.inputImage = 100 * np.random.normal(size=size)
        self.blankImage = np.zeros(size)
        self.image = self.blankImage
#        self.i = 0
        self.dy = 0


# This is the function triggered by pressing the liveview button

    def liveview(self):
        """ Image live view when not recording
        """
        if self.liveviewButton.isChecked():
            self.liveviewStart()

        else:
            self.liveviewStop()

    def liveviewStart(self):

        self.channelsOpen()
        self.viewtimer.start(self.linetime)


    def liveviewStop(self):

        self.viewtimer.stop()
        self.done()

    def updateView(self):
        self.linea()
        self.lineData = self.cuentas  # self.inputImage[:, self.i]
        self.image[:, self.numberofPixels-1-self.dy] = self.lineData

        self.img.setImage(self.image, autoLevels=False)

        if self.dy < self.numberofPixels-1:
#            self.i = self.i + 1
            self.dy = self.dy + 1
        else:
#            self.i = 0
            self.dy = 0
            self.movetoStart()
#            self.inputImage = 100 * np.random.normal(
#                    size=(self.numberofPixels, self.numberofPixels))

    def linea(self):

        cuentas = np.zeros((self.numberofPixels))
        primSig = makeRamp(float(self.initialPosition[0]),  # initpos
                           self.scanRange, self.numberofPixels)

        self.barridox = primSig / convFactors['x']
        secSig = np.ones(self.numberofPixels) * float(self.initialPosition[1])
        self.barridoy = secSig / convFactors['y']
        self.barridoz = np.zeros(len(self.barridox))

        for i in range(self.numberofPixels):
            tic = time.time()

            self.aotask.write(
             [self.barridox[i],
              self.barridoy[i] + (self.dy * self.pixelSize / convFactors['y']),
              self.barridoz[i]], auto_start=True)

            APD = self.ditask.read(self.Napd)
            self.ditask.wait_until_done()
            aux = 0
            for c in range(self.Napd-1):
                if APD[c] < APD[c+1]:
                    aux = aux + 1
            cuentas[i] = np.random.rand(1)[0] + i + self.dy  # aux
            print(tic-time.time())
        self.cuentas = cuentas

    def channelsOpen(self):
        if 'NoseComoHacerloMejor' in globals():
            print("Ya estan abiertos los canales")  # para evitar el error
            #  usando esto podria no cerrarlos nunca.
        else:
            NoseComoHacerloMejor = int(1)
            global NoseComoHacerloMejor
            self.aotask = nidaqmx.Task('aotask')
            self.dotask = nidaqmx.Task('dotask')
            self.aitask = nidaqmx.Task('aitask')  # Ger
            self.ditask = nidaqmx.Task('ditask')  # Ger

            self.ditask.di_channels.add_di_chan(
                lines="Dev1/port0/line7", name_to_assign_to_lines='chan5',
                line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)

            apdrate = 9*10**6
            self.Napd = int(np.round(apdrate * self.pixelTime))
            self.ditask.timing.cfg_samp_clk_timing(
              rate=apdrate,
              sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
              samps_per_chan=self.Napd)

            self.channelOrder = ['x', 'y', 'z']
            AOchans = [0, 1, 2]
            # Following loop creates the voltage channels
            for n in range(len(AOchans)):
                self.aotask.ao_channels.add_ao_voltage_chan(
                    physical_channel='Dev1/ao%s' % AOchans[n],
                    name_to_assign_to_channel='chan_%s' % self.channelOrder[n],
                    min_val=minVolt[self.channelOrder[n]],
                    max_val=maxVolt[self.channelOrder[n]])

    def done(self):
        if 'NoseComoHacerloMejor' in globals():
            print("Cierro todos los canales")  # para evitar el error
            self.aotask.stop()
            self.aotask.close()
            self.dotask.stop()
            self.dotask.close()
            self.aitask.stop()  # Ger
            self.aitask.close()  # Ger
            self.ditask.stop()  # Ger
            self.ditask.close()  # Ger
    #        self.nidaq.reset_device()
    #        self.finalizeDone.emit()
            del NoseComoHacerloMejor
        else:
            print("llego hasta el done pero no tenia nada que cerrar")

    def movetoStart(self):
        t = 0.1
        print("vuelve al principio, tarda t segundos =", t)
        maximoy = (float(self.initialPosition[1]) + self.dy * self.pixelSize)
        volviendoy = np.linspace(maximoy, 0, 100)
        volviendox = np.zeros(len(volviendoy))
        volviendoz = np.zeros(len(volviendoy))
        for i in range(len(volviendoy)):
            self.aotask.write(
                 [volviendox[i],
                  volviendoy[i] / convFactors['y'],
                  volviendoz[i]], auto_start=True)
            time.sleep(t / 100)
        self.dy = 0
