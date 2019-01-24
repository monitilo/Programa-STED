# -*- coding: utf-8 -*-
"""
Created on jan 24 14:34:11 2019

@author: yo
"""

#import nidaqmx
import time
import numpy as np
import matplotlib.pyplot as plt


# %%
# EL CONTROLADOR NUESTRO ES EL 545
#import pipython.pitools as pi
from pipython import GCSDevice
#from pipython import gcscommands

pi_device = GCSDevice ()	# Load PI Python Libraries
pi_device.EnumerateUSB()
#%%
pi_device.ConnectUSB ('0111176619')	# Connect to the controller via USB with serial number 0111176619
#pi_device.qIDN()
#Out[53]: 'Physik Instrumente, E-517, 0111176619, V01.243\n'

#%%
# prende el comando ONLINE para todos los canales. Esto permite manejarlo por PC
axes = ['A','B','C']  # xyz son ABC
pi_device.ONL([1,2,3],[1,1,1])
pi_device.qONL()  # pregunto el estado de ONLINE (true/false)

#%%
# prende el "Drift compensation mode" para cada canal
pi_device.DCO(axes, [True, True, True])
pi_device.qDCO()  # pregunta el estado (tiene que ser true... lo setie recien)
#%%
pi_device.SVO (axes, [True, True, True])	# Turn on servo control
pi_device.qSVO()
# %%
# Velocity control... si lo prendo no me anda el MOV
pi_device.VCO(axes, [False, False, False])
pi_device.qVCO()

#%%
# pregunto la posicion de todos los canales. muevo el x y pregunto de nuevo
pi_device.qPOS()
pi_device.MOV ('A', 1.5)	# Command axis "A" to position 1.5

pi_device.qPOS()

#%%
# se puede pedir la posicion muchas veces para conocer el error de lectura
tic=time.time()
N = 100
aPos = np.zeros(N)
bPos = np.zeros(N)
cPos = np.zeros(N)
for i in range(N):
    pos = pi_device.qPOS()
    aPos[i] = pos['A']
    bPos[i] = pos['B']
    cPos[i] = pos['C']

#print(np.mean(aPos), np.mean(bPos), np.mean(cPos))
print(np.max(aPos), np.mean(aPos), np.min(aPos))
print(time.time()-tic)
#%%
# una manera facil de esperar a que llegue al target
pi_device.qONT()  # checkea si ya se movio o se esta moviendo la platina
axes='A'
targets = 0
pi_device.MOV(axes, targets)
tic=time.time()
while not all(pi_device.qONT(axes).values()):
    time.sleep(0.01)
print(pi_device.qPOS())
print(time.time()-tic)

# %%
# corta la coneccion.
pi_device.CloseConnection()
#pi_device.StopAll()
#pi_device.SystemAbort()

# %%

servo_time = 0.000040  # seconds  # tiempo del servo: 40­µs. lo dice qGWD()

N = 500
axis = 'A'
if axis == 'A':
    number = 1
elif axis == 'B':
    number = 2
elif axis == 'C':
    number = 3

pi_device.WTR(number, 100, 0)

tic = time.time()


nciclos=1
pi_device.WGC(number, nciclos)


print(pi_device.qONT(axis))

print(pi_device.qPOS()[axis])
# creo una onda lineal con esos parametros:
pi_device.WAV_LIN(number, 1, 1000, "X", 100, 20, 0, 1000)

tic = time.time()
pi_device.WGR()

pi_device.WGO(number, True)
print(pi_device.qPOS()[axis])
while any(pi_device.IsGeneratorRunning().values()):
    time.sleep(0.01)
print( "tiempo", time.time()-tic)
#print(pi_device.qONT(axis))
pi_device.WGO(number, 0)

print(pi_device.qPOS()[axis])

#%%
servo_time = 0.000040  # seconds  # tiempo del servo: 40­µs. lo dice qGWD()

N = 500
axis = 'A'
if axis == 'A':
    number = 1
elif axis == 'B':
    number = 2
elif axis == 'C':
    number = 3
wtrtime =100
pi_device.WTR(number, wtrtime, 0)

tic = time.time()


nciclos=1
pi_device.WGC(number, nciclos)


print(pi_device.qONT(axis))

print(pi_device.qPOS()[axis])
Npoints=1000
# creo una onda lineal con esos parametros:
pi_device.WAV_RAMP(number, 1, 1000, "X", 500, 100, 20, 0, Npoints)

tic = time.time()
pi_device.WGR()

pi_device.WGO(number, True)
print(pi_device.IsMoving())
#pi_device.IsGeneratorRunning()
#time.sleep(servo_time*Npoints*wtrtime)

while any(pi_device.IsGeneratorRunning().values()):
    time.sleep(0.01)
    
print(pi_device.qPOS()[axis])
#while not all(pi_device.qONT().values()):
#    time.sleep(0.1)
print( "tiempo", time.time()-tic)
#print(pi_device.qONT(axis))
pi_device.WGO(number, 0)

print(pi_device.qPOS()[axis])
#TWS 2 1 1 2 2 0 2 3 0
#%%  Armo el scaneo completo

#servo_time = 0.000040  # seconds  # tiempo del servo: 40­µs. lo dice qGWD()

pi_device.MOV(['A','B'], [10,10])
#%%Armo el scaneo completo
x_init_pos = pi_device.qPOS()['A']
wtrtime =1
pi_device.WTR(1, wtrtime, 0)
pi_device.WTR(2, wtrtime, 0)
nciclos=1
pi_device.WGC(1, nciclos)
pi_device.WGC(2, nciclos)


tic = time.time()

Npoints=1100
Nrampa = 1000
#       tabla, init, Nrampa, appen, center, speed,amplit, offset, lenght
pi_device.WAV_RAMP(1, 1, Nrampa, "X", 500, 50, 10, 0, Npoints)

#       tabla, init, Nrampa, appen, speed, amplit, offset, lenght
#pi_device.WAV_LIN(2, 1, Nrampa, "X", 100, 1, 0, Npoints)

pi_device.TWC()

pi_device.TWS([1,1,1],[1,3,5],[1,1,1])
pi_device.CTO(1,1,0.005)
pi_device.CTO(1,3,4)
tiic = time.time()

for i in range(32):
    tic = time.time()
    pi_device.WGO(1, True)
    while any(pi_device.IsGeneratorRunning().values()):
        time.sleep(0.01)
    pi_device.WGO(1, False)
    pi_device.MOV('A', x_init_pos)

    #time.sleep(servo_time*Npoints*wtrtime)
    pi_device.WOS(2, i)
    pi_device.WGO(2, True)
    while any(pi_device.IsGeneratorRunning().values()):
        time.sleep(0.01)
    pi_device.WGO(2, False)

    while not all(pi_device.qONT().values()):
        print("no creo que entre a este while")
        time.sleep(0.01)

#    print(i, "tiempo paso i", time.time()-tic)
#    print("tendria que tardar", 2*servo_time*Npoints*wtrtime)
#
#print( "tiempo total", time.time()-tiic)

#pi_device.TWS(1,1,1)
#pi_device.TWS([1,1,1],[1,2,3],[1,0,0])

#%%
pi_device.qPOS()
# %%
pi_device.GOH('C')
pi_device.MOV('C', 1)











#%%
while not all(pi_device.qONT(axis).values()):
    time.sleep(0.1)
print(pi_device.qONT(axis))
#for i in range(1,N):
##    if i == 5:
##        pi_device.WGO(1, True)
#    pos = pi_device.qPOS()
#    aPos[i] = pos['A']
#    bPos[i] = pos['B']
#    cPos[i] = pos['C']
##    if i == N-1:
##        pi_device.WGO(1,False)
pi_device.WGO(number, 0)
print(pi_device.qONT(axis))
print(pi_device.qPOS()[axis])

print( "tiempo", time.time()-tic)
#print(aPos)
#plt.plot(bPos,'.-')
#%%
#from pipython import GCSDevice
#gcs = GCSDevice('E-517')
#gcs.InterfaceSetupDlg()
#print (gcs.qIDN())
##gcs.CloseConnection()
#gcs.qPOS()
#with GCSDevice('E-517') as gcs:
#    gcs.InterfaceSetupDlg()
#    print (gcs.qIDN())
##gcs.CloseConnection()

#-------------------------------------------------------------------------

