
""" Programa inicial donde miraba como anda el liveScan
 sin usar la pc del STED"""

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

convFactors = {'x': 25, 'y': 25, 'z': 25}  # la calibracion es 1 µm = 40 mV; la de Z no la medi
def makeRamp(start, end, samples):
    return np.linspace(start, end, num=samples)


class Positionner(QtGui.QWidget):
    """This class communicates with the different analog outputs of the nidaq
    card. When not scanning, it drives the 3 axis x, y and z.

    :param ScanWidget main: main scan GUI"""

    def __init__(self, main):
        super().__init__()

        self.scanWidget = main
#        self.focusWgt = self.scanWidget.focusWgt

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

#        self.aotask = nidaqmx.Task("positionnerTask")
#        # Following loop creates the voltage channels
#        for n in self.AOchans:
#            self.aotask.ao_channels.add_ao_voltage_chan(
#                physical_channel='Dev1/ao%s' % n,
#                name_to_assign_to_channel=self.activeChannels[n],
#                min_val=minVolt[self.activeChannels[n]],
#                max_val=maxVolt[self.activeChannels[n]])

#        self.aotask.timing.cfg_samp_clk_timing(
#            rate=self.sampleRate,
#            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
#            samps_per_chan=self.nSamples)

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

# --------------------------------------------------------------------------


class ScanWidget(QtGui.QFrame):

    def keyPressEvent(self, e):

        if e.key() == QtCore.Qt.Key_Escape:
            self.close()
            self.liveviewStop()

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

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
        self.scanModes = ['step scan', 'otro scan', 'tempesta scan']
        self.scanMode.addItems(self.scanModes)
        self.scanMode.currentIndexChanged.connect(
            lambda: self.setScanMode(self.scanMode.currentText()))

        def setScanMode(self, mode):
            self.stageScan.setScanMode(mode)
            self.scanParameterChanged('scanMode')

        # no lo quiero cuadrado

#        self.squareRadio = QtGui.QRadioButton('Cuadrado')
#        self.squareRadio.clicked.connect(self.squareOrNot)
#        self.squareRadio.setChecked(True)

        # Scanning parameters

        self.initialPositionLabel = QtGui.QLabel('Initial Pos [x0 y0 z0] (µm)')
        self.initialPositionEdit = QtGui.QLineEdit('1 1 5')
        self.scanRangexLabel = QtGui.QLabel('Scan range x (µm)')
        self.scanRangexEdit = QtGui.QLineEdit('10')
#        self.scanRangeyLabel = QtGui.QLabel('Scan range y (µm)')
#        self.scanRangeyEdit = QtGui.QLineEdit('10')
        pixelTimeLabel = QtGui.QLabel('Pixel time (µs)')
        self.pixelTimeEdit = QtGui.QLineEdit('400')
        numberofPixelsLabel = QtGui.QLabel('Number of pixels')
        self.numberofPixelsEdit = QtGui.QLineEdit('64')
        self.pixelSizeLabel = QtGui.QLabel('Pixel size (nm)')
        self.pixelSizeValue = QtGui.QLabel('')
        self.timeTotalLabel = QtGui.QLabel('tiempo total del escaneo (s)')
        self.timeTotalValue = QtGui.QLabel('')
#        label_save = QtGui.QLabel('Nombre del archivo (archivo.tiff)')
#        label_save.resize(label_save.sizeHint())
#        self.edit_save = QtGui.QLineEdit('imagenScan.tiff')
#        self.edit_save.resize(self.edit_save.sizeHint())

        self.numberofPixelsEdit.textChanged.connect(self.paramChanged)
#        self.scanRangexEdit.textChanged.connect(self.squarex)
#        self.scanRangeyEdit.textChanged.connect(self.squarey)
        self.scanRangexEdit.textChanged.connect(self.paramChanged)
#        self.scanRangeyEdit.textChanged.connect(self.paramChanged)
        self.pixelTimeEdit.textChanged.connect(self.paramChanged)
        self.initialPositionEdit.textChanged.connect(self.paramChanged)

        self.paramChanged()

        self.paramWidget = QtGui.QWidget()

        grid = QtGui.QGridLayout()
        self.setLayout(grid)
        grid.addWidget(imageWidget, 0, 0)
        grid.addWidget(self.paramWidget, 0, 1)
        
#        self.piezoWidget = Positionner(ScanWidget)
#        grid.addWidget(self.piezoWidget, 1, 0)

        subgrid = QtGui.QGridLayout()
        self.paramWidget.setLayout(subgrid)
        subgrid.addWidget(self.liveviewButton, 10, 1)
        subgrid.addWidget(self.saveimageButton, 15, 1)  #
#        subgrid.addWidget(self.squareRadio, 12, 2)  #
        subgrid.addWidget(self.scanMode, 12, 1)
        subgrid.addWidget(self.initialPositionLabel, 0, 1)
        subgrid.addWidget(self.initialPositionEdit, 1, 1)
        subgrid.addWidget(self.scanRangexLabel, 2, 1)
        subgrid.addWidget(self.scanRangexEdit, 3, 1)
#        subgrid.addWidget(self.scanRangeyLabel, 2, 2)
#        subgrid.addWidget(self.scanRangeyEdit, 3, 2)
        subgrid.addWidget(pixelTimeLabel, 4, 1)
        subgrid.addWidget(self.pixelTimeEdit, 5, 1)
        subgrid.addWidget(numberofPixelsLabel, 6, 1)
        subgrid.addWidget(self.numberofPixelsEdit, 7, 1)
        subgrid.addWidget(self.pixelSizeLabel, 8, 1)
        subgrid.addWidget(self.pixelSizeValue, 9, 1)
        subgrid.addWidget(self.timeTotalLabel, 13, 1)
        subgrid.addWidget(self.timeTotalValue, 14, 1)
#        subgrid.addWidget(label_save, 16, 0, 1, 2)
#        subgrid.addWidget(self.edit_save, 17, 0, 1, 2)

        self.paramWidget.setFixedHeight(400)

        self.vb.setMouseMode(pg.ViewBox.RectMode)
        self.img = pg.ImageItem()
        self.img.translate(-0.5, -0.5)
        self.vb.addItem(self.img)
        self.vb.setAspectLocked(True)
        imageWidget.setAspectLocked(True)
        self.hist = pg.HistogramLUTItem(image=self.img)
        self.hist.gradient.loadPreset('flame')  # thermal
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

    def paramChanged(self):

        self.scanRangex = float(self.scanRangexEdit.text())
        self.scanRangey = self.scanRangex  # float(self.scanRangeyEdit.text())

        self.numberofPixels = int(self.numberofPixelsEdit.text())
        self.pixelTime = float(self.pixelTimeEdit.text()) / 10**6
        self.initialPosition = np.array(
                self.initialPositionEdit.text().split(' '))

        self.pixelSize = self.scanRangex/self.numberofPixels

        self.pixelSizeValue.setText('{}'.format(np.around(
                        1000 * self.pixelSize, 2)))

        self.linetime = (1/1000)*float(
                self.pixelTimeEdit.text())*int(self.numberofPixelsEdit.text())
        print(self.linetime)

        self.timeTotalValue.setText('{}'.format(np.around(
                        self.numberofPixels * self.linetime, 2)))

        size = (self.numberofPixels, self.numberofPixels)

        self.inputImage = 100 * np.random.normal(size=size)
        self.blankImage = np.zeros(size)
        self.image = self.blankImage
        self.i = 0

# cosas para el save image nuevo
    def saveimage(self):
        """ la idea es que escanee la zona deseada (desde cero)
y guarde la imagen"""
        if self.saveimageButton.isChecked():
            self.save = True
            self.movetoStart()
            self.saveimageButton.setText('Abort')
            self.guarda = np.zeros((self.numberofPixels, self.numberofPixels))
            self.liveviewStart()

        else:
            self.save = False
            print("Abort")
            self.saveimageButton.setText('reintentar')
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
            self.viewtimer.start(self.linetime)
        else:
            print("solo anda el Step scan por ahora")

    def liveviewStop(self):
        if self.save:
            print("listo el pollo")
            self.saveimageButton.setChecked(False)
            self.saveimageButton.setText('Otro Scan and Stop')
            self.save = False
        self.liveviewButton.setChecked(False)
        self.viewtimer.stop()

    def updateView(self):

#        self.inputImage[5, self.i] = 0
#        self.inputImage[9, self.i] = 333
        self.lineData = self.inputImage[:, self.i]  # + 2.5*self.i
        lineData2 = self.inputImage[:, self.i + 1]
        self.image[:, self.numberofPixels-1-self.i] = self.lineData
        self.image[:, self.numberofPixels-2-self.i] = lineData2
        
        self.img.setImage(self.image, autoLevels=False)

        if self.save:
            if self.i < self.numberofPixels-2:
                self.guarda[:, self.i] = self.inputImage[:, self.i]
                self.i = self.i + 2
            else:
                print("Hipoteticamente Guardo la imagen\n")
#                name = str(self.edit_save.text())
#                filepath = "C:/Users/Santiago/Desktop/Germán Tesis de lic/Winpython (3.5.2 para tormenta)/WinPython-64bit-3.5.2.2/notebooks/Guardando tiff/"
#                timestr = time.strftime("%Y%m%d-%H%M%S")
#                name = str(filepath + "image-" + timestr + ".tiff")  # nombre con la fecha -hora
#                guardado = Image.fromarray(self.guarda)
#                guardado.save(name)

                self.saveimageButton.setText('Fin')
                self.liveviewStop()

        else:
            if self.i < self.numberofPixels-2:
                self.i = self.i + 2
            else:
#                self.i = self.i - 2
                self.movetoStart()

    def movetoStart(self):
        self.inputImage = 100 * np.random.normal(
                    size=(self.numberofPixels, self.numberofPixels))
        t = 0.1
        tic = time.time()
        maximoy = (float(self.initialPosition[1]) + (self.i * self.pixelSize))
        volviendoy = np.linspace(maximoy, 0, 100)
        volviendox = np.ones(len(volviendoy)) * float(self.initialPosition[0])
        volviendoz = np.ones(len(volviendoy)) * float(self.initialPosition[2])
        for i in range(len(volviendoy)):
            b = volviendoy[i] + volviendox[i] + volviendoz[i]
#            self.aotask.write(
#                 [volviendox[i],
#                  volviendoy[i] / convFactors['y'],
#                  volviendoz[i]], auto_start=True)
            time.sleep(t / 100)
        print(t, "vs" , np.round(time.time() - tic, 2))
        self.i = 0
# - - - ----------------------------------------

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

if __name__ == '__main__':

    app = QtGui.QApplication([])
    win = ScanWidget()
    win.show()

    app.exec_()

#        if 'a' in locals() or 'a' in globals():
#            print("borro a")
#            del a
#        else:
#            print("no esta a para borrar")
