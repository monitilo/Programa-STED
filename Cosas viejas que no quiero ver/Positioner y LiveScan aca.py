
""" Programa un poco mas completo para correr el liveScan CON LA NIDAQ
incluye positioner para moverse por la muestra"""

import numpy as np
import time
import scipy.ndimage as ndi
import matplotlib.pyplot as plt

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.dockarea import Dock, DockArea
import pyqtgraph.ptime as ptime

from PIL import Image

import re

import nidaqmx

device = nidaqmx.system.System.local().devices['Dev1']
convFactors = {'x': 25, 'y': 25, 'z': 1.683}
# la calibracion en x,y es 1 µm = 40 mV;1/0.040 = 25  (espejos galvanometricos)
# en z es 1.68 um = 1 V ==> 1 um = 0.59V; 1/0.59 ~=1.683  (platina nanomax)
minVolt = {'x': -10, 'y': -10, 'z': 0}
maxVolt = {'x': 10, 'y': 10, 'z': 10}

apdrate = 10**5

def makeRamp(start, end, samples):
    return np.linspace(start, end, num=samples)


class ScanWidget(QtGui.QFrame):

    def keyPressEvent(self, e):

        if e.key() == QtCore.Qt.Key_Escape:
            self.close()
            self.liveviewStop()

    def __init__(self, device, *args, **kwargs):  # agregue device

        super().__init__(*args, **kwargs)

        self.nidaq = device  # esto tiene que ir


# ---  Positioner metido adentro

        # Parameters for smooth moving (to no shake hard the piezo)
        self.moveTime = 0.1  # total time to move(s)
#        self.sampleRate = 10**3  # 10**5
        self.moveSamples = 50  # samples to move

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
        self.xLabel = QtGui.QLabel('0.0')
#            "<strong>x = {0:.2f} µm</strong>".format(self.x))
        self.xLabel.setTextFormat(QtCore.Qt.RichText)
        self.xUpButton = QtGui.QPushButton("+")
        self.xUpButton.pressed.connect(self.xMoveUp)
        self.xDownButton = QtGui.QPushButton("-")
        self.xDownButton.pressed.connect(self.xMoveDown)
        self.xStepEdit = QtGui.QLineEdit("1")  # estaban en 0.05<
        self.xStepUnit = QtGui.QLabel(" µm")

        self.yLabel = QtGui.QLabel('0.0')
#            "<strong>y = {0:.2f} µm</strong>".format(self.y))
        self.yLabel.setTextFormat(QtCore.Qt.RichText)
        self.yUpButton = QtGui.QPushButton("+")
        self.yUpButton.pressed.connect(self.yMoveUp)
        self.yDownButton = QtGui.QPushButton("-")
        self.yDownButton.pressed.connect(self.yMoveDown)
        self.yStepEdit = QtGui.QLineEdit("1")
        self.yStepUnit = QtGui.QLabel(" µm")

        self.zLabel = QtGui.QLabel('0.0')
#            "<strong>z = {0:.2f} µm</strong>".format(self.z))
        self.zLabel.setTextFormat(QtCore.Qt.RichText)
        self.zUpButton = QtGui.QPushButton("+")
        self.zUpButton.pressed.connect(self.zMoveUp)
        self.zDownButton = QtGui.QPushButton("-")
        self.zDownButton.pressed.connect(self.zMoveDown)
        self.zStepEdit = QtGui.QLineEdit("1")
        self.zStepUnit = QtGui.QLabel(" µm")

#---- fin parte del positioner ----------

        imageWidget = pg.GraphicsLayoutWidget()
        self.vb = imageWidget.addViewBox(row=1, col=1)

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

        # Defino el tipo de Scan que quiero

        self.scanMode = QtGui.QComboBox()
        self.scanModes = ['step scan', 'ramp scan', 'otro scan']
        self.scanMode.addItems(self.scanModes)
        self.scanMode.currentIndexChanged.connect(self.paramChanged)

        # para que guarde todo (trazas de Alan)

        self.Alancheck = QtGui.QRadioButton('Alan continous save')
        self.Alancheck.setChecked(False)

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

#        self.initialPositionLabel = QtGui.QLabel('Initial Pos [x0 y0 z0] (µm)')
#        self.initialPositionEdit = QtGui.QLineEdit('0 0 0')
        self.scanRangeLabel = QtGui.QLabel('Scan range (µm)')
        self.scanRangeEdit = QtGui.QLineEdit('10')
        self.pixelTimeLabel = QtGui.QLabel('Pixel time (ms)')
        self.pixelTimeEdit = QtGui.QLineEdit('1')
        self.numberofPixelsLabel = QtGui.QLabel('Number of pixels')
        self.numberofPixelsEdit = QtGui.QLineEdit('20')
        self.pixelSizeLabel = QtGui.QLabel('Pixel size (nm)')
        self.pixelSizeValue = QtGui.QLabel('')
        self.timeTotalLabel = QtGui.QLabel('tiempo total del escaneo (s)')
#        self.timeTotalValue = QtGui.QLabel('')

        self.onlyInt = QtGui.QIntValidator()
        self.numberofPixelsEdit.setValidator(self.onlyInt)

        self.numberofPixelsEdit.textChanged.connect(self.paramChanged)
        self.scanRangeEdit.textChanged.connect(self.paramChanged)
        self.pixelTimeEdit.textChanged.connect(self.paramChanged)
#        self.initialPositionEdit.textChanged.connect(self.paramChanged)

        self.paramChanged()

        self.paramWidget = QtGui.QWidget()

        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        grid.addWidget(imageWidget, 0, 0)
        grid.addWidget(self.paramWidget, 0, 1)

        subgrid = QtGui.QGridLayout()
        self.paramWidget.setLayout(subgrid)

#        subgrid.addWidget(self.initialPositionLabel, 0, 1)
#        subgrid.addWidget(self.initialPositionEdit, 1, 1)
        subgrid.addWidget(self.shutterredbutton, 0, 1)
        subgrid.addWidget(self.shuttergreenbutton, 1, 1)
        subgrid.addWidget(self.shutterotrobutton, 2, 1)
        subgrid.addWidget(self.scanRangeLabel, 3, 1)
        subgrid.addWidget(self.scanRangeEdit, 4, 1)
        subgrid.addWidget(self.pixelTimeLabel, 5, 1)
        subgrid.addWidget(self.pixelTimeEdit, 6, 1)
        subgrid.addWidget(self.numberofPixelsLabel, 7, 1)
        subgrid.addWidget(self.numberofPixelsEdit, 8, 1)
        subgrid.addWidget(self.pixelSizeLabel, 9, 1)
        subgrid.addWidget(self.pixelSizeValue, 10, 1)
        subgrid.addWidget(self.liveviewButton, 12, 1)
        subgrid.addWidget(self.scanMode, 11, 1)
        subgrid.addWidget(self.Alancheck, 13, 1)
        subgrid.addWidget(self.timeTotalLabel, 14, 1)
#        subgrid.addWidget(self.timeTotalValue, 14, 1)
        subgrid.addWidget(self.saveimageButton, 15, 1)


# - POSITIONERRRRR----------------------------

        self.positioner = QtGui.QWidget()
        grid.addWidget(self.positioner, 1, 0)
        layout = QtGui.QGridLayout()
        self.positioner.setLayout(layout)
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
        layout.addWidget(QtGui.QLabel("||"), 1, 6)
        layout.addWidget(QtGui.QLabel("||"), 2, 6)
        layout.addWidget(QtGui.QLabel("||"), 3, 6)

        self.gotoWidget = QtGui.QWidget()
        grid.addWidget(self.gotoWidget, 1, 1)
        layout2 = QtGui.QGridLayout()
        self.gotoWidget.setLayout(layout2)
        layout2.addWidget(QtGui.QLabel("||"), 1, 7)
        layout2.addWidget(QtGui.QLabel("||"), 2, 7)
        layout2.addWidget(QtGui.QLabel("||"), 3, 7)
        self.xgotoLabel = QtGui.QLineEdit("1")
        self.ygotoLabel = QtGui.QLineEdit("1")
        self.zgotoLabel = QtGui.QLineEdit("1")
        self.gotoButton = QtGui.QPushButton("Go")
        self.gotoButton.pressed.connect(self.goto)
        layout2.addWidget(self.gotoButton, 1, 9, 2, 2)
        layout2.addWidget(self.xgotoLabel, 1, 8)
        layout2.addWidget(self.ygotoLabel, 2, 8)
        layout2.addWidget(self.zgotoLabel, 3, 8)

#- fin POSITIONEERRRRRR----------------------------

        self.paramWidget.setFixedHeight(400)

        self.vb.setMouseMode(pg.ViewBox.RectMode)
        self.img = pg.ImageItem()
        self.img.translate(-0.5, -0.5)
        self.vb.addItem(self.img)
        self.vb.setAspectLocked(True)
        imageWidget.setAspectLocked(True)
        self.hist = pg.HistogramLUTItem(image=self.img)
        self.hist.gradient.loadPreset('thermal')
# 'thermal', 'flame', 'yellowy', 'bipolar', 'spectrum', 'cyclic', 'greyclip', 'grey'
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
        self.pixelTime = float(self.pixelTimeEdit.text()) / 10**3  # segs

        self.Napd = int(np.round(apdrate * self.pixelTime))
#        self.initialPosition = np.array(
#                        self.initialPositionEdit.text().split(' '))
        self.initialPosition = (float(self.xLabel.text()), float(self.yLabel.text()),
              float(self.zLabel.text()))



        self.pixelSize = self.scanRange/self.numberofPixels

        self.pixelSizeValue.setText('{}'.format(np.around(
                                        1000 * self.pixelSize, 2)))  # en nm

#        self.linetime = (1 / 100000)*float(self.pixelTimeEdit.text()) * float(
#                                        self.numberofPixelsEdit.text())
        self.linetime = self.pixelTime * self.numberofPixels

        print(self.linetime, "linetime")

        self.timeTotalLabel.setText("Tiempo total (s) = " + '{}'.format(np.around(
                         self.numberofPixels * self.linetime, 2)))

        size = (self.numberofPixels, self.numberofPixels)

        if self.scanMode.currentText() == "step scan":
            self.barridos()
        if self.scanMode.currentText() == "ramp scan":
            self.rampas()

        self.inputImage = 1 * np.random.normal(size=size)
        self.blankImage = np.zeros(size)
        self.image = self.blankImage
#        self.i = 0
        self.dy = 0

# cosas para el save image
    def saveimage(self):
        """ la idea es que escanee la zona deseada (desde cero)
y guarde la imagen"""
        if self.saveimageButton.isChecked():
            self.save = True
            self.liveviewButton.setChecked(False)
            self.channelsOpen()
            self.movetoStart()
            self.saveimageButton.setText('Abort')
            self.guarda = np.zeros((self.numberofPixels, self.numberofPixels))
            self.liveviewStart()

        else:
            self.save = False
            print("Abort")
            self.saveimageButton.setText('reintentar Scan and Stop')
            self.liveviewStop()

# This is the function triggered by pressing the liveview button
    def liveview(self):
        """ Image live view when not recording"""
        if self.liveviewButton.isChecked():
            self.save = False
            self.liveviewStart()

        else:
            self.liveviewStop()

    def liveviewStart(self):
        if self.scanMode.currentText() == "step scan":
            self.channelsOpen()
            self.viewtimer.start(self.linetime)
        if self.scanMode.currentText() == "ramp scan":
#            self.channelsOpen2()
            self.viewtimer.start(self.linetime)
        if self.scanMode.currentText() == "otro scan":
            print("elegri step o ramp scan")
            self.liveviewButton.setChecked(False)

    def liveviewStop(self):
        if self.save:
#            print("listo el pollo")
            self.saveimageButton.setChecked(False)
            self.saveimageButton.setText('Otro Scan and Stop')
            self.save = False


        self.liveviewButton.setChecked(False)
        self.viewtimer.stop()
        self.done()

# ---updateView -----------------
    def updateView(self):

        if self.scanMode.currentText() == "step scan":
            self.linea()
        if self.scanMode.currentText() == "ramp scan":
            self.linearampa()

        if self.step == 1:
            self.lineData = self.cuentas
            self.image[:, self.numberofPixels-1-(self.dy)] = self.lineData
        else:
            cuentas2 = np.split(self.cuentas, 2)
            self.lineData = cuentas2[0]  # self.inputImage[:, self.dy] 
            lineData2 = cuentas2[1]
            self.image[:, self.numberofPixels-1-(self.dy)] = self.lineData
            self.image[:, self.numberofPixels-2-(self.dy)] = lineData2

        self.img.setImage(self.image, autoLevels=False)

        if self.save:
            if self.dy < self.numberofPixels-self.step:
                self.dy = self.dy + self.step
            else:
                self.guardarimagen()

                self.saveimageButton.setText('Fin')  # ni se ve
                self.movetoStart()
                self.liveviewStop()

        else:
                    
            if self.dy < self.numberofPixels-self.step:
                self.dy = self.dy + self.step
            else:
#                self.dy = 0
                if self.Alancheck.isChecked():
                    self.guardarimagen()  # para guardar siempre (Alan idea)

                self.movetoStart()

# arma los barridos con los parametros dados
    def barridos(self):
        """
        self.cuentas = np.zeros((2 * self.numberofPixels))
        Samps = int(self.numberofPixels)

#       Barrido x
        startX = float(self.initialPosition[0])
        sizeX = self.scanRange + startX
        idax = makeRamp(startX, sizeX, Samps)
        vueltax = makeRamp(sizeX, startX, Samps)
        primSig = np.concatenate((idax, vueltax))
        self.barridox = primSig / convFactors['x']

#       Barrido y
        startY = float(self.initialPosition[1])
#        sizeY = self.scanRange
#        self.stepSize = self.dy * self.pixelSize / convFactors['y']
        iday = np.ones(Samps)*startY
        ida2y = np.ones(Samps) * (startY + self.pixelSize)
        secSig = np.concatenate((iday, ida2y))
        self.barridoy = secSig / convFactors['y']

#       Barrido z (se queda en la posicion inicial)
        startZ = float(self.initialPosition[2])
        self.barridoz = np.ones(len(self.barridox)) * startZ / convFactors['z']
#        """

#        """para hacerlo de a lineas y que no sea de 2 en 2:

        self.cuentas = np.zeros((self.numberofPixels))

#       Barrido x
        startX = float(self.initialPosition[0])
        sizeX = self.scanRange
        idax = makeRamp(startX, sizeX+startX, self.numberofPixels)
        primSig = np.append(0, idax)
        self.barridox = primSig / convFactors['x']

#       Barrido y
        startY = float(self.initialPosition[1])
        iday = np.ones(self.numberofPixels)*startY
        secSig = np.append(0, iday)
        self.barridoy = secSig / convFactors['y']

#       Barrido z (se queda en la posicion inicial)
        startZ = float(self.initialPosition[2])
        self.barridoz = np.ones(len(self.barridox)) * startZ / convFactors['z']
#        """


# manda las señales a las salidas analogicas y lee el apd
    def linea(self):
        """
        self.step = 2  # saltod e 2 en 2 frames por como arme el barrido
        tic = time.time()
        for i in range(2 * self.numberofPixels):
            tec = time.time()
            self.aotask.write(
             [self.barridox[i],
              self.barridoy[i] + (self.dy * self.pixelSize / convFactors['y']),
              self.barridoz[i]], auto_start=True)
            tac = time.time()
            APD = self.ditask.read(number_of_samples_per_channel=self.Napd)
#            self.ditask.wait_until_done()
            toc = time.time()
            aux = 0
            for c in range(self.Napd-1):
                if APD[c] < APD[c+1]:
                    aux = aux + 1
            self.cuentas[i] = aux + np.random.rand(1)[0]

        print("\n", "ditask posta", np.round(toc-tac, 4), "pixeltime = ", self.pixelTime)
        print("data posta", np.round(time.time() - tic, 4), "linetime = ", self.linetime)
        print(np.round(time.time() - tec, 4))
        print(self.Napd, "Napd", len(APD), "APD92\n")
#        """
#    """       para hacerlo de a lineas y que no sea de 2 en 2:
        self.step = 1
        tic = time.time()
        for i in range(self.numberofPixels):
            tec = time.time()
            self.aotask.write(
             [self.barridox[(i+1)*(-1)**self.dy],
              self.barridoy[(i+1)] + (self.dy * self.pixelSize / convFactors['y']),
              self.barridoz[i]], auto_start=True)
            tac = time.time()
            APD = self.ditask.read(number_of_samples_per_channel=self.Napd)
#            self.ditask.wait_until_done()
            toc = time.time()
            aux = 0
            for c in range(self.Napd-1):
                if APD[c] < APD[c+1]:
                    aux = aux + 1
            self.cuentas[i] = aux + np.random.rand(1)[0]

        print("\n", "ditask posta", np.round(toc-tac, 4), "pixeltime = ", self.pixelTime)
        print("data posta", np.round(time.time() - tic, 4), "linetime = ", self.linetime)
        print(np.round(time.time() - tec, 4))
        print(self.Napd, "Napd\n")
#    """

# se encarga de abrir todos los canales de la nidaq

    def channelsOpen(self):
        if self.ischannelopen:
            print("Ya estan abiertos los canales")  # para evitar el error
            #  en realidad podria no cerrarlos nunca. Para pensar.

        else:

            self.ischannelopen = True

            self.aotask = nidaqmx.Task('aotask')
            self.dotask = nidaqmx.Task('dotask')
            self.aitask = nidaqmx.Task('aitask')  # Ger
            self.ditask = nidaqmx.Task('ditask')  # Ger
    
            self.ditask.di_channels.add_di_chan(
                lines="Dev1/port0/line2",  # name_to_assign_to_lines='chan2.0',
                line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)

#            self.ditask.timing.cfg_samp_clk_timing(
#              rate=apdrate,
#              sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
#              samps_per_chan=self.Napd)

            self.ditask.timing.cfg_samp_clk_timing(  # quiero probar esto.
              rate=apdrate,
              sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
              samps_per_chan=10**8)


    #        # Tengo que hacer que dotask accione el/los shutters.

    #        self.dotask.do_channels.add_do_chan(  # se ocuparia del shutter
    #            lines="Dev1/port0/line6", name_to_assign_to_lines='chan6',
    #            line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)  # Ger
    
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
        if self.ischannelopen:
            print("Cierro todos los canales")  # para evitar el error
            self.aotask.stop()
            self.aotask.close()
            self.dotask.stop()
            self.dotask.close()
            self.aitask.stop()  # Ger
            self.aitask.close()  # Ger
            self.ditask.stop()  # Ger
            self.ditask.close()  # Ger
#            self.nidaq.reset_device()
#            self.finalizeDone.emit()
#            del NoseComoHacerloMejor
            self.ischannelopen = False
        else:
            print("llego hasta el done pero no tenia nada que cerrar")

# Se mueve a la posicion inicial de una manera agradable para el piezo
    def movetoStart(self):
#        self.inputImage = 1 * np.random.normal(
#                    size=(self.numberofPixels, self.numberofPixels))
        t = self.moveTime
        N = self.moveSamples

        tic = time.time()
        startY = float(self.initialPosition[1])
        maximoy = startY + ((self.dy+1) * self.pixelSize)
        volviendoy = np.linspace(maximoy, startY, N)
        volviendox = np.ones(len(volviendoy)) * float(self.initialPosition[0])
        volviendoz = np.ones(len(volviendoy)) * float(self.initialPosition[2])
        for i in range(len(volviendoy)):
            self.aotask.write(
                 [volviendox[i] / convFactors['x'],
                  volviendoy[i] / convFactors['y'],
                  volviendoz[i] / convFactors['z']], auto_start=True)
            time.sleep(t / N)
        print(t, "vs" , np.round(time.time() - tic, 3))
        self.dy = 0

    def guardarimagen(self):
        print("\n Hipoteticamente Guardo la imagen\n")

#        filepath = "C:/Users/Santiago/Desktop/Germán Tesis de lic/Winpython (3.5.2 para tormenta)/WinPython-64bit-3.5.2.2/notebooks/Guardando tiff/"
#        timestr = time.strftime("%Y%m%d-%H%M%S")
#        name = str(filepath + "image-" + timestr + ".tiff")  # nombre con la fecha -hora
#        guardado = Image.fromarray(self.guarda)
#        guardado.save(name)


# --------------------------------------------------------------------------
# ---Move----------------------------------------

    def move(self, axis, dist):
        """moves the position along the axis specified a distance dist."""
        self.channelsOpen()
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

        factors = np.array([convFactors['x'], convFactors['y'],
                           convFactors['z']])[:, np.newaxis]
        fullSignal = fullPos/factors
        toc = time.time()

        for i in range(self.nSamples):
            self.aotask.write(fullSignal, auto_start=True)
            time.sleep( t / N)

        print("se mueve en", np.round(time.time() - toc, 3), "segs")

        # update position text
        newPos = fullPos[self.activeChannels.index(axis)][-1]
#        newText = "<strong>" + axis + " = {0:.2f} µm</strong>".format(newPos)
        newText = "{}".format(newPos)
        getattr(self, axis + "Label").setText(newText)
        self.paramChanged()

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
            self.zStepEdit.setStyleSheet("{ background-color: }")
        if self.initialPosition[2] == 0:  # para no ira z negativo
            self.zDownButton.setStyleSheet(
                "QPushButton { background-color: red; }"
                "QPushButton:pressed { background-color: blue; }")
            self.zDownButton.setEnabled(False)
# ---goto

    def goto(self):
        self.channelsOpen()
        print("arranco en",float(self.xLabel.text()), float(self.yLabel.text()),
              float(self.zLabel.text()))

        self.moveto(float(self.xgotoLabel.text()),
                    float(self.ygotoLabel.text()),
                    float(self.zgotoLabel.text()))

        print("termino en", float(self.xLabel.text()), float(self.yLabel.text()),
              float(self.zLabel.text()))

        self.paramChanged()

    def moveto(self, x, y, z):
        """moves the position along the axis to a specified point."""
        t = self.moveTime * 3
        N = self.moveSamples * 3
        # read initial position for all channels
        texts = [getattr(self, ax + "Label").text()
                 for ax in self.activeChannels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]

        rampx = makeRamp(float(initPos[0]), x, self.nSamples)
        rampy = makeRamp(float(initPos[1]), y, self.nSamples)
        rampz = makeRamp(float(initPos[2]), z, self.nSamples)

        tuc = time.time()
        for i in range(self.nSamples):
            self.aotask.write([rampx[i] / convFactors['x'],
                               rampy[i] / convFactors['y'],
                               rampz[i] / convFactors['z']], auto_start=True)
            time.sleep(t / N)

        print("se mueve todo en", np.round(time.time()-tuc, 3),"segs")

        self.xLabel.setText("{}".format(np.around(float(rampx[-1]), 2)))
        self.yLabel.setText("{}".format(np.around(float(rampy[-1]), 2)))
        self.zLabel.setText("{}".format(np.around(float(rampz[-1]), 2)))

# --- Shutter time --------------------------

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
        self.channelsOpen()
        print("abre shutter", p)
        shutters = ["red", "green", "otro"]
        for i in range(3):
            if p == shutters[i]:
                self.shuttersignal[i] = self.shuttersignal[i] + 5
#        self.dotask.write(self.shuttersignal, auto_start=True)
        print(self.shuttersignal)

    def closeShutter(self, p):
        self.channelsOpen()
        print("cierra shutter", p)
        shutters = ["red", "green", "otro"]
        for i in range(3):
            if p == shutters[i]:
                self.shuttersignal[i] = self.shuttersignal[i] - 5
#        self.dotask.write(self.shuttersignal, auto_start=True)
        print(self.shuttersignal)

#---END PROGRAM------------------------------------------------

# hacer el barrido con rampas (hay que cambiar tambien el channelsOpen())

    def channelsOpen2(self):

            self.aotask = nidaqmx.Task('aotask')
            self.dotask = nidaqmx.Task('dotask')
            self.aitask = nidaqmx.Task('aitask')  # Ger
            self.ditask = nidaqmx.Task('ditask')  # Ger
    
            self.ditask.di_channels.add_di_chan(
                lines="Dev1/port0/line2",  # name_to_assign_to_lines='chan2.0',
                line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
    
            self.ditask.timing.cfg_samp_clk_timing(
              rate=apdrate,
              sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
              samps_per_chan=10**8)
    
    #        # Tengo que hacer que dotask accione el/los shutters.
    
    #        self.dotask.do_channels.add_do_chan(  # se ocuparia del shutter
    #            lines="Dev1/port0/line6", name_to_assign_to_lines='chan6',
    #            line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)  # Ger
    
            self.channelOrder = ['x', 'y', 'z']
            AOchans = [0, 1, 2]
            # Following loop creates the voltage channels
            for n in range(len(AOchans)):
                self.aotask.ao_channels.add_ao_voltage_chan(
                    physical_channel='Dev1/ao%s' % AOchans[n],
                    name_to_assign_to_channel='chan_%s' % self.channelOrder[n],
                    min_val=minVolt[self.channelOrder[n]],
                    max_val=maxVolt[self.channelOrder[n]])

#            rate = (1 / self.pixelTime)  # *self.step
            self.aotask.timing.cfg_samp_clk_timing(
                rate=(1 / self.pixelTime),
#                source=r'100kHzTimeBase',
                sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                samps_per_chan=(self.numberofPixels*2))
    #        self.aotask.in_stream.input_buf_size = len(self.barridox)

    def rampas(self):
#        """
        self.cuentas = np.zeros((2 * self.numberofPixels))
        Samps = self.numberofPixels
#       Barrido x
        startX = float(self.initialPosition[0])
        sizeX = self.scanRange + startX
        idax = makeRamp(startX, sizeX, Samps)
        vueltax = makeRamp (sizeX, startX, Samps)
        primSig = np.concatenate((idax, vueltax))
        self.barridox = primSig / convFactors['x']

#       Barrido y
        startY = float(self.initialPosition[1])
#        sizeY = self.scanRange
#        self.stepSize = self.dy * self.pixelSize / convFactors['y']
        iday = np.ones(Samps)*startY
        ida2y = np.ones(Samps) * (startY + self.pixelSize)
        secSig = np.concatenate((iday, ida2y))
        self.barridoy = secSig / convFactors['y']

#       Barrido z (se queda en la posicion inicial)
        startZ = float(self.initialPosition[2])
        self.barridoz = np.ones(len(self.barridox)) * startZ / convFactors['z']
        self.channelsOpen2()
#        """

    """       para hacerlo de a lineas y que no sea de 2 en 2:

        self.cuentas = np.zeros((self.numberofPixels))
#       Barrido x
        startX = float(self.initialPosition[0])
        sizeX = self.scanRange
        idax = makeRamp(startX, sizeX, self.numberofPixels)
        self.barridox = idax / convFactors['x']

#       Barrido y
        startY = float(self.initialPosition[1])
#        sizeY = self.scanRange
#        self.stepSize = self.dy * self.pixelSize / convFactors['y']
        iday = np.ones(self.numberofPixels)*startY
        self.barridoy = iday / convFactors['y']

#       Barrido z (se queda en la posicion inicial)
        startZ = float(self.initialPosition[2])
        self.barridoz = np.ones(len(self.barridox)) * startZ / convFactors['z']

    def vueltaX(self):
        startX = float(self.initialPosition[0])
        sizeX = self.scanRange
        vueltax = np.linspace(sizeX, startX, self.moveSamples)
        self.aotask.write(
         [vueltax,
          self.barridoy + (self.dy * self.pixelSize / convFactors['y']),
          self.barridoz], auto_start=True)

#    """


# manda las señales a las salidas analogicas y lee el apd
    def linearampa(self):
#        """
        self.step = 2

        tic = time.time()
        self.aotask.write(
         [self.barridox,
          self.barridoy + (self.dy * self.pixelSize / convFactors['y']),
          self.barridoz], auto_start=True)
        tac = time.time()
        APDtodo = self.ditask.read(self.Napd * 2*self.numberofPixels)
#        self.aotask.wait_until_done()
#        self.ditask.wait_until_done()
        toc = time.time()

        APD = np.split(np.array(APDtodo), 2*self.numberofPixels)
        for j in range(2*self.numberofPixels):
            aux = 0
            for c in range(2*self.numberofPixels * self.Napd -1):
                if APD[j][c] < APD[j][c+1]:
                    aux = aux + 1
            self.cuentas[j] = aux + np.random.rand(1)[0]

        print("\n", "ditask posta", np.round(toc-tac, 4), "pixeltime = ", self.pixelTime)
        print("data posta", np.round(time.time() - tic, 4), "linetime = ", self.linetime)
        print(self.Napd, "Napd\n")
#        """

    """       para hacerlo de a lineas y que no sea de 2 en 2:
        self.step = 1
        tic = time.time()
        self.aotask.write(
         [self.barridox,
          self.barridoy + (self.dy * self.pixelSize / convFactors['y']),
          self.barridoz], auto_start=True)
        tac = time.time()
        APDtodo = self.ditask.read(self.Napd * self.numberofPixels)
        self.aotask.wait_until_done()
#        self.ditask.wait_until_done()
        toc = time.time()

        APD = np.split(APDtodo, self.numberofPixels)
        for j in range(self.numberofPixels):
            aux = 0
            for c in range(self.Napd-1):
                if APD[j][c] < APD[j][c+1]:
                    aux = aux + 1
            self.cuentas[j] = aux + np.random.rand(1)[0]
        self.vueltaX()

        print("\n", "ditask posta", np.round(toc-tac, 4), "pixeltime = ", self.pixelTime)
        print("data posta", np.round(time.time() - tic, 4), "linetime = ", self.linetime)
        print(self.Napd, "Napd\n")
#    """

#if __name__ == '__main__':

app = QtGui.QApplication([])
win = ScanWidget(device)
win.show()

app.exec_()

#ScanWidget()
