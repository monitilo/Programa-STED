# -*- coding: utf-8 -*-
"""
Created on Mon Apr 16 11:50:11 2018

@author: mdborde
"""
import pprint
import nidaqmx
import time
import numpy as np
import matplotlib.pyplot as plt

pp = pprint.PrettyPrinter(indent=4)
# %% probando streams

#https://github.com/ni/nidaqmx-python/blob/master/nidaqmx_examples/ai_multi_task_pxie_ref_clk.py
#https://github.com/ni/nidaqmx-python/blob/master/nidaqmx/tests/test_stream_analog_readers_writers.py

#https://nidaqmx-python.readthedocs.io/en/latest/stream_readers.html
# %%

# %% progando con los dos contadores al mismo tiempo

from nidaqmx.types import CtrTime
resolucionDAQ = 0.0003 * 2 * 25 # V => µm; uso el doble para no errarle
Npix=500
apdrate= 10**5
tpix = 0.01 *10**-3 # en milisegundos
Napd=int(apdrate*tpix)
Range = 10

Nsamples = int(np.ceil(Range/resolucionDAQ))
signal = np.ones((Nsamples*Napd),dtype="bool")
signalAnalog= np.ones(len(signal)) * 5*np.random.rand(len(signal))
#
otro = np.zeros(len(signal),dtype='bool')
for i in range(10,len(signal)):
    r = np.random.rand(1)[0]
    if r > 0.5:
        otro[i] = True
    else:
        otro[i] = False
#for i in range(int(2*len(signal)/3)):
#    signal[i] = True
for i in range(550):
    signal[i] = False
#for i in range(500):
#    otro[i] = False
#otro[-10:-1] = True
#otro[-1] = False
trigger = signal  # np.append(signal,otro)
rate = np.round(1 / tpix,9)
#rate = apdrate

#citask = nidaqmx.Task('citask')    

#nidaqmx.stream_readers
#    add_global_channels(["Dev1/ctr0"])
data = np.zeros(len(signal))
#nidaqmx.stream_readers.CounterReader.read_many_sample_double(data,
#                                                             len(signal))
cuentas = np.zeros(Npix)
with nidaqmx.Task("read") as citask:
    with nidaqmx.Task("dotask") as dotask:
        with nidaqmx.Task("aotask") as aotask:
            with nidaqmx.Task("apdtask") as apdtask:
#                citask.stream_readers.CounterReader.read_many_sample_double(data,
#                                                             len(signal))
                tic = time.time()
                dotask.do_channels.add_do_chan(
                       "Dev1/port0/line6",
                       line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
        
                dotask.timing.cfg_samp_clk_timing(
                             rate=rate,  # muestras por segundo
                             sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
        #                     source='',
                             samps_per_chan=len(trigger))
        
                citask.ci_channels.add_ci_count_edges_chan(
                            counter='Dev1/ctr0',
                            initial_count=0)
        
                citask.timing.cfg_samp_clk_timing(
                          rate=apdrate,
                          sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                          source=r'100kHzTimebase',
                          samps_per_chan = len(signal))

                apdtask.ci_channels.add_ci_count_edges_chan(
                            counter='Dev1/ctr1',
                            name_to_assign_to_channel='counter',
                            initial_count=0)

                apdtask.timing.cfg_samp_clk_timing(
                          rate=apdrate,
                          sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                          source=r'100kHzTimebase',
                          samps_per_chan = len(signal))

                triggerchannelname = "PFI4"
                aotask.ao_channels.add_ao_voltage_chan(
                           physical_channel='Dev1/ao0')
                aotask.timing.cfg_samp_clk_timing(
                    rate=rate,
    #                source=r'100kHzTimeBase',
                    sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                    samps_per_chan=len(signalAnalog))
    
                aotask.triggers.start_trigger.cfg_dig_edge_start_trig(
                                    trigger_source = triggerchannelname)#,
        #                                trigger_edge = nidaqmx.constants.Edge.RISING)
    
                citask.triggers.arm_start_trigger.dig_edge_src = triggerchannelname
                citask.triggers.arm_start_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_EDGE
                apdtask.triggers.arm_start_trigger.dig_edge_src = triggerchannelname
                apdtask.triggers.arm_start_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_EDGE

                apdtask.triggers.sync_type.MASTER = True
                citask.triggers.sync_type.SLAVE = True

#                with nidaqmx.Task("stream") as streamtask:
#                    streamtask.in_stream.
#                    in_stream.channels_to_read1('counter')

                dotask.write(trigger,auto_start=False)
                aotask.write(signalAnalog,auto_start=False)
                tuc=time.time()
                aotask.start()
                dotask.start()
#stream_readers.CounterReader
#read_many_sample_double(data, number_of_samples_per_channel=-1, timeout=10.0)
                citask.start()
                apdtask.start()

#                APDtodo = citask.read(number_of_samples_per_channel=len(signal))
#                print("paso un conter")
#                APD2 = apdtask.read(number_of_samples_per_channel=len(signal))
#                print("paso el otro")
                (APDtodo,APD2) = (citask.read(number_of_samples_per_channel=len(signal)),
                                 apdtask.read(number_of_samples_per_channel=len(signal)))

#                citask.wait_until_done()
#                apdtask.wait_until_done()
                tec = time.time()
                dotask.wait_until_done()

#        pp.pprint(cdata)
toc = time.time()
#cuentas = np.zeros(len(APDtodo))
#for i in range(len(APDtodo)-1):
#    cuentas[i] = APDtodo[i+1] - APDtodo[i]
#print((toc-tic)*10**3, "milisegundos", tpix*Npix*10**3,"\ncitask solo = ", (tec-tac)*10**3, "\n ditask")#, (tuc-tupac)*10**3)
plt.plot(trigger, '-')
plt.plot(signalAnalog, '-')
plt.plot(APDtodo, '--r')
plt.plot(APD2, '--m')
#plt.plot(cuentas, '*-m')
#plt.axis([0, len(signal)/50+1, -0.1, 1.1])
plt.show()


# %% Voltaje fijo analogo
c = 0
for i in range(3):
    if i == c:
        with nidaqmx.Task() as task:
            task.ao_channels.add_ao_voltage_chan(
                            physical_channel='Dev1/ao%s' % i,
                            min_val=-5, max_val=7)
            task.write([0.0], auto_start=True)
    else:
        with nidaqmx.Task() as task:
            task.ao_channels.add_ao_voltage_chan(
                            physical_channel='Dev1/ao%s' % i,
                            min_val=-5, max_val=5)
            task.write([0.0], auto_start=True)
# %% Leer Analog
with nidaqmx.Task("ai7") as task:
    task.ai_channels.add_ai_voltage_chan("Dev1/ai7:6")
    task.wait_until_done()
#    data6 = task.read(number_of_samples_per_channel=5)

#    task.ai_channels.add_ai_voltage_chan("Dev1/ai7")
#    task.wait_until_done()
    data = task.read(number_of_samples_per_channel=5)

    pp.pprint(data)
#    pp.pprint(data6)

# %% Leer Digital
#
#tic = time.time()
#
#with nidaqmx.Task("digital") as task:
#    task.di_channels.add_di_chan(
#                lines='Dev1/port0/line0:31',
#                line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
#
#    task.timing.cfg_samp_clk_timing(
#                rate=1, sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
#                samps_per_chan=5)
#
#    data = task.read(number_of_samples_per_channel=10)
#    task.wait_until_done()
#    t = 0
#    for i in range(len(data)):
#        if data[i]:
#            t = t+1
#    pp.pprint(data)
#    print(t)
#
#toc = time.time()
#print(toc-tic, "segundos")
##    pp.pprint(data6)

# %% Leer Cont
""" Leo las entradas CONTADORES
"""

with nidaqmx.Task() as task:
    task.ci_channels.add_ci_count_edges_chan("Dev1/ctr0")
        
    task.wait_until_done()
    print('1 Channel 1 Sample Read: ')
    data = task.read()
    pp.pprint(data)

    print('1 Channel N Samples Read: ')
    data = task.read(number_of_samples_per_channel=25)
    pp.pprint(data)

#plt.plot(data)

# %% Analog --> Conunt
"""mando señal analoga, y la leo con contadores.
No logro leer nada.
"""
from nidaqmx.types import CtrTime

tic = time.time()
data = 0
rate = 10**3
#tiempo = 0.1  # en segundos
N = 100
ini = 0+25
fin = N-25
signal = np.zeros(N, dtype=int)
signal[range(ini, fin)] = 1

#citask = nidaqmx.Task('citask')    

with nidaqmx.Task("read") as citask:
    with nidaqmx.Task("aotask") as aotask:

        aotask.ao_channels.add_ao_voltage_chan(
                                "Dev1/ao0",
                                min_val=-5.0, max_val=5.0,
                                units=nidaqmx.constants.VoltageUnits.VOLTS)
#        aotask.timing.cfg_samp_clk_timing(
#                     rate=rate,  # muestras por segundo
#                     sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
#                     samps_per_chan=N)
        aotask.write(signal, auto_start=True)

        citask.ci_channels.add_ci_count_edges_chan(
                    counter='Dev1/ctr0')

#        citask.timing.cfg_samp_clk_timing(
#          rate=rate, sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
#          source=r'do/SampleClock', samps_per_chan=N)

        aotask.wait_until_done(15)
        cdata = citask.read(number_of_samples_per_channel=8)

#    citask.wait_until_done(5)
        pp.pprint(cdata)


#plt.plot(signal, '-')
#plt.plot(cdata, '--r')
#plt.axis([0, N+1, -0.1, 1.1])
toc = time.time()
print(toc-tic, "segundos")

#cotask.stop()
#citask.stop()
#cotask.close()
#citask.close()
# %% digital --> Cont
"""mando señal digital, y la leo con contadores.
"""
from nidaqmx.types import CtrTime

Npix=500
#data = 0
rate = 10**5
apdrate= 10**5
t = 0.1 *10**-3 # en milisegundos
Nc=int(apdrate*t*Npix)
N=Nc
Napd = int(rate*t)
#N = int(Napd*Npix)

print(Napd,Nc)
#ini = 0+25
#fin = N
#signal = [True,True,False,False,True,True,False,False,True,True,False,False,True,True,False,False,True,True]#np.zeros(N, dtype="bool")
#signal[range(ini, fin)] = True

#citask = nidaqmx.Task('citask')    
cuentas = np.zeros(Npix)
with nidaqmx.Task("read") as citask:
    with nidaqmx.Task("ditask") as ditask:
        with nidaqmx.Task("citask") as citask:
            tic = time.time()
            ditask.di_channels.add_di_chan(
                   "Dev1/port0/line2",
                   line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
    
            ditask.timing.cfg_samp_clk_timing(
                         rate=rate,  # muestras por segundo
                         sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                         samps_per_chan=Nc)
    #
            tupac=time.time()
            APDtodo = ditask.read(number_of_samples_per_channel=N)
            ditask.wait_until_done()
            tuc=time.time()
    #
    #        APD = np.split(np.array(APDtodo), Npix)
    #        aux = 0
    #        for i in range(Npix):
    #            for c in range(Napd-1):
    #                if APD[i][c] < APD[i][c+1]:
    #                    aux = aux + 1
    #            cuentas[i] = aux
    
            citask.ci_channels.add_ci_count_edges_chan(
                        counter='Dev1/ctr0')
    
            citask.timing.cfg_samp_clk_timing(
              rate=apdrate, sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
              source=r'100kHzTimebase', samps_per_chan= Nc)
    
            tac = time.time()
            cdata = citask.read(number_of_samples_per_channel=Nc)
    #        citask.wait_until_done()
            tec = time.time()
    
    #    citask.wait_until_done(5)
    #        pp.pprint(cdata)
toc = time.time()

print((toc-tic)*10**3, "milisegundos", t*Npix*10**3,"\ncitask solo = ", (tec-tac)*10**3, "\n ditask", (tuc-tupac)*10**3)
#plt.plot(signal, '-')
plt.plot(cdata, '--r')
#plt.plot(cuentas)
#plt.axis([0, len(signal)+1, -0.1, 1.1])



#cotask.stop()
#citask.stop()
#cotask.close()
#citask.close()

# %% digital --> analog
"""mando señal digital, y la leo con analogica.
No llega a leer todo. solo ve el final
"""
from nidaqmx.types import CtrTime

tic = time.time()
data = 0
rate = 10**3
#tiempo = 0.1  # en segundos
N = 100
ini = 0+25
fin = N
#signal = [False,False,True,True,False,False,True,True,False,False,True,True,False,False,True,True]
signal = np.zeros(N, dtype="bool")
signal[range(ini, fin)] = True

#citask = nidaqmx.Task('citask')    

with nidaqmx.Task("read") as aitask:
    with nidaqmx.Task("dotask") as dotask:

        dotask.do_channels.add_do_chan(
               "Dev1/port0/line6",
               line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)

        dotask.timing.cfg_samp_clk_timing(
                     rate=rate,  # muestras por segundo
                     sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                     samps_per_chan=len(signal))
        dotask.write(signal, auto_start=True)

        aitask.ai_channels.add_ai_voltage_chan("Dev1/ai7")

        aitask.timing.cfg_samp_clk_timing(
                rate=rate,
                sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                samps_per_chan=len(signal))


        dotask.wait_until_done()
        data = aitask.read(number_of_samples_per_channel=len(signal))

#        aitask.wait_until_done(5)
        pp.pprint(data)


plt.plot(signal, '-')
plt.plot(data, '--r')
#plt.axis([0, len(signal)+1, -0.1, 1.1])
toc = time.time()
print(toc-tic, "segundos")

#cotask.stop()
#citask.stop()
#cotask.close()
#citask.close()

# %% analog --> digital
"""mando señal analogica y la leo con la digital.
a partir de 1.7 V, ve un 1 en la salida digital, pero tampoco da el tiempo
solo ve el ultimo punto
"""
from nidaqmx.types import CtrTime

tic = time.time()
data = 0
rate = 10**2
#tiempo = 0.1  # en segundos
N = 100
ini = 0+25
fin = N
#signal = [False,False,True,True,False,False,True,True,False,False,True,True,False,False,True,True]
#signal = np.zeros(N, dtype=float)  # "bool"
#signal[range(ini, fin)] = 2
signal=[0,0,0,2,2,2,0,0,0,2,2,2,0,0,0,2,2,2,2,2,0,0,0,2,0,0,2,2,2]
#citask = nidaqmx.Task('citask')    

with nidaqmx.Task("read") as ditask:
    with nidaqmx.Task("aotask") as aotask:

        aotask.ao_channels.add_ao_voltage_chan("Dev1/ao0")

        aotask.timing.cfg_samp_clk_timing(
                     rate=rate,  # muestras por segundo
                     sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                     samps_per_chan=len(signal))
        aotask.write(signal, auto_start=True)

        ditask.di_channels.add_di_chan(
            "Dev1/port0/line6",
            line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)

        ditask.timing.cfg_samp_clk_timing(
                rate=rate,
                sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                samps_per_chan=len(signal))

        aotask.wait_until_done()
        data = ditask.read(number_of_samples_per_channel=len(signal))

#        aitask.wait_until_done(5)
        pp.pprint(data)


plt.plot(signal, '-')
plt.plot(data, '--r')
#plt.axis([0, len(signal)+1, -0.1, 1.1])
toc = time.time()
print(toc-tic, "segundos")

#cotask.stop()
#citask.stop()
#cotask.close()
#citask.close()
# %% Escribi cont
"""no me funciona escribir por contadores
"""
import nidaqmx
from nidaqmx.types import CtrTime
with nidaqmx.Task() as task:
    task.co_channels.add_co_pulse_chan_time("Dev1/ctr0")
    sample = CtrTime(high_time=0.001, low_time=0.001)
    task.write(sample)

#    task.wait_until_done()

# %% digital --> digital (continua)
""" todo con salidas y entradas digitales
"""

tic = time.time()
data = 0
rate = 10**2
tiempo = 0.1  # en segundos
N = 50
ini = 0+25
fin = N
signal = np.zeros(N, dtype="bool")
#signal[range(ini, fin)] = True
#signal = [True,True,False,False,True,True,False,False,True,True,False,False,True,True,False,False,True,True]#np.zeros(N, dtype="bool")
for e in range(N):
    r = np.random.rand(1)[0]
#        print(r)
    if 0.8 < r:
        signal[e] = True

#with nidaqmx.Task("read") as ditask:
#    with nidaqmx.Task("write") as dotask:
dotask = nidaqmx.Task('dotask')
ditask = nidaqmx.Task('ditask')

dotask.do_channels.add_do_chan(
            lines='Dev1/port0/line7',
            line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
#
dotask.timing.cfg_samp_clk_timing(
  rate=rate, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
  samps_per_chan=len(signal))



ditask.di_channels.add_di_chan(
            lines='Dev1/port0/line4',
            line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
#ditask.in_stream.input_buf_size = 0

ditask.timing.cfg_samp_clk_timing(
  rate=rate, sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
  samps_per_chan=N)

#ditask.timing.cfg_change_detection_timing(
#        rising_edge_chan='Dev1/port1/line3', falling_edge_chan='Dev1/port1/line3',
#        sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
#        samps_per_chan=len(signal))
dotask.write(signal, auto_start=True)
data = ditask.read(number_of_samples_per_channel=N)
ditask.wait_until_done()
#        t = 0
#        for i in range(len(data)):
#            if not data[0]:
#                for j in range(len(data[0])):
#                    if data[i][j]:
#                        t = t+1
#        pp.pprint(data)
#        print(t)

plt.plot(signal, '-')
plt.plot(data, '--r')
plt.axis([0, len(signal)+1, -0.1, 1.1])
toc = time.time()
print(toc-tic, "segundos")


dotask.stop()
ditask.stop()
dotask.close()
ditask.close()

# %% Analogo --> analogo (continua)
"""estoy tratando de mandar un voltaje por el canal ao1 y leerlo por el ai7
de manera continua. (con un seno de N puntos). y lo logré
"""

tic = time.time()

N = 10**4
x = np.linspace(0, 2*np.pi, N)
y = np.sin(x)
#tiempo = 0.5  # para tiempos menores a 0.5 (N=!00) empieza a leer tarde  
rate = int(N)
sampsInScan = int(N/2)*8
#data=np.zeros((4))

#with nidaqmx.Task("write") as task:
#    with nidaqmx.Task("read") as task2:
task = nidaqmx.Task("write")
task2 = nidaqmx.Task("read")
task.ao_channels.add_ao_voltage_chan(
        "Dev1/ao0",
        name_to_assign_to_channel="canal0", min_val=-5.0, max_val=5.0,
        units=nidaqmx.constants.VoltageUnits.VOLTS)

#    task.out_stream.output_buf_size = N+1

task.timing.cfg_samp_clk_timing(
        rate=rate, # muestras por segundo
        sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
        samps_per_chan=sampsInScan)
#    task.write(y, auto_start=True)
#        task.write([0,0.5,1,1.5,2,2.222], auto_start=True)
task.write(y, auto_start=False)

#    task.wait_until_done(15)

task2.ai_channels.add_ai_voltage_chan("Dev1/ai7")
task2.timing.cfg_samp_clk_timing(
        rate=rate,
        sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
        samps_per_chan=sampsInScan)

task.start()
data = task2.read(number_of_samples_per_channel=N)
task.wait_until_done(15)
#        task2.wait_until_done(15)
#        pp.pprint(data)


toc = time.time()
print(toc-tic, "segundos")

#z=np.linspace(0,2*np.pi,2*N)

plt.plot(y, '-b')
plt.plot(data, '--r')
#plt.xlim([0,1100])
plt.show()

task.stop()
task2.stop()
task.close()
task2.close()
#%% analogo-->analog (discreto)
""" logro leer lo que mando, pero de una manera "discreta". punto por punto
"""
import numpy as np
import time
import matplotlib.pyplot as plt
tic=time.time()
N=100
x=np.linspace(0,2*np.pi,N)
y=np.sin(x)
data=np.zeros((N, 2))
#for j in range(3):
for i in range(N):
    with nidaqmx.Task() as task:
        task.ao_channels.add_ao_voltage_chan("Dev1/ao0:1", 
          name_to_assign_to_channel="canal1",min_val=-5.0, max_val=5.0, 
          units=nidaqmx.constants.VoltageUnits.VOLTS)
        
        task.write([2*y[i], y[i]*0.5], auto_start=True,timeout=10.0)
        
    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_voltage_chan("Dev1/ai7:6")
        data[i, :]=task.read()
#            pp.pprint(data)
        time.sleep(10**-3) 

toc = time.time()
print(toc-tic, "segundos")            
plt.plot(x, y, 'b')
plt.plot(x, data[:, 0], 'm')
plt.plot(x, data[:, 1], 'r')

plt.show()

#%% analogo-->digital (discreto)
""" Mando analogo, y leo por digital. De a puntos. anda
"""
import numpy as np
import time
import matplotlib.pyplot as plt
tic=time.time()
N=100
x=np.linspace(0,np.pi,N)
y=np.sin(x)*2
y=[0,0,0,2,2,2,0,0,0,2,2,2,0,0,0,2,2,2,2,2,0,0,0,2,0,0,2,2,2]

data=np.zeros((len(y)))
#for j in range(3):
for i in range(len(y)):
    with nidaqmx.Task() as task:
        task.ao_channels.add_ao_voltage_chan("Dev1/ao0", 
          name_to_assign_to_channel="canal1",min_val=-5.0, max_val=5.0, 
          units=nidaqmx.constants.VoltageUnits.VOLTS)
        task.write([y[i]], auto_start=True,timeout=10.0)
        
    with nidaqmx.Task() as ditask:
        ditask.di_channels.add_di_chan(
            "Dev1/port0/line6",
            line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
        data[i]=ditask.read()
#        pp.pprint(data)
#        time.sleep(10**-3) 

toc=time.time()
print(toc-tic, "segundos")            
plt.plot(y)
plt.plot(data,'*r')
#plt.axis([0, 6, -1.1, 1.1])
plt.show()

#%% digital->analog (discreto)
""" Mando de digital y leo por analog; discreto. anda
"""
import numpy as np
import time
import matplotlib.pyplot as plt
tic=time.time()
N=100
ini = 0+25
fin = N-25
#signal = [False,False,True,True,False,False,True,True,False,False,True,True,False,False,True,True]
signal = np.zeros(N, dtype="bool")
signal[range(ini, fin)] = True
data=np.zeros((len(signal)))
#for j in range(3):
for i in range(len(signal)):
    with nidaqmx.Task() as dotask:
        dotask.do_channels.add_do_chan(
           "Dev1/port0/line6",
           line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
        dotask.write(signal[i], auto_start=True,timeout=10.0)

    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_voltage_chan("Dev1/ai7")
        data[i]=task.read()
#        pp.pprint(data)
        time.sleep(10**-3) 

toc=time.time()
print(toc-tic, "segundos")            
plt.plot(signal)
plt.plot(data,'*r')
plt.show()
#%% digital-> contador (discreto)
""" Mando de digital y leo porcontador; discreto. No anda
Claramente no entiendo como funciona un contador...
Quizas estoy confundiendo la entrada. 
hay hasta ctr4 y no se donde
"""

tic=time.time()
N=100
ini = 0+25
fin = N
#signal = [False,False,True,True,False,False,True,True,False,False,True,True,False,False,True,True]
signal = np.zeros(N, dtype="bool")
signal[range(ini, fin)] = True
data=np.zeros((len(signal)))
#for j in range(3):
for i in range(len(signal)):
    with nidaqmx.Task() as dotask:
        dotask.do_channels.add_do_chan(
           "Dev1/port0/line6",
           line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
        dotask.write(signal[i], auto_start=True,timeout=10.0)

    with nidaqmx.Task() as citask:
        citask.ci_channels.add_ci_count_edges_chan(
                    counter='Dev1/ctr0')
        data[i]=citask.read()
#        pp.pprint(data)
        time.sleep(10**-2) 

toc=time.time()
print(toc-tic, "segundos")            
plt.plot(signal)
plt.plot(data,'*r')
plt.show()

# %% digital-> digital (discreto)
""" Mando de digital y leo por digital; discreto.
"""

tic=time.time()
N=100
ini = 0+25
fin = N
signal = [False,False,True,True,False,False,True,True,False,False,True,True,False,False,True,True]
#signal = np.zeros(N, dtype="bool")
#signal[range(ini, fin)] = True
data=np.zeros((len(signal)))

#dotask = nidaqmx.Task('write')    
#ditask = nidaqmx.Task('read')    

with nidaqmx.Task() as dotask:
    dotask.do_channels.add_do_chan(
            "Dev1/port0/line7",
            line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
    
    with nidaqmx.Task() as ditask:
        ditask.di_channels.add_di_chan(
                 "Dev1/port1/line3",
                 line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
        
        for i in range(len(signal)):
            tic = time.time()
            dotask.write(signal[i], auto_start=True,timeout=10.0)

            data[i]=ditask.read()
    #        pp.pprint(data)
#            time.sleep(0.01) 

            toc = time.time()
            print(toc-tic, "segundos")

plt.plot(signal)
plt.plot(data, '*r')
plt.axis([0, len(signal)+1, -0.1, 1.1])
plt.show()


#dotask.stop()
#ditask.stop()
#dotask.close()
#ditask.close()
# %%


# %% digital --> Cont
"""mando señal digital, y la leo con contadores.
"""
from nidaqmx.types import CtrTime
resolucionDAQ = 0.0003 * 2 * 25 # V => µm; uso el doble para no errarle
Npix=500
apdrate= 10**5
tpix = 0.01 *10**-3 # en milisegundos
Napd=int(apdrate*tpix)
Range = 10

Nsamples = int(np.ceil(Range/resolucionDAQ))
signal = np.ones((Nsamples*Napd),dtype="bool")

for i in range(len(signal)):
    r = np.random.rand(1)[0]
    if r > 0.5:
        signal[i] = True
    else:
        signal[i] = False
#for i in range(int(2*len(signal)/3)):
#    signal[i] = True
for i in range(10):
    signal[i] = False
rate = (Range/resolucionDAQ) / (tpix*Npix)
#rate = apdrate

#citask = nidaqmx.Task('citask')    

cuentas = np.zeros(Npix)
with nidaqmx.Task("read") as citask:
    with nidaqmx.Task("dotask") as dotask:
        
#dotask = nidaqmx.Task('write')
#citask = nidaqmx.Task('read')

        tic = time.time()
        dotask.do_channels.add_do_chan(
               "Dev1/port0/line7",
               line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
        #
        dotask.timing.cfg_samp_clk_timing(
                     rate=rate,  # muestras por segundo
                     sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                     source='',
                     samps_per_chan=len(signal))

        citask.ci_channels.add_ci_count_edges_chan(
                    counter='Dev1/ctr0')

        citask.timing.cfg_samp_clk_timing(
                  rate=apdrate,
                  sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                  source=r'100kHzTimebase',
                  samps_per_chan = len(signal))

#        citask.triggers.start_trigger.cfg_dig_edge_start_trig(
#                               trigger_source = "Dev1/port0/line7",
#                               trigger_edge = nidaqmx.constants.Edge.RISING)
#        citask.triggers.start_trigger.dig_edge_src="Dev1/port0/line7"
#        citask.triggers.start_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING

#        citask.triggers.start_trigger.anlg_edge_src = "Dev1/ao0"

        dotask.triggers.start_trigger.dig_edge_src="Dev1/ctr0"
        dotask.triggers.start_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING

#        dotask.triggers.start_trigger.disable_start_trig()
        dotask.triggers.start_trigger.delay_units = nidaqmx.constants.DigitalWidthUnits.SECONDS
        dotask.triggers.start_trigger.delay = 0.0035 #segs  # 200000*1.5 #default

        dotask.write(signal,auto_start=False)
        tuc=time.time()
        dotask.start()
        APDtodo = citask.read(number_of_samples_per_channel=len(signal))
        citask.wait_until_done()
        tec = time.time()

        dotask.wait_until_done()

#        pp.pprint(cdata)
toc = time.time()
cuentas = np.zeros(len(APDtodo))
for i in range(len(APDtodo)-1):
    cuentas[i] = APDtodo[i+1] - APDtodo[i]
#print((toc-tic)*10**3, "milisegundos", tpix*Npix*10**3,"\ncitask solo = ", (tec-tac)*10**3, "\n ditask")#, (tuc-tupac)*10**3)
plt.plot(signal, '-')
#plt.plot(APDtodo, '--r')
plt.plot(cuentas, '*-m')
#plt.axis([0, len(signal)/50+1, -0.1, 1.1])
plt.show()



#dotask.stop()
#citask.stop()
#dotask.close()
#citask.close()



# %% ANALOG --> Cont (onda completa)
"""mando señal digital, y la leo con contadores.
"""
from nidaqmx.types import CtrTime
resolucionDAQ = 0.0003 * 2 * 25 # V => µm; uso el doble para no errarle
Npix=5
apdrate= 10**5
tpix = 0.01 *10**-3 # en milisegundos
Napd=int(apdrate*tpix)
Range = 10

Nsamples = int(np.ceil(Range/resolucionDAQ))
signal = np.zeros((Nsamples))
signal[100] = 5.1
#for i in range(len(signal)):
#    r = np.random.rand(1)[0]
#    if r > 0.99:
#        signal[i] = 5.1
#    else:
#        signal[i] = 0.0
#for i in range(int(2*len(signal)/3)):
#    signal[i] = True
#for i in range(10):
#    signal[i] = 0

#rate = (Range/resolucionDAQ) / (tpix*Npix)
rate = apdrate

Nposta = int((len(signal)/rate) * apdrate)  # == Npix*Napd

signaltodo = np.tile(signal, Npix)

contando = np.zeros((len(signal),Npix))
with nidaqmx.Task("read") as citask:
    with nidaqmx.Task("aotask") as aotask:
        
#dotask = nidaqmx.Task('write')
#citask = nidaqmx.Task('read')

        tic = time.time()
        aotask.ao_channels.add_ao_voltage_chan(
               "Dev1/ao0",
               units=nidaqmx.constants.VoltageUnits.VOLTS)
        #
        aotask.timing.cfg_samp_clk_timing(
                     rate=apdrate,  # muestras por segundo
                     sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
#                     source='100kHzTimebase',
                     samps_per_chan=len(signaltodo))

        citask.ci_channels.add_ci_count_edges_chan(
                    counter='Dev1/ctr0')

        citask.timing.cfg_samp_clk_timing(
                  rate=apdrate,
                  sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                  source='100kHzTimebase',
                  samps_per_chan = len(signaltodo))
#
#        citask.triggers.start_trigger.cfg_anlg_edge_start_trig(
#                               trigger_source = "Dev1/ao0",
#                               trigger_slope = nidaqmx.constants.Slope.RISING)
#        citask.triggers.start_trigger.dig_edge_src="Dev1/ao0"
#        citask.triggers.start_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING

#        citask.triggers.start_trigger.anlg_edge_src = "Dev1/ao0"

#        aotask.triggers.start_trigger.dig_edge_src="Dev1/ctr0"

        aotask.triggers.start_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING
        aotask.triggers.start_trigger.delay_units = nidaqmx.constants.DigitalWidthUnits.TICKS
        aotask.triggers.start_trigger.delay = 320000
#        print(aotask.triggers.start_trigger.delay)
        # 320000 #default(ticks)
        # 300 #sample clock period
        # 0.003 #segs

        aotask.write(signaltodo,auto_start=False)
        tuc=time.time()
        aotask.start()
#        for i in range(Npix):
#            tac=time.time()
#            contando[:,i] = citask.read(number_of_samples_per_channel=len(signal))
#    #        APDtodo = citask.read(number_of_samples_per_channel=len(signal))
#            citask.wait_until_done()
#    #            citask.stop()
#            tec = time.time()
        tac=time.time()
        APDtodo = citask.read(number_of_samples_per_channel=len(signaltodo))
        citask.wait_until_done()
#            citask.stop()
        tec = time.time()
        aotask.wait_until_done()

#        pp.pprint(cdata)
toc = time.time()
#cuentas = np.zeros((len(contando[:,0]), Npix))
#for j in range(Npix):
#    for i in range(len(contando[:,0])-1):
#        cuentas[i,j] = contando[i+1,j] - contando[i,j]

APD = np.zeros((len(APDtodo)))
s=0
for j in range(Npix):
#    l = (j*Npix)-1
    l=s
    for i in range((len(signal)-1)):
        APD[i+s] = APDtodo[i+1+l] - APDtodo[i+l]
    s = s + len(signal)
#
#b=0
#for i in range(len(APD)):
#    if APD[i] != 0:
#        b = b+1
#print(b)

#print((toc-tic)*10**3, "milisegundos", tpix*Npix*10**3,"\ncitask solo = ", (tec-tac)*10**3, "\n ditask")#, (tuc-tupac)*10**3)
print((tec-tuc)*10**3,"ms total", (tec-tac)*10**3, "cada paso", "\n la cuenta da en s", Npix*(tec-tac))
plt.plot(signaltodo, '-')
#plt.plot(APDtodo, '-.r')
plt.plot(APD, '*g')

#jota = np.split(APD,Npix,axis=0)
#for i in range(len(jota)):
#    plt.plot(jota[:][i],'.')

#plt.plot(cuentas.ravel(), '*-m')
#plt.axis([0, len(signal)/2+1, -0.1, 1.1])
#plt.axis([500, 1500, -0.1, 2.1])
plt.show()
#for i in range(Npix):
#    print(contando[-1,i])

#dotask.stop()
#citask.stop()
#dotask.close()
#citask.close()


# %% ANALOG --> Cont (Npix mediciones con citask)
"""mando señal digital, y la leo con contadores.
"""
from nidaqmx.types import CtrTime
resolucionDAQ = 0.0003 * 2 * 25 # V => µm; uso el doble para no errarle
Npix=1
apdrate= 10**5
tpix = 0.01 *10**-3 # en milisegundos
Napd=int(apdrate*tpix)
Range = 10

Nsamples = int(np.ceil(Range/resolucionDAQ))
signal = np.zeros((Nsamples))
signal[100] = 5.1
#for i in range(len(signal)):
#    r = np.random.rand(1)[0]
#    if r > 0.99:
#        signal[i] = 5.1
#    else:
#        signal[i] = 0.0
#for i in range(int(2*len(signal)/3)):
#    signal[i] = True
#for i in range(10):
#    signal[i] = 0

#rate = (Range/resolucionDAQ) / (tpix*Npix)
rate = apdrate

Nposta = int((len(signal)/rate) * apdrate)  # == Npix*Napd

signaltodo = np.tile(signal, Npix)

contando = np.zeros((len(signal),Npix))
with nidaqmx.Task("read") as citask:
    with nidaqmx.Task("aotask") as aotask:
        
#dotask = nidaqmx.Task('write')
#citask = nidaqmx.Task('read')

        tic = time.time()
        aotask.ao_channels.add_ao_voltage_chan(
               "Dev1/ao0",
               units=nidaqmx.constants.VoltageUnits.VOLTS)
        #
        aotask.timing.cfg_samp_clk_timing(
                     rate=apdrate,  # muestras por segundo
                     sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
#                     source='100kHzTimebase',
                     samps_per_chan=len(signaltodo))

        citask.ci_channels.add_ci_count_edges_chan(
                    counter='Dev1/ctr0')

        citask.timing.cfg_samp_clk_timing(
                  rate=apdrate,
                  sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                  source='100kHzTimebase',
                  samps_per_chan = len(signaltodo))
#
#        citask.triggers.start_trigger.cfg_anlg_edge_start_trig(
#                               trigger_source = "Dev1/ao0",
#                               trigger_slope = nidaqmx.constants.Slope.RISING)
#        citask.triggers.start_trigger.dig_edge_src="Dev1/ao0"
#        citask.triggers.start_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING

#        citask.triggers.start_trigger.anlg_edge_src = "Dev1/ao0"

#        aotask.triggers.start_trigger.dig_edge_src="Dev1/ctr0"

        aotask.triggers.start_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING
        aotask.triggers.start_trigger.delay_units = nidaqmx.constants.DigitalWidthUnits.TICKS
        aotask.triggers.start_trigger.delay = 310000
#        print(aotask.triggers.start_trigger.delay)
        # 320000 #default(ticks)
        # 300 #sample clock period
        # 0.003 #segs

        aotask.write(signaltodo,auto_start=False)
        tuc=time.time()
#        aotask.start()
        for i in range(Npix):
            tac=time.time()
            contando[:,i] = citask.read(number_of_samples_per_channel=len(signal))
    #        APDtodo = citask.read(number_of_samples_per_channel=len(signal))
            citask.wait_until_done()
    #            citask.stop()
            tec = time.time()


#        aotask.wait_until_done()

#        pp.pprint(cdata)
toc = time.time()
cuentas = np.zeros((len(contando[:,0]), Npix))
for j in range(Npix):
    for i in range(len(contando[:,0])-1):
        cuentas[i,j] = contando[i+1,j] - contando[i,j]

#print((toc-tic)*10**3, "milisegundos", tpix*Npix*10**3,"\ncitask solo = ", (tec-tac)*10**3, "\n ditask")#, (tuc-tupac)*10**3)
print((toc-tuc)*10**3,"ms total", (tec-tac)*10**3, "cada paso", "\n la cuenta da en s", Npix*(tec-tac))

#plt.plot(signaltodo, '-')
#plt.plot(APDtodo, '-.r')
#plt.plot(APD, '*g')
plt.plot(contando[:,0])
#plt.plot(cuentas,'.-')
#plt.plot(cuentas.ravel(order='F'), '*-m')
#plt.axis([0, len(signal)/2+1, -0.1, 1.1])
#plt.axis([500, 1500, -0.1, 2.1])
plt.show()
for i in range(Npix):
    print(contando[-1,i])

b=0
for i in range(len(cuentas[:,0])):
    for j in range(Npix):
        if cuentas[i,j] !=0:
            b=b+1
print(b)
#dotask.stop()
#citask.stop()
#dotask.close()
#citask.close()

# %% ANALOG --> Cont (Npix mediciones con citask)
"""mando señal digital, y la leo con contadores.
"""
from nidaqmx.types import CtrTime
resolucionDAQ = 0.0003 * 2 * 25 # V => µm; uso el doble para no errarle
Npix=5
apdrate= 10**5
tpix = 0.01 *10**-3 # en milisegundos
Napd=int(apdrate*tpix)
Range = 10

Nsamples = int(np.ceil(Range/resolucionDAQ))
signal = np.zeros((Nsamples))
signal[100] = 5.1
#for i in range(len(signal)):
#    r = np.random.rand(1)[0]
#    if r > 0.99:
#        signal[i] = 5.1
#    else:
#        signal[i] = 0.0
#for i in range(int(2*len(signal)/3)):
#    signal[i] = True
#for i in range(10):
#    signal[i] = 0

#rate = (Range/resolucionDAQ) / (tpix*Npix)
rate = apdrate

Nposta = int((len(signal)/rate) * apdrate)  # == Npix*Napd

signaltodo = np.tile(signal, Npix)

contando = np.zeros((len(signal),Npix))
with nidaqmx.Task("read") as citask:
    with nidaqmx.Task("aotask") as aotask:
        
#dotask = nidaqmx.Task('write')
#citask = nidaqmx.Task('read')

        tic = time.time()
        aotask.ao_channels.add_ao_voltage_chan(
               "Dev1/ao0",
               units=nidaqmx.constants.VoltageUnits.VOLTS)
        #
        aotask.timing.cfg_samp_clk_timing(
                     rate=apdrate,  # muestras por segundo
                     sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
#                     source='100kHzTimebase',
                     samps_per_chan=len(signaltodo))

        citask.ci_channels.add_ci_count_edges_chan(
                    counter='Dev1/ctr0')

        citask.timing.cfg_samp_clk_timing(
                  rate=apdrate,
                  sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                  source='100kHzTimebase',
                  samps_per_chan = len(signaltodo))
#
#        citask.triggers.start_trigger.cfg_anlg_edge_start_trig(
#                               trigger_source = "Dev1/ao0",
#                               trigger_slope = nidaqmx.constants.Slope.RISING)
#        citask.triggers.start_trigger.dig_edge_src="Dev1/ao0"
#        citask.triggers.start_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING

#        citask.triggers.start_trigger.anlg_edge_src = "Dev1/ao0"

#        aotask.triggers.start_trigger.dig_edge_src="Dev1/ctr0"

        aotask.triggers.start_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING
        aotask.triggers.start_trigger.delay_units = nidaqmx.constants.DigitalWidthUnits.TICKS
        aotask.triggers.start_trigger.delay = 310000
#        print(aotask.triggers.start_trigger.delay)
        # 320000 #default(ticks)
        # 300 #sample clock period
        # 0.003 #segs

        aotask.write(signaltodo,auto_start=False)
        tuc=time.time()
        aotask.start()
        for i in range(Npix):
            tac=time.time()
            contando[:,i] = citask.read(number_of_samples_per_channel=len(signal))
    #        APDtodo = citask.read(number_of_samples_per_channel=len(signal))
            citask.wait_until_done()
    #            citask.stop()
            tec = time.time()


        aotask.wait_until_done()

#        pp.pprint(cdata)
toc = time.time()
cuentas = np.zeros((len(contando[:,0]), Npix))
for j in range(Npix):
    for i in range(len(contando[:,0])-1):
        cuentas[i,j] = contando[i+1,j] - contando[i,j]

#print((toc-tic)*10**3, "milisegundos", tpix*Npix*10**3,"\ncitask solo = ", (tec-tac)*10**3, "\n ditask")#, (tuc-tupac)*10**3)
print((toc-tuc)*10**3,"ms total", (tec-tac)*10**3, "cada paso", "\n la cuenta da en s", Npix*(tec-tac))

plt.plot(signaltodo, '-')
#plt.plot(APDtodo, '-.r')
#plt.plot(APD, '*g')
#plt.plot(contando)
#plt.plot(cuentas,'.-')
plt.plot(cuentas.ravel(order='F'), '*-m')
#plt.axis([0, len(signal)/2+1, -0.1, 1.1])
#plt.axis([500, 1500, -0.1, 2.1])
plt.show()
for i in range(Npix):
    print(contando[-1,i])

b=0
for i in range(len(cuentas[:,0])):
    for j in range(Npix):
        if cuentas[i,j] !=0:
            b=b+1
print(b)
#dotask.stop()
#citask.stop()
#dotask.close()
#citask.close()

# %% ANALOG --> Cont (dotask trigger)
"""mando señal digital, y la leo con contadores.
"""
from nidaqmx.types import CtrTime
resolucionDAQ = 0.0003 * 2 * 25 # V => µm; uso el doble para no errarle
Npix=5
apdrate= 10**5
tpix = 0.01 *10**-3 # en milisegundos
Napd=int(apdrate*tpix)
Range = 10

Nsamples = int(np.ceil(Range/resolucionDAQ))
signal = np.zeros((Nsamples))
signal[100] = 5.1
#for i in range(len(signal)):
#    r = np.random.rand(1)[0]
#    if r > 0.99:
#        signal[i] = 5.1
#    else:
#        signal[i] = 0.0
#for i in range(int(2*len(signal)/3)):
#    signal[i] = True
#for i in range(10):
#    signal[i] = 0

#rate = (Range/resolucionDAQ) / (tpix*Npix)
rate = apdrate

Nposta = int((len(signal)/rate) * apdrate)  # == Npix*Napd

signaltodo = np.tile(signal, Npix)
triggerrate = apdrate
trigger = np.zeros((len(signaltodo)),dtype="bool")  # np.zeros((10), dtype="bool")  # np.zeros((len(signaltodo)),dtype="bool")
trigger[500:1400] = True
trigger[2000:-5] = True
trigger[-3:-2] = True
#for i in range(int(len(trigger)/2)):
#    trigger[i*2] = True
#trigger[50:500] = 2
#trigger[400:900] = 3
#trigger[200:300] = False
#trigger[50:100] = False
#trigger[2000:2500] = False


contando = np.zeros((len(signal),Npix))
with nidaqmx.Task("read") as citask:
    with nidaqmx.Task("aotask") as aotask:
        with nidaqmx.Task("trigger") as dotask:
            with nidaqmx.Task("ditask") as ditask:
                tic = time.time()
#
#                ditask.di_channels.add_di_chan(
#                       "Dev1/port0/line7",
#                       line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
#    #
#                ditask.timing.cfg_samp_clk_timing(
#                             rate=apdrate,  # muestras por segundo
#                             sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
#    #                         source='do/StartTrigger',
#                             active_edge = nidaqmx.constants.Edge.RISING,
#                             samps_per_chan=len(trigger))

#                ditask.ci_channels.add_ci_count_edges_chan(
#                            counter='Dev1/ctr1')
    
#                ditask.timing.cfg_samp_clk_timing(
#                          rate=apdrate,
#                          sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
##                          source='100kHzTimebase',
#                          active_edge = nidaqmx.constants.Edge.RISING,
#                          samps_per_chan = len(signaltodo))
#                
                dotask.do_channels.add_do_chan(
                       "Dev1/port0/line6",
                       line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
    #
                dotask.timing.cfg_samp_clk_timing(
                             rate=triggerrate,  # muestras por segundo
                             sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
#                             source='100kHzTimebase',
                             active_edge = nidaqmx.constants.Edge.RISING,
                             samps_per_chan=len(trigger))
    
    #            dotask.triggers.start_trigger.cfg_dig_edge_start_trig(
    #                                trigger_source = "Dev1/port0/line6",
    #                                trigger_edge = nidaqmx.constants.Edge.RISING)
    
                aotask.ao_channels.add_ao_voltage_chan(
                       "Dev1/ao0",
                       units=nidaqmx.constants.VoltageUnits.VOLTS)
                #
                aotask.timing.cfg_samp_clk_timing(
                             rate=apdrate,  # muestras por segundo
                             sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
#                             source='di/StartTrigger',
                             active_edge = nidaqmx.constants.Edge.RISING,
                             samps_per_chan=len(signaltodo))
    
    
#                aotask.triggers.start_trigger.cfg_anlg_edge_start_trig(
#                                    trigger_source = "APFI0",  #APFI0 o 1
#                                    trigger_slope = nidaqmx.constants.Slope.RISING)


                citask.ci_channels.add_ci_count_edges_chan(
                            counter='Dev1/ctr0')

                citask.timing.cfg_samp_clk_timing(
                          rate=apdrate,
                          sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                          source='100kHzTimebase', # '100kHzTimebase'   'do/SampleClock'
                          active_edge = nidaqmx.constants.Edge.RISING,
                          samps_per_chan = len(signaltodo))

#                citask.timing.cfg_change_detection_timing(  # NO SIRVE
#                                  rising_edge_chan=u'PFI4',
##                                  falling_edge_chan=u'',
#                                  sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
#                                  samps_per_chan=len(signaltodo))

                triggerchannelname = "PFI4"

                aotask.triggers.start_trigger.cfg_dig_edge_start_trig(
                                    trigger_source = triggerchannelname)
#                                    #trigger_edge = nidaqmx.constants.Edge.RISING)
#                aotask.triggers.pause_trigger.dig_lvl_src = triggerchannelname
#                aotask.triggers.pause_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_LEVEL
#                aotask.triggers.pause_trigger.dig_lvl_when = nidaqmx.constants.Level.LOW


                citask.triggers.arm_start_trigger.dig_edge_src = triggerchannelname
                citask.triggers.arm_start_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_EDGE

#                citask.triggers.pause_trigger.dig_lvl_src = triggerchannelname
#                citask.triggers.pause_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_LEVEL
#                citask.triggers.pause_trigger.dig_lvl_when = nidaqmx.constants.Level.LOW
    #            dotask.triggers.start_trigger.cfg_dig_edge_start_trig(
    #                                trigger_source = "PFI8",
    #                                trigger_edge = nidaqmx.constants.Edge.RISING)

#                ditask.triggers.start_trigger.cfg_dig_edge_start_trig(
#                                    trigger_source = triggerchannelname)
#                
                
    #            citask.triggers.start_trigger.cfg_dig_edge_start_trig(  # no existe, solo arm.
    #                                trigger_source = "PFI8",
    #                                trigger_edge = nidaqmx.constants.Edge.RISING)
    

    #            citask.triggers.arm_start_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING
                
        #cfg_dig_edge_start_trig
    #            citask.triggers.start_trigger.cfg_anlg_edge_start_trig(
    #                                   trigger_source = "Dev1/ao0",
    #                                   trigger_slope = nidaqmx.constants.Slope.RISING)
    
        #        citask.triggers.start_trigger.dig_edge_src="Dev1/ao0"
        #        citask.triggers.start_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING
        
        #        citask.triggers.start_trigger.anlg_edge_src = "Dev1/ao0"
    
    #            aotask.triggers.reference_trigger.dig_edge_src = "Dev1/port0/line6"
    #            aotask.triggers.reference_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING
    #            nidaqmx._task_modules.triggering.start_trigger.StartTrigger.term = "Dev1/port0/line6"
    
    #            aotask.triggers.start_trigger.dig_edge_src = "Dev1/port0/line6"
    #            aotask.triggers.start_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING
    
    #            aotask.triggers.pause_trigger.dig_lvl_src = "Dev1/port0/line6"
    #            aotask.triggers.pause_trigger.dig_lvl_when = nidaqmx.constants.Level.HIGH
                
    
    #            citask.triggers.arm_start_trigger.trig_type.DIGITAL_EDGE
    #            citask.triggers.arm_start_trigger.
    
    
    
    
    #            citask.triggers.pause_trigger.dig_lvl_src = "Dev1/port0/line6"
    #            citask.triggers.pause_trigger.dig_lvl_when = nidaqmx.constants.Level.HIGH
    #            
    #            citask.triggers.start_trigger.dig_edge_src="Dev1/port0/line7" no andan!!
    #            citask.triggers.start_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING
    
    #            aotask.triggers.start_trigger.delay_units = nidaqmx.constants.DigitalWidthUnits.TICKS
    #            aotask.triggers.start_trigger.delay = 320000
    #
    #            print(aotask.triggers.start_trigger.delay)
                # 320000 #default(ticks)
                # 300 #sample clock period
                # 0.003 #segs
    

    #            dotask.triggers.start_trigger.delay_units = nidaqmx.constants.DigitalWidthUnits.SECONDS
    #            dotask.triggers.start_trigger.delay = 0.003
    #
    #            dotask.triggers.start_trigger.dig_edge_src = "Dev1/port0/line6sadas"
    #            dotask.triggers.start_trigger.dig_edge_edge = nidaqmx.constants.Edge.RISING


                aotask.write(signaltodo, auto_start=True)


                tuc=time.time()
                tac=time.time()

                dotask.write(trigger, auto_start = True)

                APDtodo = citask.read(number_of_samples_per_channel=len(signaltodo))

                dotask.write(trigger, auto_start = True)

#                counter2 = ditask.read(len(trigger))

    #            citask.wait_until_done()
        #            citask.stop()
                tec = time.time()
#                aotask.wait_until_done()
    
#                dotask.wait_until_done()

toc = time.time()

#cuentas = np.zeros((len(contando[:,0]), Npix))
#for j in range(Npix):
#    for i in range(len(contando[:,0])-1):
#        cuentas[i,j] = contando[i+1,j] - contando[i,j]

APD = np.zeros((len(APDtodo)))
s=0
for j in range(Npix):
#    l = (j*Npix)-1
    l=s
    for i in range((len(signal)-1)):
        APD[i+s] = APDtodo[i+1+l] - APDtodo[i+l]
    s = s + len(signal)
#
#b=0
#for i in range(len(APD)):
#    if APD[i] != 0:
#        b = b+1
#print(b)

#print((toc-tic)*10**3, "milisegundos", tpix*Npix*10**3,"\ncitask solo = ", (tec-tac)*10**3, "\n ditask")#, (tuc-tupac)*10**3)
print((tec-tuc)*10**3,"ms con aostart <=>", "solo citask", (tec-tac)*10**3)
print((toc-tic), " T total")

plt.plot(signaltodo, '-')
plt.plot(APDtodo, '-.r')
plt.plot(APD, '*g')
plt.plot(trigger)
plt.plot(counter2)
#jota = np.split(APD,Npix,axis=0)
#for i in range(len(jota)):
#    plt.plot(jota[:][i],'.')

#plt.plot(cuentas.ravel(), '*-m')
#plt.axis([0, len(signal)/2+1, -0.1, 1.1])
#plt.axis([500, 1500, -0.1, 2.1])
plt.show()
#for i in range(Npix):
#    print(contando[-1,i])

#dotask.stop()
#citask.stop()
#dotask.close()
#citask.close()

