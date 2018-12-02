# -*- coding: utf-8 -*-
"""
Created on Sat Dec  1 12:13:25 2018

@author: German
"""
# %%
# importamos el modulo pyplot, y lo llamamos plt
import matplotlib.pyplot as plt

#configuracion necesaria de pyplot para ver las imagenes en escala de grises
plt.rcParams['image.cmap'] = 'gray'
import numpy as np

from skimage import io
import time

image=io.imread("Z:/German/Rol/DM/Campaña de a 2/maxp.jpg")/255.0 # imread lee las imagenes con los pixeles codificados como enteros 
# en el rango 0-255. Por eso la convertimos a flotante y en el rango 0-1
plt.figure()
print("- Dimensiones de la imagen:")
print(image.shape)
plt.imshow(image,vmin=0,vmax=1)
#
#lena_rgb=io.imread("Z:/German/Rol/DM/Campaña de a 2/maxp.jpg")/255.0 
#plt.imshow(lena_rgb[:,:,0],vmin=0,vmax=1)
#plt.title("Canal Rojo")
#plt.figure()
#plt.imshow(lena_rgb[:,:,1],vmin=0,vmax=1)
#plt.title("Canal Verde")
#plt.figure()
#plt.imshow(lena_rgb[:,:,2],vmin=0,vmax=1)
#plt.title("Canal Azul")
#
#lena_red=np.copy(lena_rgb) # creo una copia de la imagen para preservar la original
#lena_red[:,:,1]=0
#lena_red[:,:,2]=0
#plt.title("Lena_ canal rojo")
#plt.imshow(lena_red)
#
#lena_red_green=np.copy(lena_rgb) # creo una copia de la imagen para preservar la original
#lena_red_green[:,:,2]=0
#plt.title("Lena_ sin canal azul")
#plt.imshow(lena_red_green)
plt.figure()
tic = time.time()
umb = 0.2
image2 = np.copy(image)
for i in range(image.shape[0]):
    for j in range(image.shape[1]):
        for l in range(image.shape[2]):
            if image2[i,j,l] < umb:
                image2[i,j,l] = 0
plt.imshow(image2,vmin=0,vmax=1)
print(time.time()-tic)

image3 = np.copy(image2)
for i in range(image.shape[0]):
    for j in range(image.shape[1]):
        for l in range(image.shape[2]):
            if image3[i,j,l] == 0:
                image3[i,j,l] = 1
plt.imshow(image3,vmin=0,vmax=1)

# %%
import cv2
import matplotlib.pyplot as plt
import numpy as np


im = cv2.imread('Quenya.jpg')
#plt.imshow(im,vmin=0,vmax=1)
imgray = cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
#ret,thresh = cv2.threshold(imgray,127,255,0) #original
ret,thresh = cv2.threshold(imgray,150,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C)
im2, contours, hierarchy = cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
cv2.imshow("original", imgray)
cv2.imshow("con contornos", im2)

im3=np.copy(im2)
for i in range(im2.shape[0]):
    for j in range(im2.shape[1]):
        if im2[i,j]==255:
            im3[i,j]=1

cv2.imshow("con 1s", im3)
plt.matshow(im3, cmap=plt.cm.gist_earth_r, origin='upper', interpolation='none')
plt.matshow(im3, cmap=plt.cm.gist_earth_r)

#im3=np.array(im2)
#im3.astype(float)
#im3[np.where(im3==0)] = np.nan*np.zeros(len(im3[np.where(im3==0)]))  # float("nan")

#N=im2.shape[0]
#X = np.linspace(-2, 2, int(N))
#Y = np.linspace(-2, 2, int(N))
#pcolormesh
#p = ax.pcolor(X, Y, np.flip(im2[:,:N],0), cmap=plt.cm.jet, vmin=0)
#cb = fig.colorbar(p)
#ax.set_xlabel('x [um]')
#ax.set_ylabel('y [um]')
# %%
import cv2

image = cv2.imread("clouds.jpg")
gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#plt.imshow(image)
#plt.imshow(gray_image)
cv2.imshow("Over the Clouds", image)
cv2.imshow("Over the Clouds - gray", gray_image)
cv2.waitKey(0)
cv2.destroyAllWindows()
cv2.drawContours(image, contours, -1, (0,255,0), 3)







