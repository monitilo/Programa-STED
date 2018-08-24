
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

def makeRamp(start, end, samples):
    return np.linspace(start, end, num=samples)
convFactors = {'x': 4.06, 'y': 3.9, 'z': 10}

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
#
#    def resetChannels(self, channels):
#        """Method called when the analog output channels need to be used by
#        another resource, typically for scanning. Deactivates the Positionner
#        when it is active and reactives it when it is not, typically after a
#        scan.
#
#        :param dict channels: the channels which are used or released by
#        another object. The positionner does not touch the other channels"""
#        if(self.isActive):
#            self.aotask.stop()
#            self.aotask.close()
#            del self.aotask
#            totalChannels = ["x", "y", "z"]
#            self.aotask = nidaqmx.Task("positionnerTask")
#
#            # returns a list containing the axis not in use
#            self.activeChannels = [
#                x for x in totalChannels if x not in channels]
#
#            try:
#                axis = self.activeChannels[0]
#                n = self.AOchans[self.activeChannels.index(axis)]
#                channel = "Dev1/ao%s" % n
#                self.aotask.ao_channels.add_ao_voltage_chan(
#                    physical_channel=channel, name_to_assign_to_channel=axis,
#                    min_val=minVolt[axis], max_val=maxVolt[axis])
#            except IndexError:
#                pass
#            self.isActive = False
#
#        else:
#            # Restarting the analog channels
#            self.aotask.stop()
#            self.aotask.close()
#            del self.aotask
#            self.aotask = nidaqmx.Task("positionnerTask")
#
#            totalChannels = ["x", "y", "z"]
#            self.activeChannels = totalChannels
#            for axis in totalChannels:
#                n = self.AOchans[self.activeChannels.index(axis)]
#                channel = "Dev1/ao%s" % n
#                self.aotask.ao_channels.add_ao_voltage_chan(
#                    physical_channel=channel, name_to_assign_to_channel=axis,
#                    min_val=minVolt[axis], max_val=maxVolt[axis])
#
#            self.aotask.timing.cfg_samp_clk_timing(
#                rate=self.sampleRate,
#                sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
#                samps_per_chan=self.nSamples)
#            self.aotask.start()
#            self.isActive = True
#
#        for axis in self.activeChannels:
#            newText = "<strong>" + axis + " = {0:.2f} µm</strong>".format(0)
#            getattr(self, axis + "Label").setText(newText)
#
#    def closeEvent(self, *args, **kwargs):
#        if(self.isActive):
#            # Resets the sliders, which will reset each channel to 0
#            self.aotask.wait_until_done(timeout=2)
#            self.aotask.stop()
#            self.aotask.close()

if __name__ == '__main__':

    app = QtGui.QApplication([])
    win = Positionner()
    win.show()

    app.exec_()