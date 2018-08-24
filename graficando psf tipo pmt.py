
import numpy as np
import matplotlib.pyplot as plt
import time
# %%

#name= "imagenScan.npz"
#f=open(name,"r")
#data=np.load(name)
#f.close()
# %%

data = np.ones((100,100))
x = np.linspace(0, 1, len(data))
y = x

X, Y = np.meshgrid(x, y)

fig, ax = plt.subplots()
p = ax.pcolor(X, Y, data, cmap=plt.cm.jet, vmin=0)
cb = fig.colorbar(p)
ax.set_xlabel('x [um]')
ax.set_ylabel('y [um]')


# %%xy punto a punto)
"""simulador de señal del pmt (xy punto a punto)"""
L = 20
N = 20
a = np.zeros((L, L))
signal = np.zeros((L, L, N), dtype='bool')
tiic = time.time()

for i in range(L):
    for j in range(L):

        for e in range(N):
            r = np.random.rand(1)[0]
    #        print(r)
            if 0.7 < r:
                signal[i, j, e] = True

    #    plt.plot(signal)

for i in range(10):
    for j in range(10):
        for e in range(N):
            signal[i+1, j+1, e] = True
toc = time.time()
print(toc-tiic, "el primero")
#
x = np.linspace(0, 1, L)
y = x
X, Y = np.meshgrid(x, y)
fig, ax = plt.subplots()
ax.set_xlabel('x [um]')
ax.set_ylabel('y [um]')
# """cuento los picos de la señal"""
for i in range(2):
    tic = time.time()
    for j in range(L):
        for p in range(N-1):
            if signal[i, j, p+1] > signal[i, j, p]:
                a[i, j] = a[i, j] + 1
    toc = time.time()
    print(toc-tic, "segundos")
    
p = ax.pcolor(X, Y, a, cmap=plt.cm.jet, vmin=0)
cb = fig.colorbar(p)
toc = time.time()
print(toc-tiic)
# %%

x = np.linspace(0, 1, L)
y = x

X, Y = np.meshgrid(x, y)

fig, ax = plt.subplots()
p = ax.pcolor(X, Y, a, cmap=plt.cm.jet, vmin=0)
cb = fig.colorbar(p)
ax.set_xlabel('x [um]')
ax.set_ylabel('y [um]')

# %%en xy, midendo continuo
"""simulador de señal del pmt (en xy, midendo continuo)"""

N = 1000  # puntos de mi medicion con el APD
pasos = 5  # subdiviciones en el tiempo
L = 10
a = np.zeros((pasos, L))
signal = np.zeros((L, N), dtype='bool')
tic = time.time()

for j in range(L):

    for e in range(N):
        r = np.random.rand(1)[0]
#        print(r)
        if 0.8 < r:
            signal[j, e] = True

for j in range(L):
    for c in range(pasos):
        b = 0
        for p in range(int(N/pasos)):
            if signal[j, p+c*10]:
                b = 1 +10*c + 100*j
        a[c, j] = b

#plt.plot(signal[0, :])
# %%

x = np.linspace(0, 1, L)
y = np.linspace(0, 2, pasos)

X, Y = np.meshgrid(x, y)

fig, ax = plt.subplots()
p = ax.pcolor(X, Y, a[:,:], cmap=plt.cm.jet, vmin=0)
cb = fig.colorbar(p)
ax.set_xlabel('x [um]')
ax.set_ylabel('y [um]')

# %%solo en x
"""simulador de señal del pmt (solo en x)"""

N = 1000  # puntos de mi medicion con el APD
pasos = 100  # subdiviciones en el tiempo
L = pasos
a = np.zeros((L))
signal = np.zeros((N), dtype='bool')
tic = time.time()

for e in range(N):
    r = np.random.rand(1)[0]
#        print(r)
    if 0.8 < r:
        signal[e] = True

for c in range(pasos):
    b = 0
    for p in range(int(N/pasos)):
        if signal[p+c*10]:
            b = b+1
    a[c] = b

x = np.linspace(0, 1, pasos)
plt.plot(x, a, '*-')

# %%
N = 20
N2 = int(N/2)
stepY = 1
barridoLTR = np.linspace(0, 10, N2)
barridoRTL = np.linspace(10, 0, N2)
barridox = np.append(barridoLTR, barridoRTL, axis=0)
barrido1 = np.linspace(0, 0, N)
#barrido2 = np.linspace(stepY, stepY, N2)
#barridoy = np.append(barrido1, barrido2, axis=0)

data = np.zeros((N, N, 2))
for j in range(N):
    for i in range(N):
        data[i, j, :] = [barridox[i], barrido1[i]+2*stepY*j]


data7 = data[:, 0]
for k in range(1, 5):
    data7 = np.append(data7, data[:, k], axis=0)
plt.plot(data7, '.-')
plt.plot(barridox, '-r')
plt.plot(barrido1, '-g')

# %%

plt.axis([0, 20, 0, 1])

for i in range(20):
    y = np.random.random()
    plt.scatter(i, y)
    plt.pause(0.05)

plt.show()