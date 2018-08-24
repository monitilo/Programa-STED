
import numpy as np
import time
import scipy.ndimage as ndi
import matplotlib.pyplot as plt

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.dockarea import Dock, DockArea
import pyqtgraph.ptime as ptime

from PIL import Image


import nidaqmx

device = nidaqmx.system.System.local().devices['Dev1']

convFactors = {'x': 25, 'y': 25, 'z': 1.683}
# la calibracion es 1 µm = 40 mV; la de Z no la medi
# en z, 0.17 µm = 0.1 V  ==> 1 µm = 0.58 V
# 1.68 um = 1 V ==> 1 um = 0.59V
minVolt = {'x': -10, 'y': -10, 'z': 0}
maxVolt = {'x': 10, 'y': 10, 'z': 10}


def makeRamp(start, end, samples):
    return np.linspace(start, end, num=samples)


class ScanWidget(QtGui.QFrame):
    def steptype(self):
        if self.stepcheck.isChecked():
            self.step = True
            print("step es True", self.step == 1)
        else:
            self.step = False
            print("step es False", self.step == 1)

    def keyPressEvent(self, e):

        if e.key() == QtCore.Qt.Key_Escape:
            self.close()
            self.liveviewStop()

    def __init__(self, device, *args, **kwargs):  # agregue device

        super().__init__(*args, **kwargs)

        self.nidaq = device  # esto tiene que ir

        imageWidget = pg.GraphicsLayoutWidget()
        self.vb = imageWidget.addViewBox(row=1, col=1)

#        imageWidget2 = pg.GraphicsLayoutWidget()
#        self.vb2 = imageWidget2.addViewBox(row=1, col=1)

        # Parameters for smooth moving (to no shake hard the piezo)
        self.moveTime = 0.1  # total time to move(s)
        self.moveSamples = 1000  # samples to move
        self.moveRate = self.moveSamples / self.moveTime
        self.activeChannels = ["x", "y", "z"]
        self.AOchans = [0, 1, 2]

        # LiveView Button

        self.liveviewButton = QtGui.QPushButton('confocal LIVEVIEW')
        self.liveviewButton.setCheckable(True)
        self.liveviewButton.clicked.connect(self.liveview)
#        self.liveviewButton.clicked.connect(self.channelsOpen)

        # save image Button

        self.saveimageButton = QtGui.QPushButton('Scan and Save')
        self.saveimageButton.setCheckable(True)
        self.saveimageButton.clicked.connect(self.saveimage)
        self.saveimageButton.setStyleSheet(
                "QPushButton { background-color: gray; }"
                "QPushButton:pressed { background-color: blue; }")

        # Defino el tipo de Scan que quiero

        self.scanMode = QtGui.QComboBox()
        self.scanModes = ['step scan', 'otro scan', 'tempesta scan']
        self.scanMode.addItems(self.scanModes)
#        self.scanMode.currentIndexChanged.connect(
#            lambda: self.setScanMode(self.scanMode.currentText()))

#        def setScanMode(self, mode):
##            self.stageScan.setScanMode(mode)
#            self.scanParameterChanged('scanMode')

        self.stepcheck = QtGui.QCheckBox('Scan Barckward')
        self.stepcheck.clicked.connect(self.steptype)
        self.step = False


        self.canales = False
        # Scanning parameters

        self.initialPositionLabel = QtGui.QLabel('Initial Pos [x0 y0 z0] (µm)')
        self.initialPositionEdit = QtGui.QLineEdit('-7 -5 1')
        self.scanRangeLabel = QtGui.QLabel('Scan range (µm)')
        self.scanRangeEdit = QtGui.QLineEdit('10')
        self.pixelTimeLabel = QtGui.QLabel('Pixel time (ms)')
        self.pixelTimeEdit = QtGui.QLineEdit('1')
        self.numberofPixelsLabel = QtGui.QLabel('Number of pixels')
        self.numberofPixelsEdit = QtGui.QLineEdit('100')
        self.deformationLabel = QtGui.QLabel('Number of deformacion')
        self.deformationEdit = QtGui.QLineEdit('10')
        self.pixelSizeLabel = QtGui.QLabel('Pixel size (nm)')
        self.pixelSizeValue = QtGui.QLabel('')

        self.timeTotalLabel = QtGui.QLabel('tiempo total del escaneo (s)')
        self.timeTotalValue = QtGui.QLabel('')

        self.numberofPixelsEdit.textChanged.connect(self.paramChanged)
        self.deformationEdit.textChanged.connect(self.paramChanged)
        self.scanRangeEdit.textChanged.connect(self.paramChanged)
        self.pixelTimeEdit.textChanged.connect(self.paramChanged)
        self.initialPositionEdit.textChanged.connect(self.paramChanged)

        self.paramChanged()

        self.paramWidget = QtGui.QWidget()

        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        grid.addWidget(imageWidget, 0, 0)
        grid.addWidget(self.paramWidget, 0, 1)
#        grid.addWidget(imageWidget2, 0, 2)

        subgrid = QtGui.QGridLayout()
        self.paramWidget.setLayout(subgrid)
        subgrid.addWidget(self.liveviewButton, 10, 1)
        subgrid.addWidget(self.initialPositionLabel, 0, 1)
        subgrid.addWidget(self.initialPositionEdit, 1, 1)
        subgrid.addWidget(self.scanRangeLabel, 2, 1)
        subgrid.addWidget(self.scanRangeEdit, 3, 1)
        subgrid.addWidget(self.pixelTimeLabel, 4, 1)
        subgrid.addWidget(self.pixelTimeEdit, 5, 1)
        subgrid.addWidget(self.numberofPixelsLabel, 6, 1)
        subgrid.addWidget(self.numberofPixelsEdit, 7, 1)
        subgrid.addWidget(self.deformationLabel, 6, 2)
        subgrid.addWidget(self.deformationEdit, 7, 2)
        subgrid.addWidget(self.pixelSizeLabel, 8, 1)
        subgrid.addWidget(self.pixelSizeValue, 9, 1)
        subgrid.addWidget(self.timeTotalLabel, 13, 1)
        subgrid.addWidget(self.timeTotalValue, 14, 1)
        subgrid.addWidget(self.stepcheck, 11, 2)

#        subgrid.addWidget(self.scanMode, 12, 1)
        subgrid.addWidget(self.saveimageButton, 15, 1)  #

        self.paramWidget.setFixedHeight(400)

        self.vb.setMouseMode(pg.ViewBox.RectMode)
#        self.vb2.setMouseMode(pg.ViewBox.RectMode)
        self.img = pg.ImageItem()
        self.img.translate(-0.5, -0.5)
        self.vb.addItem(self.img)
        self.vb.setAspectLocked(True)
#        self.vb2.addItem(self.img)
#        self.vb2.setAspectLocked(True)
        imageWidget.setAspectLocked(True)
#        imageWidget2.setAspectLocked(True)
        self.hist = pg.HistogramLUTItem(image=self.img)
        self.hist.gradient.loadPreset('thermal')
        self.hist.vb.setLimits(yMin=0, yMax=66000)
#        self.hist.vb2.setLimits(yMin=0, yMax=66000)

#        self.cubehelixCM = pg.ColorMap(np.arange(0, 1, 1/256),
#                                       guitools.cubehelix().astype(int))
#        self.hist.gradient.setColorMap(self.cubehelixCM)

        for tick in self.hist.gradient.ticks:
            tick.hide()
        imageWidget.addItem(self.hist, row=1, col=2)
#        imageWidget2.addItem(self.hist, row=1, col=2)

#        self.ROI = guitools.ROI((0, 0), self.vb, (0, 0), handlePos=(1, 0),
#                               handleCenter=(0, 1), color='y', scaleSnap=True,
#                               translateSnap=True)

        self.viewtimer = QtCore.QTimer()
        self.viewtimer.timeout.connect(self.updateView)

    def paramChanged(self):

        self.scanRange = float(self.scanRangeEdit.text())
        self.numberofPixels = int(self.numberofPixelsEdit.text())
        self.pixelTime = float(self.pixelTimeEdit.text()) / 10**3  # segs
        self.initialPosition = np.array(
                        self.initialPositionEdit.text().split(' '))

        self.deformacion = int(self.deformationEdit.text())

        self.apdrate = 20*10**6
        self.Napd = int(np.round(self.apdrate * self.pixelTime))

        self.pixelSize = self.scanRange/self.numberofPixels

        self.pixelSizeValue.setText('{}'.format(np.around(
                                        1000 * self.pixelSize, 2)))  # en nm

#        self.linetime = (1 / 100000)*float(self.pixelTimeEdit.text()) * float(
#                                        self.numberofPixelsEdit.text())
        self.linetime = self.pixelTime * self.numberofPixels

        print(self.linetime)

        self.timeTotalValue.setText('{}'.format(np.around(
                        2 * self.numberofPixels * self.linetime, 2)))

        size = (self.numberofPixels, self.numberofPixels)
        self.barridos()

        self.inputImage = 1 * np.random.normal(size=size)
        self.blankImage = np.zeros(size)
        self.image = self.blankImage
        self.imagevuelta = np.zeros(size)
#        self.i = 0
        self.dy = 0

# cosas para el save image nuevo
    def saveimage(self):
        """ la idea es que escanee la zona deseada (desde cero)
y guarde la imagen"""
        if self.saveimageButton.isChecked():
            self.save = True
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
        """ Image live view when not recording
        """
        if self.liveviewButton.isChecked():
            self.save = False
            self.channelsOpen()
            self.liveviewStart()

        else:
            self.liveviewStop()

    def liveviewStart(self):
        if self.scanMode.currentText() == "step scan":
            self.viewtimer.start(self.linetime)
        else:
            print("solo anda el Step scan por ahora")

    def liveviewStop(self):
        if self.save:
#            print("listo el pollo")
            self.saveimageButton.setChecked(False)
            self.saveimageButton.setText('Otro Scan and Stop')
            self.save = False
            self.movetoStart()

        self.liveviewButton.setChecked(False)
        self.viewtimer.stop()
        self.done()

    def updateView(self):

        self.lineaida()

        self.lineData = self.cuentas[self.deformacion:]  # self.inputImage[:, self.dy] 
        self.image[:, self.numberofPixels-1-(self.dy)] = self.lineData
        self.img.setImage(self.image, autoLevels=False)

        self.lineavuelta()
        lineDatavuelta = self.cuentasvuelta[:self.numberofPixels]  # self.inputImage[:, self.dy]
        self.imagevuelta[:, self.numberofPixels-1-(self.dy)] = np.flip(lineDatavuelta, axis=0)

        if self.step:
            self.img.setImage(self.imagevuelta, autoLevels=False)
            print("aaa")

        if self.save:
            if self.dy < self.numberofPixels-1:
                self.dy = self.dy + 1
            else:
                self.guardarimagen()

                self.saveimageButton.setText('Fin')
                self.liveviewStop()
        else:
                    
            if self.dy < self.numberofPixels-1:
    #            self.i = self.i + 1
                self.dy = self.dy + 1
            else:
#                self.dy = 0
                self.movetoStart()


    def lineaida(self):
        tic = time.time()

        self.aotask.stop()
        self.citask.stop()

        self.aotask.write(
           np.array([self.barridox,
            self.barridoy + (self.dy * self.pixelSize / convFactors['y']),
            self.barridoz]), auto_start=True)

        tac = time.time()
        APDtodo = self.citask.read(self.Napd * (self.numberofPixels + self.deformacion))
        self.aotask.wait_until_done()
        toc = time.time()

        self.cuentas[0] = APDtodo[self.Napd - 1]
        for j in range(1, self.numberofPixels + self.deformacion):
            self.cuentas[j] = APDtodo[((j+1)*self.Napd)-1] - APDtodo[((j)*self.Napd)-1]

#
#        print("\nvuelta\n", "ditask posta", np.round(toc-tac, 5)/(self.numberofPixels), "pixeltime = ", self.pixelTime)
#        print("data posta", np.round(time.time() - tic, 5), "linetime = ", self.linetime)
#        print(self.Napd, "Napd\n")

    def lineavuelta(self):
        tic = time.time()

        self.aotask.stop()
        self.citask.stop()

        self.aotask.write(
           np.array([self.barridoxvuelta,
            self.barridoy + (self.dy * self.pixelSize / convFactors['y']),
            self.barridoz]), auto_start=True)
        self.aotask.wait_until_done()
        tac = time.time()
        APDtodo = self.citask.read(self.Napd * (self.numberofPixels + self.deformacion))

        toc = time.time()

        self.cuentasvuelta[0] = APDtodo[self.Napd - 1]
        for j in range(1, self.numberofPixels + self.deformacion):
            self.cuentasvuelta[j] = APDtodo[((j+1)*self.Napd)-1] - APDtodo[((j)*self.Napd)-1]


#        print("\n", "ditask posta", np.round(toc-tac, 5)/(self.numberofPixels), "pixeltime = ", self.pixelTime)
#        print("data posta", np.round(time.time() - tic, 5), "linetime = ", self.linetime)
#        print(self.Napd, "Napd\n")

    def barridos(self):
# arma los barridos con los parametros dados
        Samps = self.numberofPixels + self.deformacion
        self.cuentas = np.zeros((Samps))
        self.cuentasvuelta = np.zeros((Samps))

        #       Barrido x
        startX = float(self.initialPosition[0])
        finishX = self.scanRange + startX
        self.barridox = np.linspace(startX, finishX, Samps) / convFactors['x']
        self.barridoxvuelta = np.flip(self.barridox, axis=0)

        #       Barrido y
        startY = float(self.initialPosition[1])
        self.barridoy = np.ones(Samps)*startY / convFactors['y']

        #       Barrido z (se queda en la posicion inicial)
        startZ = float(self.initialPosition[2])
        self.barridoz = np.ones(len(self.barridox)) * startZ / convFactors['z']


    def channelsOpen(self):
        if self.canales:
            print("Ya estan abiertos los canales")  # para evitar el error
            #  usando esto podria no cerrarlos nunca.
        else:
            self.canales = True

            self.aotask = nidaqmx.Task('aotask')
            self.dotask = nidaqmx.Task('dotask')
            self.aitask = nidaqmx.Task('aitask')  # Ger
            self.ditask = nidaqmx.Task('ditask')  # Ger
            self.citask = nidaqmx.Task('citask')
            

            self.citask.ci_channels.add_ci_count_edges_chan(counter='Dev1/ctr0',
                                name_to_assign_to_channel=u'conter',
                                initial_count=0)

            self.citask.timing.cfg_samp_clk_timing(
              rate=self.apdrate, sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
              source='20MHzTimebase',
              samps_per_chan = self.Napd * (self.numberofPixels + self.deformacion))

    #        # Tengo que hacer que dotask accione el/los shutters.
    
    #        self.dotask.do_channels.add_do_chan(  # se ocuparia del shutter
    #            lines="Dev1/port0/line6", name_to_assign_to_lines='chan6',
    #            line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)  # Ger

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
                samps_per_chan=self.numberofPixels + self.deformacion)

    def done(self):
        if self.canales:
#            print("Cierro todos los canales")  # para evitar el error
            self.aotask.stop()
            self.aotask.close()
            self.dotask.stop()
            self.dotask.close()
            self.aitask.stop()  # Ger
            self.aitask.close()  # Ger
            self.ditask.stop()  # Ger
            self.ditask.close()  # Ger
            self.citask.stop()
            self.citask.close()
#            self.nidaq.reset_device()
#            self.finalizeDone.emit()
#            del NoseComoHacerloMejor
            self.canales = False
        else:
            print("llego hasta el done pero no tenia nada que cerrar")

    def openShutter(self, color):
        if color == "red":
            print("abre shutter rojo")
#            self.dotask.write(5, auto_start=True)
# TODO: Es una idea de lo que tendria que hacer la funcion

    def movetoStart(self):
        self.done()
        N = self.moveSamples

        # Following loop creates the voltage channels
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
            samps_per_chan=N)

        tic = time.time()
        startY = float(self.initialPosition[1])
        maximoy = startY + ((self.dy) * self.pixelSize)
        volviendoy = np.linspace(maximoy, startY, N)
        volviendox = np.ones(len(volviendoy)) * float(self.initialPosition[0])
        volviendoz = np.ones(len(volviendoy)) * float(self.initialPosition[2])
        volviendotodo = np.zeros((len(self.AOchans),len(volviendoy)))
        volviendotodo[0,:] =volviendox / convFactors['x']
        volviendotodo[1,:] =volviendoy / convFactors['y']
        volviendotodo[2,:] =volviendoz / convFactors['z']

        self.aotask.write(
             volviendotodo, auto_start=True)
        self.aotask.wait_until_done()
        print(np.round(time.time() - tic, 5))
        self.dy = 0

        self.aotask.stop()
        self.aotask.close()

        self.channelsOpen()

    def guardarimagen(self):
        print("\n Hipoteticamente Guardo la imagen\n")

#        name = str(self.edit_save.text())
#        filepath = "C:/Users/Santiago/Desktop/Germán Tesis de lic/Winpython (3.5.2 para tormenta)/WinPython-64bit-3.5.2.2/notebooks/Guardando tiff/"
#        timestr = time.strftime("%Y%m%d-%H%M%S")
#        name = str(filepath + "image-" + timestr + ".tiff")  # nombre con la fecha -hora
#        guardado = Image.fromarray(self.image)
#        guardado.save(name)

#        name = str(filepath + "imageVUELTA-" + timestr + ".tiff")  # nombre con la fecha -hora
#        guardado = Image.fromarray(self.imagevuelta)
#        guardado.save(name)

#if __name__ == '__main__':

app = QtGui.QApplication([])
win = ScanWidget(device)
win.show()

app.exec_()

#ScanWidget()
