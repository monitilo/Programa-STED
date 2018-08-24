
""" Programa un poco mas completo para correr el liveScan CON LA NIDAQ
incluye positioner para moverse por la muestra"""

import numpy as np
import time
#import scipy.ndimage as ndi
#import matplotlib.pyplot as plt

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
#from pyqtgraph.dockarea import Dock, DockArea
#import pyqtgraph.ptime as ptime

#from PIL import Image

import re

import nidaqmx

device = nidaqmx.system.System.local().devices['Dev1']
convFactors = {'x': 25, 'y': 25, 'z': 1.683}
# la calibracion en x,y es 1 µm = 40 mV;1/0.040 = 25  (espejos galvanometricos)
# en z es 1.68 um = 1 V ==> 1 um = 0.59V; 1/0.59 ~=1.683  (platina nanomax)
minVolt = {'x': -10, 'y': -10, 'z': 0}
maxVolt = {'x': 10, 'y': 10, 'z': 10}

apdrate = 20*10**6


def makeRamp(start, end, samples):
    return np.linspace(start, end, num=samples)


#  el espanglish is trong in this programa
class ScanWidget(QtGui.QFrame):

    def keyPressEvent(self, e):

        if e.key() == QtCore.Qt.Key_Escape:
            self.close()
            self.liveviewStop()

    def __init__(self, device, *args, **kwargs):  # agregue device

        super().__init__(*args, **kwargs)

        self.nidaq = device  # esto tiene que ir para la NiDaq

# ---  El armado de la interfaz grafica.

        # Parameters for smooth moving (to no shake hard the piezo)
        self.moveTime = 0.2  # total time to move(s)
        self.moveSamples = 100  # samples to move
        self.moveRate = self.moveSamples / self.moveTime

        # Parameters for the ramp (driving signal for the different channels)
        self.rampTime = 0.1  # Time for each ramp in s
        self.sampleRate = 10**5
        self.nSamples = int(self.rampTime * self.sampleRate)

        # this positionner to access the analog output channels
        self.activeChannels = ["x", "y", "z"]
        self.AOchans = [0, 1, 2]
        self.DOchans = [0, 1, 2]

        # La ventana con el grafico

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
        self.scanModes = ['ramp scan', 'step scan', 'otro scan']
        self.scanMode.addItems(self.scanModes)
        self.scanMode.currentIndexChanged.connect(self.paramChanged)

        # para que guarde todo (trazas de Alan)

        self.Alancheck = QtGui.QRadioButton('Alan continous save')
        self.Alancheck.setChecked(False)

    # Para alternar entre pasos de a 1 y de a 2 (en el programa final se va)

        self.stepcheck = QtGui.QCheckBox('hacerlo de a 2')
#        self.stepcheck.clicked.connect(self.steptype)

        # La señal para los shutters que se usen (se pueden poner mas, o menos)
        self.shuttersignal = [False, False, False]
        # np.array([0, 0, 0],dtype=bool)

        # botones para shutters (por ahora no hacen nada)
        self.shutterredbutton = QtGui.QCheckBox('shutter 640')
        self.shutterredbutton.clicked.connect(self.shutterred)

        self.shuttergreenbutton = QtGui.QCheckBox('shutter 532')
        self.shuttergreenbutton.clicked.connect(self.shuttergreen)

        self.shutterotrobutton = QtGui.QCheckBox('shutter otro')
        self.shutterotrobutton.clicked.connect(self.shutterotro)

#       This boolean is set to True when open the nidaq channels
        self.ischannelopen = False
        self.ischannelopen2 = False

        # Scanning parameters

#        self.initialPositionLabel = QtGui.QLabel('Initial Pos[x0 y0 z0] (µm)')
#        self.initialPositionEdit = QtGui.QLineEdit('0 0 0')
        self.scanRangeLabel = QtGui.QLabel('Scan range (µm)')
        self.scanRangeEdit = QtGui.QLineEdit('10')
        self.pixelTimeLabel = QtGui.QLabel('Pixel time (µs)')
        self.pixelTimeEdit = QtGui.QLineEdit('500')
        self.numberofPixelsLabel = QtGui.QLabel('Number of pixels')
        self.numberofPixelsEdit = QtGui.QLineEdit('100')
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
#        subgrid.addWidget(self.stepcheck, 11, 2)
        subgrid.addWidget(self.Alancheck, 13, 1)
        subgrid.addWidget(self.timeTotalLabel, 14, 1)
#        subgrid.addWidget(self.timeTotalValue, 14, 1)
        subgrid.addWidget(self.saveimageButton, 15, 1)

# ---  Positioner part ---------------------------------
        # Axes control
        self.xLabel = QtGui.QLabel('0.0')
        self.xLabel.setTextFormat(QtCore.Qt.RichText)
        self.xUpButton = QtGui.QPushButton("+")
        self.xUpButton.pressed.connect(self.xMoveUp)
        self.xDownButton = QtGui.QPushButton("-")
        self.xDownButton.pressed.connect(self.xMoveDown)
        self.xStepEdit = QtGui.QLineEdit("1")
        self.xStepUnit = QtGui.QLabel(" µm")

        self.yLabel = QtGui.QLabel('0.0')
        self.yLabel.setTextFormat(QtCore.Qt.RichText)
        self.yUpButton = QtGui.QPushButton("+")
        self.yUpButton.pressed.connect(self.yMoveUp)
        self.yDownButton = QtGui.QPushButton("-")
        self.yDownButton.pressed.connect(self.yMoveDown)
        self.yStepEdit = QtGui.QLineEdit("1")
        self.yStepUnit = QtGui.QLabel(" µm")

        self.zLabel = QtGui.QLabel('0.0')
        self.zLabel.setTextFormat(QtCore.Qt.RichText)
        self.zUpButton = QtGui.QPushButton("+")
        self.zUpButton.pressed.connect(self.zMoveUp)
        self.zDownButton = QtGui.QPushButton("-")
        self.zDownButton.pressed.connect(self.zMoveDown)
        self.zStepEdit = QtGui.QLineEdit("1")
        self.zStepUnit = QtGui.QLabel(" µm")

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
# 'thermal', 'flame', 'yellowy', 'bipolar',
# 'spectrum', 'cyclic', 'greyclip', 'grey'
        self.hist.vb.setLimits(yMin=0, yMax=66000)
        for tick in self.hist.gradient.ticks:
            tick.hide()
        imageWidget.addItem(self.hist, row=1, col=2)

        self.viewtimer = QtCore.QTimer()
        self.viewtimer.timeout.connect(self.updateView)

    def paramChanged(self):

        self.scanRange = float(self.scanRangeEdit.text())
        self.numberofPixels = int(self.numberofPixelsEdit.text())
        self.pixelTime = float(self.pixelTimeEdit.text()) / 10**6  # µs to segs

        self.Napd = int(np.round(apdrate * self.pixelTime))

        self.initialPosition = (float(self.xLabel.text()),
                                float(self.yLabel.text()),
                                float(self.zLabel.text()))

        self.pixelSize = self.scanRange / self.numberofPixels

        self.pixelSizeValue.setText('{}'.format(np.around(
                                        1000 * self.pixelSize, 2)))  # µm to nm

        self.linetime = self.pixelTime * self.numberofPixels

        print(self.linetime, "linetime")

        self.timeTotalLabel.setText("Tiempo total (s) ="+'{}'.format(np.around(
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


# This is the function triggered by pressing the liveview button
    def liveview(self):
        """ Image live view when not recording"""
        if self.liveviewButton.isChecked():
            self.save = False
            self.liveviewStart()

        else:
            self.liveviewStop()

# cosas para guardar un solo escaneo, con el otro boton
    def saveimage(self):
        """ la idea es que escanee la zona deseada (desde cero)
y guarde la imagen en .tiff"""
        if self.saveimageButton.isChecked():
            self.save = True
            self.liveviewButton.setChecked(False)
            self.channelsOpen()
            self.movetoStart()
            self.saveimageButton.setText('Abort')
            self.liveviewStart()

        else:
            self.save = False
            print("Abort")
            self.saveimageButton.setText('reintentar Scan and Stop')
            self.liveviewStop()

    def liveviewStart(self):
        if self.scanMode.currentText() == "step scan":
            self.channelsOpen()
            print("step scan")
            self.viewtimer.start(self.linetime)
        if self.scanMode.currentText() == "ramp scan":
            self.channelsOpen2()
            print("ramp scan")
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

        cuentas2 = np.split(self.cuentas, 2)
        self.lineData = cuentas2[0]  # self.inputImage[:, self.dy]
        lineData2 = cuentas2[1]
        self.image[:, self.numberofPixels-1-(self.dy)] = self.lineData
        self.image[:, self.numberofPixels-2-(self.dy)] = lineData2

        self.img.setImage(self.image, autoLevels=False)

        if self.save:
            if self.dy < self.numberofPixels-2:
                self.dy = self.dy + 2
            else:
                self.guardarimagen()

                self.saveimageButton.setText('Fin')  # ni se ve
                self.movetoStart()
                self.liveviewStop()

        else:

            if self.dy < self.numberofPixels-2:
                self.dy = self.dy + 2
            else:

                if self.Alancheck.isChecked():
                    self.guardarimagen()  # para guardar siempre (Alan idea)
                self.movetoStart()

# arma los barridos con los parametros dados
    def barridos(self):

        # va y vuelve en un solo paso, ==> pasa de 2 en 2
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
#            sizeY = self.scanRange
#            self.stepSize = self.dy * self.pixelSize / convFactors['y']
        iday = np.ones(Samps)*startY
        ida2y = np.ones(Samps) * (startY + self.pixelSize)
        secSig = np.concatenate((iday, ida2y))
        self.barridoy = secSig / convFactors['y']

        #       Barrido z (se queda en la posicion inicial)
        startZ = float(self.initialPosition[2])
        self.barridoz = np.ones(len(self.barridox))*startZ/convFactors['z']


# manda las señales a las salidas analogicas y lee el apd
    def linea(self):

        Pasoy = (self.dy * self.pixelSize / convFactors['y'])
        self.citask.stop()

        # Para hacerlo de 2 en 2
        tic = time.time()
        APD = np.zeros((2 * self.numberofPixels))
        for i in range(2 * self.numberofPixels):
            tec = time.time()
            self.aotask.write(
               [self.barridox[i],
                self.barridoy[i] + Pasoy,
                self.barridoz[i]], auto_start=True)
            tac = time.time()
            medida = self.citask.read(number_of_samples_per_channel=self.Napd)
            APD[i] = medida[-1]
  #            self.ditask.wait_until_done()
            toc = time.time()
#                aux = 0
#                for c in range(self.Napd-1):
#                    if APD[c] < APD[c+1]:
#                        aux = aux + 1
#                    self.cuentas[i] = aux + np.random.rand(1)[0]
            self.cuentas[i] = APD[i] - APD[i-1]


        print("\n", "ditask posta", np.round(toc-tac, 5), "pixeltime = ", self.pixelTime)
        print("data posta", np.round(time.time() - tic, 5), "linetime = ", self.linetime)
        print(np.round(time.time() - tec, 5))
        print(self.Napd, "Napd")  # , len(APD), "APD\n")
#        """


# se encarga de abrir todos los canales de la nidaq, para el barrido de a pasos

    def channelsOpen(self):
        if self.ischannelopen2:
            self.done()

        if self.ischannelopen:
            print("Ya estan abiertos los canales")  # para evitar el error

        else:

            self.ischannelopen = True

            self.aotask = nidaqmx.Task('aotask')
            self.dotask = nidaqmx.Task('dotask')
#            self.aitask = nidaqmx.Task('aitask')  # Ger
#            self.ditask = nidaqmx.Task('ditask')  # Ger
            self.citask = nidaqmx.Task('citask')

#            self.ditask.di_channels.add_di_chan(
#                lines="Dev1/port0/line2",
#                line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)

#            self.ditask.timing.cfg_samp_clk_timing(
#              rate=apdrate,
#              sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
#              samps_per_chan=self.Napd)

#            self.ditask.timing.cfg_samp_clk_timing(  # quiero probar esto.
#              rate=apdrate,
#              sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
#              samps_per_chan=10**8)  # buffer?, funciona mas rapido

            self.citask.ci_channels.add_ci_count_edges_chan(counter='Dev1/ctr0',
                                name_to_assign_to_channel=u'conter',
                                initial_count=0)

            self.citask.timing.cfg_samp_clk_timing(
              rate=apdrate, sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
              source='20MHzTimebase',
              samps_per_chan = self.Napd * 2*self.numberofPixels)

            # Tengo que hacer que dotask accione el/los shutters.
            for n in range(len(self.DOchans)):
                self.dotask.do_channels.add_do_chan(  # se ocuparia del shutter
                  lines="Dev1/port0/line%s" % self.DOchans[n],
                  name_to_assign_to_lines='DOchan_%s' % self.activeChannels[n],
                  line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)

            # Following loop creates the voltage channels
            for n in range(len(self.AOchans)):
                self.aotask.ao_channels.add_ao_voltage_chan(
                    physical_channel='Dev1/ao%s' % self.AOchans[n],
                    name_to_assign_to_channel='AOchan_%s' % self.activeChannels[n],
                    min_val=minVolt[self.activeChannels[n]],
                    max_val=maxVolt[self.activeChannels[n]])

    """ idea para separar cada canal segun el caso
    def closedi(self):  # digital in channel
#        if self.ischannelopen:
          print("Cierro digital in")
          self.ditask.stop()
          self.ditask.close()

    def closedo(self):  # digital out channel
#        if self.ischannelopen:
          print("Cierro digital out")  # para evitar el error
          self.dotask.stop()
          self.dotask.close()

    def closeai(self):  # analog in channel
#        if self.ischannelopen:
          print("Cierro analogin")  # para evitar el error
          self.aitask.stop()
          self.aitask.close()

    def closeao(self):  # analog out channel
#        if self.ischannelopen:
          print("Cierro analog in")  # para evitar el error
          self.aotask.stop()
          self.aotask.close()
          """
    def done(self):
        if self.ischannelopen == True or self.ischannelopen2 == True:
            print("Cierro todos los canales")  # para evitar el error
#            self.ditask.stop()
#            self.ditask.close()
            self.dotask.stop()
            self.dotask.close()
#            self.aitask.stop()
#            self.aitask.close()
            self.aotask.stop()
            self.aotask.close()
            self.citask.stop()
            self.citask.close()
            """            
            self.closedi()
            self.closedo()
            self.closeai()
            self.closeao()
#            """
            self.ischannelopen = False
            self.ischannelopen2 = False
        else:
            print("llego hasta el done pero no tenia nada que cerrar")

# Se mueve a la posicion inicial de una manera agradable para el piezo
    def movetoStart(self):
        if self.scanMode.currentText() == "step scan":
            self.movetoStartStep()
        if self.scanMode.currentText() == "ramp scan":
            self.movetoStartRamp()

    def movetoStartStep(self):
        self.aotask.stop()
        t = self.moveTime
        N = self.moveSamples

        tic = time.time()
        startY = float(self.initialPosition[1])
        maximoy = startY + ((self.dy) * self.pixelSize)
        volviendoy = np.linspace(maximoy, startY, N)
        volviendox = np.ones(len(volviendoy)) * float(self.initialPosition[0])
        volviendoz = np.ones(len(volviendoy)) * float(self.initialPosition[2])
        for i in range(len(volviendoy)):
            self.aotask.write(np.array([volviendox[i] / convFactors['x'],
                  volviendoy[i] / convFactors['y'],
                  volviendoz[i] / convFactors['z']]), auto_start=True)
#            time.sleep(t / N)
        print(t, "vs", np.round(time.time() - tic, 5))
        self.dy = 0

    def guardarimagen(self):
        print("\n Hipoteticamente Guardo la imagen\n")

#        filepath = "C:/Users/Santiago/Desktop/Germán Tesis de lic/Winpython (3.5.2 para tormenta)/WinPython-64bit-3.5.2.2/notebooks/Guardando tiff/"
#        timestr = time.strftime("%Y%m%d-%H%M%S")
#        name = str(filepath + "image-" + timestr + ".tiff")  # nombre con la fecha -hora
#        guardado = Image.fromarray(self.image)
#        guardado.save(name)


# ---Move----------------------------------------
    """
    def move(self):
        if self.scanMode.currentText() == "step scan":
            self.moveStep()
        if self.scanMode.currentText() == "ramp scan":
            self.moveRamp()
    """
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
        fullPos = np.repeat(initPos, N, axis=1)

        # make position ramp for moving axis
        ramp = makeRamp(0, dist, N)
        fullPos[self.activeChannels.index(axis)] += ramp

        factors = np.array([convFactors['x'], convFactors['y'],
                           convFactors['z']])[:, np.newaxis]
        fullSignal = fullPos/factors
        toc = time.time()

        for i in range(N):
            self.aotask.write(fullSignal[:, i], auto_start=True)
            time.sleep(t / N)

        print("se mueve en", np.round(time.time() - toc, 4), "segs")

        # update position text
        newPos = fullPos[self.activeChannels.index(axis)][-1]
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
    """
    def moveto(self, x, y, z):
        if self.scanMode.currentText() == "step scan":
            self.movetoStep(x, y, z)
        if self.scanMode.currentText() == "ramp scan":
            self.movetoRamp(x, y, z)
    """
    def moveto(self, x, y, z):
        """moves the position along the axis to a specified point."""
        self.channelsOpen()
        t = self.moveTime * 2
        N = self.moveSamples

        # read initial position for all channels
        texts = [getattr(self, ax + "Label").text()
                 for ax in self.activeChannels]
        initPos = [re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", t)[0] for t in texts]

        rampx = makeRamp(float(initPos[0]), x, N)
        rampy = makeRamp(float(initPos[1]), y, N)
        rampz = makeRamp(float(initPos[2]), z, N)

        tuc = time.time()
        for i in range(N):
            self.aotask.write([rampx[i] / convFactors['x'],
                               rampy[i] / convFactors['y'],
                               rampz[i] / convFactors['z']], auto_start=True)
            time.sleep(t / N)

        print("se mueve todo en", np.round(time.time()-tuc, 4), "segs")

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
#        self.opendo()
        print("abre shutter", p)
        shutters = ["red", "green", "otro"]
        for i in range(3):
            if p == shutters[i]:
                self.shuttersignal[i] = True
#        self.dotask.write(self.shuttersignal, auto_start=True)
        print(self.shuttersignal)

    def closeShutter(self, p):
        self.channelsOpen()
#        self.closedo()  # NO, no tengo que cerrarlo el dotask.
        print("cierra shutter", p)
        shutters = ["red", "green", "otro"]
        for i in range(3):
            if p == shutters[i]:
                self.shuttersignal[i] = False
#        self.dotask.write(self.shuttersignal, auto_start=True)
        print(self.shuttersignal)

# ---pasamos a las rampas------------------------------------------------
# hacer el barrido con rampas (hay que cambiar tambien el channelsOpen())

    def channelsOpen2(self):
        if self.ischannelopen:
            self.done()

        if self.ischannelopen2:
            print("ya esta abierto el channel2 (rampas)")

        else:

            self.aotask = nidaqmx.Task('aotask')
            self.dotask = nidaqmx.Task('dotask')
#            self.aitask = nidaqmx.Task('aitask')  # Ger
#            self.ditask = nidaqmx.Task('ditask')  # Ger
            self.citask = nidaqmx.Task('citask')

#            self.ditask.di_channels.add_di_chan(
#                lines="Dev1/port0/line2",  # name_to_assign_to_lines='chan2.0',
#                line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
#
#            self.ditask.timing.cfg_samp_clk_timing(
#              rate=apdrate,
#              sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
#              samps_per_chan=10**8)
            self.citask.ci_channels.add_ci_count_edges_chan(counter='Dev1/ctr0',
                                name_to_assign_to_channel=u'conter',
                                initial_count=0)

            self.citask.timing.cfg_samp_clk_timing(
              rate=apdrate, sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
              source='20MHzTimebase',
              samps_per_chan = self.Napd * 2 * self.numberofPixels)

    #        # Tengo que hacer que dotask accione el/los shutters.

    #        self.dotask.do_channels.add_do_chan(  # se ocuparia del shutter
    #            lines="Dev1/port0/line6", name_to_assign_to_lines='chan6',
    #            line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)

            # Following loop creates the voltage channels
            for n in range(len(self.AOchans)):
                self.aotask.ao_channels.add_ao_voltage_chan(
                    physical_channel='Dev1/ao%s' % self.AOchans[n],
                    name_to_assign_to_channel='chan_%s' % self.activeChannels[n],
                    min_val=minVolt[self.activeChannels[n]],
                    max_val=maxVolt[self.activeChannels[n]])

            self.aotask.timing.cfg_samp_clk_timing(
                rate=(1 / self.pixelTime),
#                source=r'100kHzTimeBase',
                sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                samps_per_chan=int(2 * self.numberofPixels))

    #        self.aotask.in_stream.input_buf_size = len(self.barridox)
            self.ischannelopen2 = True

    def rampas(self):

        # rampas de 2 en 2
        self.cuentas = np.zeros((2 * self.numberofPixels))
        Samps = self.numberofPixels
#                   Barrido x
        startX = float(self.initialPosition[0])
        sizeX = self.scanRange + startX
        idax = makeRamp(startX, sizeX, Samps)
        vueltax = makeRamp(sizeX, startX, Samps)
        primSig = np.concatenate((idax, vueltax))
        self.barridox = primSig / convFactors['x']

        #       Barrido y
        startY = float(self.initialPosition[1])
#            sizeY = self.scanRange
#            self.stepSize = self.dy * self.pixelSize / convFactors['y']
        iday = np.ones(Samps)*startY
        ida2y = np.ones(Samps) * (startY + self.pixelSize)
        secSig = np.concatenate((iday, ida2y))
        self.barridoy = secSig / convFactors['y']

        #       Barrido z (se queda en la posicion inicial)
        startZ = float(self.initialPosition[2])
        self.barridoz = np.ones(len(self.barridox)) * startZ / convFactors['z']
        self.channelsOpen2()
        #        """

# manda las señales a las salidas analogicas y lee el apd
    def linearampa(self):
        tic = time.time()
        self.aotask.stop()
#        self.done()
#        self.channelsOpen2()

        # Para hacerlo de 2 en 2:
        self.aotask.write(
           np.array([self.barridox,
            self.barridoy + (self.dy * self.pixelSize / convFactors['y']),
            self.barridoz]), auto_start=True)
        tac = time.time()
        APDtodo = self.citask.read(self.Napd * 2*self.numberofPixels)
        toc = time.time()
        self.cuentas[0] = APDtodo[self.Napd - 1]
        for j in range(1, 2*self.numberofPixels-2):
            self.cuentas[j] = APDtodo[((j+1)*self.Napd)-1] - APDtodo[((j)*self.Napd)-1]


        print("\n", "ditask posta", np.round(toc-tac, 5), "pixeltime = ", self.pixelTime)
        print("data posta", np.round(time.time() - tic, 5), "linetime = ", self.linetime)
        print(self.Napd, "Napd\n")

    def movetoStartRamp(self):
#        self.channelsOpen()
        self.done()
        N = self.moveSamples

        # Following loop creates the voltage channels
        with nidaqmx.Task("aotaskramp") as aotaskramp:
            for n in range(len(self.AOchans)):
                aotaskramp.ao_channels.add_ao_voltage_chan(
                    physical_channel='Dev1/ao%s' % self.AOchans[n],
                    name_to_assign_to_channel='chan_%s' % self.activeChannels[n],
                    min_val=minVolt[self.activeChannels[n]],
                    max_val=maxVolt[self.activeChannels[n]])
    
            aotaskramp.timing.cfg_samp_clk_timing(
                rate=(self.moveRate),
                sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                samps_per_chan=N)
    
            tic = time.time()
            startY = float(self.initialPosition[1])
            maximoy = startY + ((self.dy) * self.pixelSize)
            volviendoy = np.linspace(maximoy, startY, N)
            volviendox = np.ones(len(volviendoy)) * float(self.initialPosition[0])
            volviendoz = np.ones(len(volviendoy)) * float(self.initialPosition[2])
    
            aotaskramp.write(np.array(
                 [volviendox / convFactors['x'],
                  volviendoy / convFactors['y'],
                  volviendoz / convFactors['z']]), auto_start=True)
            aotaskramp.wait_until_done()
            print(np.round(time.time() - tic, 5))
            self.dy = 0

            aotaskramp.stop()
#            aotaskramp.close()

        self.channelsOpen2()

#if __name__ == '__main__':

app = QtGui.QApplication([])
win = ScanWidget(device)
win.show()

app.exec_()

#ScanWidget()
