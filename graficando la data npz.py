
import numpy as np
import matplotlib.pyplot as plt
import time
import multiprocessing as mp
import pyqtgraph.ptime as ptime

# %% Las rampas que miden cuando va y vuelve rapido
""" con m = 1 tengo ida y vuelta simetricas"""
a = 120  # aceleracion um/ms2
#m = 15  # Velocidad de vuelta respecto a la de ida
av = a # a vuelta


aaa=time.time()
bbb=ptime.time()
# la calibracion es 1 µm = 40 mV; ==> 0.3 mv = 0.0075 um = 7.5 nm
reDAQ = 0.6*(10**-3)*25
R = 10  # rango
Npix = 500  # numerode pixeles
tpix = 0.01  # tiempo de pixel en ms
T = tpix * Npix  # tiempo total de la linea
V = (R/T)  # velocidad de la rampa
#V = 100  # um/ms
m=25/V
#Npuntos= int(R / reDAQ)
#rate = Npuntos / T

rate = 10*5
Npuntos = int(rate*T)
print((ptime.time()-bbb)*10**3, (time.time()-aaa)*10**3)
x0 = 0
V0 = 0  #==> c=0
#quiero ver cuando alcanza velocidad V (a*ti =V )
ti = V / a
#xi = a*ti**2 + V0*ti  # no lo uso
Ni = int(np.ceil(ti * rate))
tiempoi=np.linspace(0,ti,Ni)
xti=np.zeros(Ni)
for i in range(Ni):
    xti[i] = 0.5*a*(tiempoi[i]**2)  # + V0*tiempoi[i]



rampax = np.linspace(xti[-1],R+xti[-1],int(Npuntos))

#ahora la otra parte. Llega con vel V a xr=R+xi, en tr=T+ti
xr = R+xti[-1]
tr = T +ti
# ==> tr=0 por comodidad, despues lo corro
#a*tr + c =V. 0.5*a*tr**2 + c*tr + d = xr
c=V
d=xr


##Busco a que tiempo alcanza velocidad -m*V: -a*tcasi +c = -m*V


tcasi =-(c+(m*V))/-a
xcasi = -0.5*a*tcasi**2 + c*tcasi + d  # no lo uso
Ncasi = 12#int(np.ceil(tcasi * rate))
tiempocasi=np.linspace(0,tcasi,Ncasi)
xtcas=np.zeros(Ncasi)
for i in range(Ncasi):
    xtcas[i] = -0.5*a*(tiempocasi[i]**2) + c*tiempocasi[i] + d

# por ultimo, quiero que baje con vel = -m*V lineal. tarda t=x/-m*V


tflip = m*V/(av)
xflip = 0.5*(av)*(tflip**2)

tfin=(xflip-xtcas[-1]/(-m*V)) + tr + tcasi
Nfin = 10#abs(int(np.ceil(((xflip-xtcas[-1])/((-m*V))*rate))))
#Nfin = Npuntos /m

# Una curva mas para la repeticion de cada señal. 
#nuevamente salgo de vel = 0 y voy para atras en el tiempo
#  en t0 v=0, x=0;; a*tflip = m*V
"""
# -a*tfin + f = -m*V ==> f = m*V/a*tfin ;;; -a *tflip + f = 0 ==> tflip = f/a ;;; 
#f = -m*V/(-a*tfin)
"""

if xtcas[-1] < xflip:
    if xtcas[-1] < 0:
        q = np.where(xtcas<=0)[0][0]
        xtcas = xtcas[:q]
        print("xtcas < 0")
        rfin = np.linspace(0,0,4)

    else:
        q = np.where(xtcas<=xflip)[0][0]
        xtcas = xtcas[:q]
        rfin = np.linspace(xflip,0,Nfin)
        print("xtcas < xflip")
    rflip = np.linspace(0,0,2)
else:

    rfin= np.linspace(xtcas[-1],xflip,Nfin)
    
    Nflip = 11#int(np.ceil(tflip * rate))
    tiempoflip=np.linspace(0,tflip,Nflip)
    print("normal")
    rflip=np.zeros(Nflip)
    for i in range(Nflip):
        rflip[i] = 0.5*(av)*(tiempoflip[i]**2)
    
    rflip = np.flip(rflip,axis=0)

    #rflip =np.flip(xti,axis=0)


barridox = np.concatenate((xti[:-1], rampax[:], xtcas[1:], rfin[1:-1],rflip[:]))
verxi= np.concatenate((xti[:-1],np.zeros(len(rampax)-1),np.zeros(len(xtcas)),np.zeros(len(rfin)-2), np.zeros(len(rflip))))
verxcas= np.concatenate((np.zeros(len(xti)-1),np.zeros(len(rampax)-1), xtcas,np.zeros(len(rfin)-2), np.zeros(len(rflip))))
verfin= np.concatenate((np.zeros(len(xti)-1),np.zeros(len(rampax)-1),np.zeros(len(xtcas)),rfin[1:-1], np.zeros(len(rflip))))
verflip =np.concatenate((np.zeros(len(xti)-1),np.zeros(len(rampax)-1),np.zeros(len(xtcas)),np.zeros(len(rfin[1:-1])), rflip))
print(Ni, "Ni\n",Npuntos, "Npuntos\n", Ncasi, "Ncasi\n",
      Nfin, "Nfin\n", Nflip, "Nflip\n")

#tvuelta = np.linspace(0, (-xcasi/(-m*V)), Nfin)+tr+tcasi

#ejex = np.concatenate((tiempoi[:-1],np.linspace(ti,tr,Npuntos)[:] , tiempocasi[:]+tr,
#                       tvuelta[1:-1], tiempoflip+tvuelta[-1]))

#resta=np.zeros((len(barridox)))
#for i in range(1,len(barridox)):
#    resta[i] = barridox[i] - barridox[i-1]

#p.start()
plt.figure(1)
plt.plot(barridox,'.-')

plt.plot(verfin,'.-c')
plt.plot(verxcas, '.-g')
plt.plot(verxi, '.-m')
plt.plot(verflip, '.-y')
#plt.plot(resta,'r.-')
#plt.xlim(-0.5,10)
#plt.ylim(-0.1,0.1)
#
#plt.plot(ejex, barridox, '.-')
##
#plt.plot(ejex,verfin, '.c')
#plt.plot(ejex,verxcas, '.g')
#plt.plot(ejex,verxi, '.m')
#
#plt.plot(ejex,resta,'*-r')

#plt.plot(xti)
#cuantos puntos tengo entre tcasi y tr?

#Ny=3
#
#
#startY = 0
#stepy = R/Ny
#rampay = np.ones(len(barridox))*startY
#
#muchasrampasy=np.tile(rampay,(Ny,1))
#barridoychico=np.zeros((Ny,len(rampay)))
#
#p = len(xti)-1 + len(rampax)-1 + int(len(xtcas))
#for i in range(Ny):
#
#    barridoychico[i,:p]= muchasrampasy[i,:p] + (i)*stepy
#    barridoychico[i,p:]= muchasrampasy[i,p:] + (i+1)*stepy
#
#
#todo = np.tile(barridox,Ny)
#barridoy = barridoychico.ravel()
###
#plt.figure(2)
#plt.plot(todo,'.-')
#plt.plot(barridoy, 'y')
#
#plt.show()
# %% Con m=1, y este ajuste, tengo rampas escalonadas
Ny=3


startY = 0
stepy = R/Ny
rampay = np.ones(len(barridox))*startY

muchasrampasy=np.tile(rampay,(Ny,1))
barridoychico=np.zeros((Ny,len(rampay)))

p = len(xti)-1 + len(rampax)-1 + int(len(xtcas))
for i in range(Ny):
    j = 2*i
    barridoychico[i,:p]= muchasrampasy[i,:p] + (j)*stepy
    barridoychico[i,p:]= muchasrampasy[i,p:] + (j+1)*stepy


todo = np.tile(barridox,Ny)
barridoy = barridoychico.ravel()
##
plt.figure(2)
plt.plot(todo,'.-')
plt.plot(barridoy, 'y')

plt.show()

# %%
# Los puntos de mas, pasados a APD

NoffR = len(barridox)-len(rampax)-3
NoffL = len(xti)

ttotal = (len(barridox)-3)/rate
tposta = len(rampax)/rate  # = T
toffR = NoffR/rate
toffL = NoffL/rate

apdrate = 10**5
ms=10**-3
Nposta = tposta*ms* apdrate  # = Npix*Napd
NoffR = int(np.round(toffR *ms *apdrate))
NoffL = int(np.round(toffL *ms *apdrate))
#Ntotal = ttotal*ms*apdrate

#tengoq ue descartar NoffL puntos a izquierda y NoffR puntos a derecha de cada linea.



# %%
"""
#medicion del APD
Ny=3
apdrate = 10**5
Napd = 2  # int( apdrate * (tpix *10**-3))
Npix = Ny
Ntirar = 2
Nramp = Ntirar + Npix  # len(barridox)  # len(rampay)  # el largo de cara rampa sola (completa).
Ntotal = Nramp * Ny  # len(todo)  # len(barridoy)  # que son todos los puntos de las rampas, despues corto.
APDtodo = np.ones((int(Ntotal*Napd)))

print(Ny, "Npix\n", Napd, "Napd\n", Nramp, "Nramp\n")

APDline = np.split(APDtodo, Npix)
for i in range(Ny):
    for j in range(len(APDline[i])):
        APDline[i][j] = i*j+j+i

i=0
# tengo un vector grande que mide Napd*Nramp*Ny. lo subdivido en Ny vectores que miden Nramp*Napd
# de cada vector, tengo solo Npix*Napd puntos que me interesan. Tengo que tirar (Nramp-Npix)*Napd
#luego me quedarian Ny(=Npix) vectores de largo Npix*Napd. y al final tomo el ultimo valor de esos (ya que el ctr suma)
#==> Ny vectores de largo Npix



cuentas = np.zeros((Npix,Ny))
for i in range(Ny):
    aux=0
    for j in range(1, Npix):
        e = (j * Napd)-1
        cuentas[j,i] = APDline[i][e]  #esto esta bien, pero saca solo el final

#Tendria que hacerlo mas metodico, sacando los puntos que corresponden. 
#Para eso tengo que saber cuando vale de verdad Ntirar
#"""



# %%
#por otro lado, creo que si lo hago en un solo vector largo es ams facil.
#medicion del APD
Ny=Npix
apdrate = 10**5
Napd = int( apdrate * (tpix *10**-3))

Ntirar = NoffL+NoffR
Nramp = Ntirar + Npix  # len(barridox)  # len(rampay)  # el largo de cara rampa sola (completa).
Ntotal = Nramp * Ny  # len(todo)  # len(barridoy)  # que son todos los puntos de las rampas, despues corto.
APDtodo = np.ones((int(Ntotal*Napd)))

APDline = np.split(APDtodo, Npix)
for i in range(Ny):
    for j in range(len(APDline[i])):
        APDline[i][j] = i*j+j+i


ooo=len(APDtodo)
APDtodo =  np.array(APDline).ravel()  #np.linspace(1,ooo,ooo) #
Nramp = Npix + NoffL + NoffR
contando = np.zeros((Npix*Ny))
s=0
for j in range(Ny):
    l = ((j*(Nramp*Napd)))  # avanza de a rampas
    for i in range(Npix):
        ef = ((i+2)*Napd)-1  # avanza de a pixels
        ei = ((i+1)*Napd)-1  # avanza de a pixels
        contando[(i)+s] = APDtodo[(ef+l)+NoffL] - APDtodo[(ei+l)+NoffL]
#        print(contando[(i)+s])
    s=s+Npix
#    print("-s-        ",s)
#print(contando, "<@>")
#print(APDtodo)
#luego, spliteo contando y ya tengo los vectores imagen:

imagin = np.split(contando, Ny)
plt.plot(imagin)
plt.show()




# %%

# %%
resolucionDAQ = 0.6*(10**-3)*25
R = 10.0  # rango
Npix = 500  # numerode pixeles
a = 120.0  # aceleracion um/ms2
tpix = 0.1  # tiempo de pixel en ms

T = tpix * Npix  # tiempo total de la linea
V = (R/T)*Npix  # velocidad de la rampa


startX = 0

ti = V / a
xi = 0.5*a*(ti**2) # + startX
xipun=(ti/resolucionDAQ)
xipuntos = int(np.ceil(xi / resolucionDAQ))

dti = ti/xipun

xini = np.zeros(xipuntos)
for i in range(xipuntos):
    xini[i] = 0.5*a*((i * dti)**2) + startX

xr = xi + R
tr = ti + T

m = 1 + 1
# si busco una velocidad de vuelta 10 veces mayor a la de ida
tcasi = m * V / a  # Vdeseada + V = m * V
xcasi = -0.5 * a * (tcasi**2) + V * tcasi  # +xr
xfinpun = abs((xcasi)/resolucionDAQ)
xfinpuntos = int(np.ceil(xfinpun))

dtf = tcasi/xfinpun

xfin = np.zeros(abs(xfinpuntos))
for i in range(xfinpuntos):
    xfin[i] = (-0.5*a*((i * dtf)**2) + V * (i*dtf)) + xr + startX

Npuntos= R / resolucionDAQ
sampleRate = Npuntos / T
barrido= np.linspace(xini[-1], xfin[0], int(Npuntos))

#Nfinal = int(np.ceil((xcasi/m*V) * (sampleRate)))
#Nvuelta = int(np.ceil(xcasi+xr)/resolucionDAQ)-40
    
#Nvuelta = abs(int(np.ceil(((xcasi+xr)/-m*V) *sampleRate)))
Nvuelta = abs(500)
rectafinal = np.linspace(xfin[-1], startX, Nvuelta)

barridox = np.concatenate((xini[:-1],barrido,xfin[1:-1], rectafinal))

pixelsoffini = int(np.ceil(ti*sampleRate))

print(xipuntos, "xipuntos\n",int(Npuntos), "Npuntos", xfinpuntos, "xfinpuntos\n",
      Nvuelta, "Nvuelta", pixelsoffini, "pixelsoffini\n")

plt.plot(barridox,'.-')
plt.show()

resta=np.zeros((len(barridox)))
for i in range(1,len(barridox)):
    resta[i] = barridox[i] - barridox[i-1]

plt.plot(resta,'.r')

#plt.xlim(670,700)
#plt.ylim(8,12)

#plt.figure(2)
#plt.plot(resta,'.r')

# %%

Napd=100
a=np.linspace(0,10,2*Napd)
b=np.split(a,2)
c=b[0]
d=np.flip(b[1],axis=0)
plt.plot(c, 'b')
plt.plot(d, 'g')
plt.plot(a, '--r')
# %%
tic=time.time()
N=2
ms = 1 / 1000
t = 10 * ms
apdrate = 10**3
Napd = int(apdrate*t)
#APDtodo = np.tile(np.linspace(0,10,Napd),N)
APDtodo = [0,1,2,3,4,5,6,7,8,9,0,1,2,3,4,5,6,7,8,9]
aux = 0
APD = np.split(np.array(APDtodo), N)
cuentas = np.zeros(N)
for j in range(N):
    for c in range(Napd-1):
        if APD[j][c] < APD[j][c+1]:
            aux = aux + 1
    cuentas[j] = aux + np.random.rand(1)[0]
print((time.time()-tic)*1000/N)
# %%

tic=time.time()
N=100 # para promediar tiempos
for j in range(N):
    ms = 1 / 1000
    t = 10 * ms
    apdrate = 10**5
    Napd = int(apdrate*t)
    APD = np.linspace(0,10,Napd)
    aux = 0
    for c in range(Napd-1):
        if APD[c] < APD[c+1]:
            aux = aux + 1
print((time.time()-tic)*1000/N)
# %%
timestr = time.strftime("%Y%m%d-%H%M%S")
aaa = str("image-" + timestr)
print (aaa)
# %% leyendo data en npz
#from os.path import join as pjoin

#filename = 'imagenScan.npz'
##path_to_file = pjoin("C:", "foo", "bar", "baz", filename)
#coso = "C:/Users/Santiago/Desktop/Germán Tesis de lic/Winpython (3.5.2 para tormenta)/WinPython-64bit-3.5.2.2/notebooks"
#name = str(coso + "/"+filename)
#f=open(name,"r")
#data=np.load(name)
#f.close()
## %%
psf = data['psf']
x = np.linspace(0, 1, len(psf))
y = x

X, Y = np.meshgrid(x, y)

fig, ax = plt.subplots()
p = ax.pcolor(X, Y, psf, cmap=plt.cm.jet, vmin=0)
cb = fig.colorbar(p)
ax.set_xlabel('x [um]')
ax.set_ylabel('y [um]')

# %% saveando las cosas a tiff
from PIL import Image
name = 'test.tiff'
#data = np.random.randint(0, 255, (100,100)).astype(np.uint8)
im = Image.fromarray(psf)
im.save(name)

# %% leyendo las cosas de tiff

from PIL import Image
name = 'imagenScan.tiff'
algo = Image.open(name)
#algo.show()
imarray = np.array(algo)
#nam = 'test.tiff'
#f = open(name,'r')
#algo = np.load(name)
#f.close()

# %%
a = imarray

x = np.linspace(0, 1, len(a))
y = x

X, Y = np.meshgrid(x, y)

fig, ax = plt.subplots()
p = ax.pcolor(X, Y, a, cmap=plt.cm.jet, vmin=0)
cb = fig.colorbar(p)
ax.set_xlabel('x [um]')
ax.set_ylabel('y [um]')
# %%
## %%xy punto a punto)
#"""simulador de señal del pmt (xy punto a punto)"""
#L = 20
#N = 20
#a = np.zeros((L, L))
#signal = np.zeros((L, L, N), dtype='bool')
#tiic = time.time()
#
#for i in range(L):
#    for j in range(L):
#
#        for e in range(N):
#            r = np.random.rand(1)[0]
#    #        print(r)
#            if 0.7 < r:
#                signal[i, j, e] = True
#
#    #    plt.plot(signal)
#
#for i in range(10):
#    for j in range(10):
#        for e in range(N):
#            signal[i+1, j+1, e] = True
#toc = time.time()
#print(toc-tiic, "el primero")
##
#x = np.linspace(0, 1, L)
#y = x
#X, Y = np.meshgrid(x, y)
#fig, ax = plt.subplots()
#ax.set_xlabel('x [um]')
#ax.set_ylabel('y [um]')
## """cuento los picos de la señal"""
#for i in range(2):
#    tic = time.time()
#    for j in range(L):
#        for p in range(N-1):
#            if signal[i, j, p+1] > signal[i, j, p]:
#                a[i, j] = a[i, j] + 1
#    toc = time.time()
#    print(toc-tic, "segundos")
#    
#p = ax.pcolor(X, Y, a, cmap=plt.cm.jet, vmin=0)
#cb = fig.colorbar(p)
#toc = time.time()
#print(toc-tiic)
## %%
#
#x = np.linspace(0, 1, L)
#y = x
#
#X, Y = np.meshgrid(x, y)
#
#fig, ax = plt.subplots()
#p = ax.pcolor(X, Y, a, cmap=plt.cm.jet, vmin=0)
#cb = fig.colorbar(p)
#ax.set_xlabel('x [um]')
#ax.set_ylabel('y [um]')
#
## %%en xy, midendo continuo
#"""simulador de señal del pmt (en xy, midendo continuo)"""
#
#N = 1000  # puntos de mi medicion con el APD
#pasos = 5  # subdiviciones en el tiempo
#L = 10
#a = np.zeros((pasos, L))
#signal = np.zeros((L, N), dtype='bool')
#tic = time.time()
#
#for j in range(L):
#
#    for e in range(N):
#        r = np.random.rand(1)[0]
##        print(r)
#        if 0.8 < r:
#            signal[j, e] = True
#
#for j in range(L):
#    for c in range(pasos):
#        b = 0
#        for p in range(int(N/pasos)):
#            if signal[j, p+c*10]:
#                b = 1 +10*c + 100*j
#        a[c, j] = b
#
##plt.plot(signal[0, :])
## %%
#
#x = np.linspace(0, 1, L)
#y = np.linspace(0, 2, pasos)
#
#X, Y = np.meshgrid(x, y)
#
#fig, ax = plt.subplots()
#p = ax.pcolor(X, Y, a[:,:], cmap=plt.cm.jet, vmin=0)
#cb = fig.colorbar(p)
#ax.set_xlabel('x [um]')
#ax.set_ylabel('y [um]')
#
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
barrido1 = np.linspace(0, 0, N2)
barrido2 = np.linspace(stepY, stepY, N2)
barridoy = np.append(barrido1, barrido2, axis=0)

data = np.zeros((N, N, 2))
for j in range(N):
    for i in range(N):
        data[i, j, :] = [barridox[i], barridoy[i]+2*stepY*j]


data7 = data[:, 0]
for k in range(1, 5):
    data7 = np.append(data7, data[:, k], axis=0)
plt.plot(data7, '.-')
plt.plot(barridox, '-r')
plt.plot(barrido1, '-g')

#%%
N = 20
stepY = 1
barridox = np.append(0, np.linspace(2, 10, N))
#barridoRTL = np.linspace(10, 0, N2)
#barridox = np.append(barridoLTR, barridoRTL, axis=0)
barrido1 = np.append(0, np.linspace(2, 2, N))
#barrido2 = np.linspace(stepY, stepY, N2)
#barridoy = np.append(barrido1, barrido2, axis=0)

data = np.zeros((N, N, 2))
for j in range(N):
    for i in range(N):
        data[i, j, :] = [barridox[(i+1)*(-1)**j],
            barrido1[i+1]+stepY*j]


data7 = data[:, 0]
for k in range(1, 5):
    data7 = np.append(data7, data[:, k], axis=0)
plt.plot(data7, '.-')
plt.plot(barridox[1:], '-r')
plt.plot(barrido1[1:], '-g')

#%%
N = 20
N2 = int(N/2)
stepY = 1
barridoLTR = np.linspace(0, 10, N2)
barridoRTL = np.linspace(10, 0, N2)
barridox = np.append(barridoLTR, barridoRTL, axis=0)
barrido1 = np.linspace(0, 0, N2)
barrido2 = np.linspace(stepY, stepY, N2)
barridoy = np.append(barrido1, barrido2, axis=0)

data = np.zeros((N, N, 2))

for j in range(N2):
    for i in range(N):
        data[i, j, :] = [barridox[i],
            barridoy[i]+ 2*stepY*j]


data7 = data[:, 0]
for k in range(1, 5):
    data7 = np.append(data7, data[:, k], axis=0)
plt.plot(data7, '.-')
plt.plot(barridox[1:], '-r')
plt.plot(barrido1[1:], '-g')

# %%

plt.axis([0, 20, 0, 1])

for i in range(20):
    y = np.random.random()
    plt.scatter(i, y)
    plt.pause(0.05)

plt.show()

# %% cosas utiles para textos
>>> "Hello {}, my name is {}".format('john', 'mike')
'Hello john, my name is mike'.

>>> "{1}, {0}".format('world', 'Hello')
'Hello, world'

>>> "{greeting}, {}".format('world', greeting='Hello')
'Hello, world'