#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov  6 11:32:34 2023

@author: lily
"""
############################# Calcul de l'ombre#######################################
import math
import pvlib
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
import pandas as pd
from pvlib import location
from datetime import datetime, timedelta
import time
from tqdm import tqdm
import matplotlib as mpl
import matplotlib.image as mpimg


def recherche_nbr_PV(lon_serre, lon_PV, damier, puit_lux):
    
    '''Trouve automatiquement le nombre de PV que l'on peut mettre sur une rangée en fonction de la longueur du
    PV et eventuellement du puit de lumière dans le cas d'un damier et de la longueur d'une serre. '''
    if damier!= False:  
       recherche= lon_PV
       nbr_PV=0
       while lon_serre>= recherche:
           nbr_PV+=1
           recherche+= lon_PV+ puit_lux
    else:
       recherche=lon_PV
       nbr_PV=0
       while lon_serre>= recherche:
           nbr_PV+=1
           recherche+= lon_PV
        
    return nbr_PV

def recherche_rang (larg_PV, couverture, larg_serre, betaPV):
    ''' Trouve automatiquement le nombre de rang nécessaire pour couvrir selon le taux de couverture 
    On part du principe que si le taux de couverture est de 50 % il faut recouvrir la moitie (0.5) de la bande de toit
    C'est pourquoi on ne travaille qu'avec larg_PV/transverse. On renvoit le nombre de rang ainsi que le taux de couverture
    réalisé qui peut être un petit peu inférieur à celui demandé en fonction des charactéristiques des PV et de la serre '''
    taux_couv=0
    couverture= couverture/100
    compteur=0
    transverse= larg_serre / math.cos(betaPV) # longueur du V du toit 
    while taux_couv < couverture and taux_couv+larg_PV/transverse<couverture:
        taux_couv+= larg_PV/transverse
        compteur+=1
    return compteur, taux_couv

def recherche_rang_asymetrique (larg_PV, couverture, petit_cote, grand_cote, petit_angle, grand_angle):
    ''' même chose mais dans le cas d'une serre asymétrique (donc avec deux angles différents)'''
    taux_couv=0
    couverture= couverture/100
    compteur=0
    grande_diag= grand_cote/math.cos(grand_angle)
    petite_diag= petit_cote/math.cos(petit_angle)
    while taux_couv<couverture and taux_couv+larg_PV/ (grande_diag+petite_diag)<couverture: 
        taux_couv+= larg_PV/ (petite_diag+grande_diag)
        compteur+=1
    return compteur, taux_couv

##########angles################            
def angles(LAT, LON):
    ''' récupère en dataframe tout les angles solaires (élevation et azimut) à cette localisation'''
    times = pd.date_range('2005-01-01', periods=8760, freq='1H', tz='Europe/Paris')
    loc = location.Location(LAT, LON, tz=times.tz)
    sp = loc.get_solarposition(times)
    # Récupération des angles solaires via le module 'loc' de pvlib
    solar_angles_df = sp[['elevation', 'azimuth']]
    return solar_angles_df

def angles_jour (solar_angles_df, date_debut):
    '''extrait les angles à la date voulue'''
    
    # Convertir la date string en pandas Timestamp
    date_obj = pd.to_datetime(date_debut, format='%Y/%m/%d', yearfirst=True, utc=True)
    date_obj = date_obj.replace(year=2005) #on prend l'année 2005, c'est les mêmes angles quelques soient les années. 
    
   # Obtenir la plage horaire correspondant à la journée spécifique
    date_start = date_obj.replace(hour=0, minute=0, second=0)
    date_end = date_obj.replace(hour=23, minute=59, second=59)
    
    # Filtrer les données pour la journée spécifique
    angles_date = solar_angles_df[(solar_angles_df.index >= date_start) & (solar_angles_df.index <= date_end)]
    
    # Extract thetaS (elevation) and gammaS (azimuth) for the specific date
    thetaS = angles_date['elevation']
    gammaS = angles_date['azimuth']

    return thetaS, gammaS

############calculs ombre et panneau  ###############

def calcul_ombre (lon_serre, larg_serre, lon_PV, larg_PV, nbr_PV, alphaPV, betaPV, angles_df, h_serre, date_debut, PV, nbr_rang, nbr_chap, h_toit, damier):
    ''' calcule l'ombre heure par heure sur une journée''' 
    cos= math.cos 
    sin= math.sin

    #initialisation 
    
    thetaS, gamaS = angles_jour(angles_df, date_debut)   

    H= h_serre + h_toit
    if damier!= False: 
        Ombre = [[[[[] for _ in range(4)] for _ in range (24)] for _ in range(int(nbr_PV*nbr_rang))] for chap in range (int(nbr_chap))] 
       
        for chap in range (int(nbr_chap)):
            for indice in range (nbr_PV*nbr_rang):    
                for heure in range (24): 
                        usx=cos(math.radians(gamaS[heure]))*cos(math.radians(thetaS[heure]))
                        usy= sin(math.radians(gamaS[heure]))*cos(math.radians(thetaS[heure]))
                        usz= sin(math.radians(thetaS[heure]))
                        
                        for point in range (4):
                            if gamaS[heure]<0 or thetaS[heure]<0:
                                Ombre[chap][indice][heure][point]= [-2] #il n'y a pas d'ombre car pas de soleil 
                            else: 
                                x= PV[chap][indice][point][0]+ (((H+ PV[chap][indice][point][2])/usz)*usx)
                                y= PV[chap][indice][point][1]- (((H+ PV[chap][indice][point][2])/usz)*usy)
                                z= -H
                                Ombre[chap][indice][heure][point]= [x,y,z] 

    else: 
        Ombre = [[[[] for _ in range(4)] for _ in range (24)] for chap in range (nbr_chap)] 
        for chap in range (nbr_chap):
            for heure in range (24): 
                usx= cos(math.radians(gamaS[heure]))*cos(math.radians(thetaS[heure]))
                usy= sin(math.radians(gamaS[heure]))*cos(math.radians(thetaS[heure]))
                usz= sin(math.radians(thetaS[heure]))
                for point in range (4):
                        if gamaS[heure]<0 or thetaS[heure]<0:
                            Ombre[chap][heure][point]= [-2] #il n'y a pas d'ombre car pas de soleil 
                        else: 
                            x= PV[chap][point][0]+ (((H+ PV[chap][point][2])/usz)*usx)
                            y= PV[chap][point][1]- (((H+ PV[chap][point][2])/usz)*usy)
                            z= -H
                            Ombre[chap][heure][point]= [x,y,z]
                    
         
                  
 
    return Ombre

def position_PV (lon_serre, larg_serre, grand_cote, lon_PV, larg_PV, alphaPV, betaPV, nbr_PV, nbr_rang, nbr_chap, espace, damier, puit_lux):
    '''lon_PV et larg PV= dimension d'un PV. betaPV: inclinaison du toit par rapport à l'horizontale'
alphaPV: angle de la serre par rapport à l'axe Ouest-Est
thetaS: elevation solaire ; gamaS: azimut
renvoie la position des PV'''
    sin= math.sin
    cos=math.cos
    if damier!= False:
        PV = [[[[] for _ in range (4)] for _ in range((nbr_PV*nbr_rang))] for _ in range (int(nbr_chap))] #initialisation de PV
        transverse= grand_cote/ cos(betaPV) #longueur de la pente du toit 
        k1= 0
        k2= 1- larg_PV/transverse #place le panneau au centre 
        indice=0
        for rang in range (nbr_rang):
            if rang%2==0 and damier== 'damier' or damier== 'rayures':
                k1= 0
            elif rang%2!=0 and damier== 'damier': 
                k1= (lon_PV/lon_serre) # le deuxième rang est décalé d'un panneau dans le cas du damier 
        
  
            for panneau in range (nbr_PV): #on commence par placer les panneaux 
 
                    #point A
                    x= k1*lon_serre*sin(alphaPV)+k2*cos(alphaPV)*grand_cote
                    y= k1*lon_serre*cos(alphaPV)-k2*sin(alphaPV)*grand_cote
                    z= -k2*sin(betaPV)*transverse
                    A= [x,y,z]
                    #point B
                    x= (k1*lon_serre+lon_PV)*sin(alphaPV)+k2*cos(alphaPV)*grand_cote
                    y= (k1*lon_serre+lon_PV)*cos(alphaPV)-k2*sin(alphaPV)*grand_cote
                    z= -k2*sin(betaPV)*transverse
                    B= [x,y,z]
            
                    #point C
                    x= (k1*lon_serre+lon_PV)*sin(alphaPV)+(k2+ larg_PV/transverse)*cos(alphaPV)*grand_cote
                    y= (k1*lon_serre+lon_PV)*cos(alphaPV)-(k2+larg_PV/transverse) *sin(alphaPV)* grand_cote
                    z= -(k2*transverse+ larg_PV)*sin(betaPV)
                    C= [x,y,z]
            
                    #point D
                    x= k1 *lon_serre*sin(alphaPV)+(k2+larg_PV/ transverse) *cos(alphaPV)* grand_cote
                    y= k1 *lon_serre*cos(alphaPV)-(k2+larg_PV/transverse) *sin(alphaPV)* grand_cote
                    z= -(k2*transverse+ larg_PV)*sin(betaPV)
                    D= [x,y,z]

                    k1+= (lon_PV+ puit_lux)/lon_serre
                    
                    PV[0][panneau+indice][0] = A
                    PV[0][panneau+indice][1] = B
                    PV[0][panneau+indice][2] = C
                    PV[0][panneau+indice][3] = D
                    
                    #dans le cas d'une multichapelle, on réplique le pattern de PV sur les autres chappelles
                    #pour cela, on décale les PV d'une largueur de chapelle en prenant en compte l'angle 
                    if nbr_chap>1: 
                        for chap in range (1,nbr_chap): # les indices sont décalés de 1 car la chapelle 0 correspond à la monochapelle calculée juste au dessus                 
                            E= [A[0]+(larg_serre+espace)*cos(alphaPV)*chap,A[1]- (larg_serre+ espace)*sin(alphaPV)*chap,A[2]]
                            F= [B[0]+(larg_serre+ espace)*cos(alphaPV)*chap,B[1]- (larg_serre+espace)*sin(alphaPV)*chap,B[2]]
                            G= [C[0]+(larg_serre+ espace)*cos(alphaPV)*chap,C[1]- (larg_serre+espace)*sin(alphaPV)*chap,C[2]]
                            H= [D[0]+(larg_serre+ espace)*cos(alphaPV)*chap,D[1]- (larg_serre+espace)*sin(alphaPV)*chap,D[2]]
                            PV[chap][panneau+indice][0] = E
                            PV[chap][panneau+indice][1] = F
                            PV[chap][panneau+indice][2] = G
                            PV[chap][panneau+indice][3] = H
            
                    
            indice+=nbr_PV
            k2-= larg_PV/(transverse)
 
    else:
        
        PV = [[[] for _ in range (4)] for _ in range (nbr_chap)] #initialisation de PV
        transverse= grand_cote/ cos(betaPV) #longueur de la pente du toit 
        k2= 1- larg_PV/(transverse) #place le panneau en bas  
        k1= 0
        
        #point D 1er PV 1er rang
        x= k1 *lon_serre*sin(alphaPV)+(k2+larg_PV/ transverse) *cos(alphaPV)* grand_cote
        y= k1 *lon_serre*cos(alphaPV)-(k2+larg_PV/transverse) *sin(alphaPV)* grand_cote
        z= -(k2*transverse+ larg_PV)*sin(betaPV)
        D= [x,y,z]
        
        for _ in range (nbr_rang-1): # si on enlève pas 1, on dépasse d'un rang 
            k2-= larg_PV/(transverse)
            
        #point A 1er PV dernier rang 
        x= k1*lon_serre*sin(alphaPV)+k2*cos(alphaPV)*grand_cote
        y= k1*lon_serre*cos(alphaPV)-k2*sin(alphaPV)*grand_cote
        z= -k2*sin(betaPV)*transverse
        A= [x,y,z]
        
        k1= lon_PV/lon_serre*(nbr_PV-1) # si on enlève pas 1, on dépasse d'un PV 
             
        #point B dernier PV dernier rang
        x= (k1*lon_serre+lon_PV)*sin(alphaPV)+k2*cos(alphaPV)*grand_cote
        y= (k1*lon_serre+lon_PV)*cos(alphaPV)-k2*sin(alphaPV)*grand_cote
        z= -k2*sin(betaPV)*transverse
        B= [x,y,z]
        
        k2=1-larg_PV/ transverse
        
        #point C dernier PV 1er rang
        x= (k1*lon_serre+lon_PV)*sin(alphaPV)+(k2+ larg_PV/transverse)*cos(alphaPV)* grand_cote
        y= (k1*lon_serre+lon_PV)*cos(alphaPV)-(k2+larg_PV/transverse) *sin(alphaPV)* grand_cote
        z= -(k2*transverse+ larg_PV)*sin(betaPV)
        C= [x,y,z]
    
        
        PV[0][0] = A
        PV[0][1] = B
        PV[0][2] = C
        PV[0][3] = D
        #dans le cas d'une multichapelle, on réplique le pattern de PV sur les autres chappelles
        #pour cela, on décale les PV d'une largueur de chapelle en prenant en compte l'angle 
        if nbr_chap>1: 
            
            for chap in range (1,nbr_chap): # les indices sont décalés de 1 car la chapelle 0 correspond à la monochapelle calculée juste au dessus                 
                E= [A[0]+(larg_serre+espace)*cos(alphaPV)*chap,A[1]- (larg_serre+ espace)*sin(alphaPV)*chap,A[2]]
                F= [B[0]+(larg_serre+ espace)*cos(alphaPV)*chap,B[1]- (larg_serre+espace)*sin(alphaPV)*chap,B[2]]
                G= [C[0]+(larg_serre+ espace)*cos(alphaPV)*chap,C[1]- (larg_serre+espace)*sin(alphaPV)*chap,C[2]]
                H= [D[0]+(larg_serre+ espace)*cos(alphaPV)*chap,D[1]- (larg_serre+espace)*sin(alphaPV)*chap,D[2]]
                PV[chap][0] = E
                PV[chap][1] = F
                PV[chap][2] = G
                PV[chap][3] = H

    return PV

############ calcul rayonnement #############

def rayonnement(LAT, LON, date_debut, date_fin):
    ''' récupération des valeurs de radiation totale et diffuse en fonction de la localisation'''
    # La librairie PVLib possède une fonction qui pemet de récupérer les données PVGIS via son API
    rayon_df = pvlib.iotools.get_pvgis_tmy(LAT, LON, outputformat='csv', usehorizon=True,
                      userhorizon=None, startyear=2005, endyear=2020, url='https://re.jrc.ec.europa.eu/api/v5_2/',
                      map_variables=False, timeout=30)
    rayon_df = rayon_df[0] 
    rayon_df= rayon_df.loc[:, ['G(h)', 'Gd(h)']] #récupère seulement les colonnes d'interêt
    rayon_df.index = rayon_df.index.tz_convert('+01:00') #converti le décalage temporaire 

    
    # Convertir la date spécifiée en objet Timestamp
    deb_date = pd.Timestamp(date_debut)
    fin_date = pd.Timestamp(date_fin)
    # Filtrer les données pour la journée spécifique (jour et mois) en ignorant l'année
    rayon_date = rayon_df[
        (rayon_df.index.day >= deb_date.day) & (rayon_df.index.month >= deb_date.month)
        & (rayon_df.index.day <= fin_date.day)  & (rayon_df.index.month <= fin_date.month)
    ]
    
    Itot = rayon_date['G(h)'] #radiation globale
    Ir = rayon_date['Gd(h)'] #radiaiton diffuse 

    return Itot, Ir

def calcul_carré (long, larg, larg_serre, precision, lon_serre, alphaPV):
    ''' calcule un carré du quadrillage de la serre (donc qui dépend de la rotation)'''
    cos= math.cos 
    sin= math.sin
    return [(-larg_serre/2+larg*precision)*cos(alphaPV)+long*precision*sin(alphaPV), sin(alphaPV)*(larg_serre/2-larg*precision)+cos(alphaPV)*(long*precision)] 
 
def carte_lux (LAT, LON, lon_serre, larg_serre, lon_PV, larg_PV, precision, alphaPV, nbr_PV, date_debut, date_fin, betaPV, PV, h_serre, nbr_rang, nbr_chap, h_toit, espace, damier, angles_df, couverture):
    ''' Calcule les différentes cartes: 
        - cubes représente la radiation reçue selon le quadrillage choisi sur l'année. Cubes_pourcent est la même carte en pourcentage
        - les cartes de saisons (ete, automone, hiver et printemps) sont pareilles mais sur des jours différents. '''
   
    taux_couv= couverture/100
    Itot, Ir= rayonnement (LAT, LON, date_debut, date_fin) #récupère les données
    cubes=np.zeros((int(lon_serre/precision), int((larg_serre+espace)*nbr_chap/precision )))  #initialise la grille 
    ete= np.zeros((int(lon_serre/precision), int((larg_serre+espace)*nbr_chap/precision )))
    printemps= np.zeros((int(lon_serre/precision), int((larg_serre+espace)*nbr_chap/precision )))
    hiver= np.zeros((int(lon_serre/precision), int((larg_serre+espace)*nbr_chap/precision )))
    automne= np.zeros((int(lon_serre/precision), int((larg_serre+espace)*nbr_chap/precision )))
   #récupère le nombre de jour sur lequel on opère 
   # Convertir la date spécifiée en objet Timestamp
    deb_date = pd.Timestamp(date_debut)
    fin_date = pd.Timestamp(date_fin)
    delta_temps = fin_date - deb_date
    # Extrait le nombre de jours et le convertit en entier
    nombre_de_jours = delta_temps.days
    
    #création de la barre de progression
    progress_bar = tqdm(total=nombre_de_jours, desc=" Progression ")
    
    for jour in range (nombre_de_jours):
        date= deb_date+ pd.Timedelta(days=jour)
        ombre= calcul_ombre(lon_serre, larg_serre, lon_PV, larg_PV, nbr_PV, alphaPV, betaPV, angles_df, h_serre, date, PV, nbr_rang, nbr_chap, h_toit, damier)
        for long in range (len(cubes)):
            for larg in range(len(cubes[0])):
                        #coordonnée du petit cube
                i= calcul_carré(long, larg, larg_serre, precision, lon_serre, alphaPV)
                j= calcul_carré(long+1, larg, larg_serre, precision, lon_serre, alphaPV)
                k= calcul_carré(long, larg+1, larg_serre, precision, lon_serre, alphaPV)
                l= calcul_carré(long+1, larg+1, larg_serre, precision, lon_serre, alphaPV)
                carre= [i,j,k,l] #élement étudié
                
                for heure in range (24):
                    presence_ombre= test (nbr_rang, nbr_PV, ombre, heure, carre, nbr_chap, damier)            
                    if presence_ombre:
                        cubes[long][larg]+=  taux_couv * Ir[heure+24*jour] 
                    else: 
                        cubes[long][larg]+= 0.9* Itot [heure+24*jour]                       
                        
                    if jour<80 or jour >=356:
                        if presence_ombre:
                            hiver[long][larg]+=  taux_couv*Ir[heure+24*jour]
                            
                        else: 
                            hiver[long][larg]+= 0.9* Itot[heure+24*jour]
                            
                    if 172<=jour<267:
                        if presence_ombre: 
                            ete [long][larg]+=  taux_couv*Ir[heure+24*jour] 
                        else: 
                            ete [long][larg]+= 0.9*Itot [heure+ 24*jour]
                        
                    if 267<=jour<356:
                        if presence_ombre:
                            automne [long][larg]+= taux_couv* Ir[heure+24*jour] 
                           
                        else: 
                            automne [long][larg]+= 0.9* Itot[heure+24*jour] 
                        
                    if 80<=jour<172:
                        if presence_ombre:
                            printemps [long][larg]+=  taux_couv*Ir[heure+24*jour]
                        else:
                            printemps [long][larg]+= 0.9* Itot[heure+24*jour] 
                        
        progress_bar.update(1)                            
                    
    maximum=0    
    I_max= Itot[(Itot.index.day>=deb_date.day) & (Itot.index.month>=deb_date.month) & 
               (Itot.index.day<=fin_date.day) & (Itot.index.month<=fin_date.month)]
    maximum= I_max. sum()  # maximum de radiation entre les deux dates étudiées
   
    cubes= cubes
    # Calcul du pourcentage de radiation
    cubes_pourcent = (cubes / maximum) * 100
    max_ete= np. max (ete)
    ete_pourcent= (ete/ max_ete)*100
    hiver_pourcent= (hiver/ np. max(hiver))*100
    auto_pourcent= (automne/ np. max(automne))*100
    print_pourcent= (printemps/ np. max(printemps))*100
    ete= ete* 3600/10000/48.6 /94
    automne= automne* 3600/10000/48.6 /89
    printemps= printemps* 3600/10000/48.6 /92
    hiver= hiver* 3600/10000/48.6/90
    cubes= cubes/1000 #resultat en kWh


    #fermer la barre de progression 
    progress_bar.close()
    return cubes, cubes_pourcent, ete, ete_pourcent, hiver, hiver_pourcent, printemps, print_pourcent, automne, auto_pourcent 

########intersection #################   
                
def dot_product(v1, v2):
    return v1[0] * v2[0] + v1[1] * v2[1]

def project_polygon(polygon, axis):
    min_proj = max_proj = dot_product(polygon[0], axis)
    for point in polygon[1:]:
        projection = dot_product(point, axis)
        min_proj = min(min_proj, projection)
        max_proj = max(max_proj, projection)
    return (min_proj, max_proj)

def intersect(rectangle, carre): #est ce que le rectangle et le carré s'intersectent 
    axes = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    for i in range(4):
        axis = (axes[i][0], axes[i][1])
        min_r, max_r = project_polygon(rectangle, axis)
        min_c, max_c = project_polygon(carre, axis)
        if max_r < min_c or max_c < min_r:
            return False

    return True

def test (nbr_rang, nbr_PV, ombre, heure, carre, nbr_chap, damier) :
    if damier!= False : 
        for chap in range (int(nbr_chap)):
            for rang in range (nbr_rang):
                for panneau in range (nbr_PV):
                    indice = rang * nbr_PV + panneau
                    if ombre [chap][indice][heure][0][0]!=-2:#si =-2--> ombre --> on ajoute rien 
                        A = [ombre[chap][indice][heure][0][0], ombre[chap][indice][heure][0][1]]
                        B = [ombre[chap][indice][heure][1][0], ombre[chap][indice][heure][1][1]]
                        C = [ombre[chap][indice][heure][2][0], ombre[chap][indice][heure][2][1]]
                        D=  [ombre[chap][indice][heure][3][0], ombre[chap][indice][heure][3][1]]
                        rectangle = [A,B,C,D] #ombre 
                
                        if intersect(rectangle, carre): # surface en commun --> ombre
                            return True  
    else:
        presence_ombre= False #fausse sauf si on detecte une ombre à cette heure là
        for chap in range (nbr_chap):
            if ombre [chap][heure][0][0]!=-2:#si =-2--> ombre --> on ajoute rien 
                A = [ombre[chap][heure][0][0], ombre[chap][heure][0][1]]
                B = [ombre[chap][heure][1][0], ombre[chap][heure][1][1]]
                C = [ombre[chap][heure][2][0], ombre[chap][heure][2][1]]
                D=  [ombre[chap][heure][3][0], ombre[chap][heure][3][1]]
                rectangle = [A,B,C,D] #ombre 
            
                if intersect(rectangle, carre): # surface en commun --> ombre
                    return True   
     
    return False
            
        ### Affichage graphique ###   
        
def donnees_utilisateur ():
    # Demander à l'utilisateur de saisir le type d'information
    type_info = input("Entrez le type d'information (monochapelle asymétrique ou symétrique, multichapelle asymétrique ou symétrique, ombrière) : ")
    damier= input ("Voulez-vous une couverture avec un motif de damier ou rayures (damier ou rayures ou non) ? ")
    if damier!='non':
        puit_lux= float(input("Entrez la largueur des puits de lumières: "))
    else: 
        puit_lux= None
        damier= False
    # Initialiser des variables pour stocker les informations
    lon_serre  = None
    larg_serre = None
    nbr_chap= None
    petit_angle= None
    grand_angle= None 
    grand_cote= None
    petit_cote= None
    espace= None
    cos= math.cos 
    sin=math.sin 
    rad= math.radians 
    # Utiliser une structure conditionnelle pour demander des informations différentes en fonction du type
    if type_info == "monochapelle symétrique":
        lon_serre = float(input("Entrez longueur de la chapelle : "))
        larg_serre= float(input ("Entrez la largueur de la chapelle: "))
    elif type_info == "multichapelle symétrique":
        lon_serre = float(input("Entrez longueur d'une chapelle : "))
        larg_serre= float(input ("Entrez la largueur d'une chapelle: "))
        nbr_chap= int(input("Entrez le nombre de chapelles: "))
    elif type_info == "monochapelle asymétrique":
        petit_angle = float(input("Entrez le petit angle de la chapelle : "))
        grand_angle= float(input ("Entrez le grand angle de la chapelle: "))
        larg_serre= float(input ("Entrez la largueur de la chapelle: "))
        lon_serre= float(input("Entrez longueur de la chapelle : "))
        #on calcule les longueurs avec la loi des sinus 
        grand_cote= larg_serre*sin(rad(grand_angle))/sin(rad(180-grand_angle-petit_angle))*cos(rad(petit_angle))
        petit_cote= larg_serre-grand_cote
    elif type_info == "multichapelle asymétrique":
        petit_angle = float(input("Entrez le petit angle d'une chapelle : "))
        grand_angle= float(input ("Entrez le grand angle d'une chapelle: "))
        larg_serre= float(input ("Entrez la largueur d'une chapelle: "))
        lon_serre= float(input("Entrez longueur d'une chapelle : "))
        nbr_chap= int(input("Entrez le nombre de chapelles: "))
        #on calcule les longueurs avec la loi des sinus+ trigonométrie (on cherche la largueur entre le projeté du sommet j/i et les bords e/d/f ou c) 
        grand_cote= larg_serre*sin(rad(grand_angle))/sin(rad(180-grand_angle-petit_angle))*cos(rad(petit_angle))
        petit_cote= larg_serre-grand_cote
    elif type_info == "ombrière":
        # attention, pour que cela fonctionne, il faut que largeur soit dans le sens des PV et longueur  perpendiculaire aux rangées 
        lon_serre = float(input("Entrez la longueur d'une rangée d'ombrières : "))
        larg_serre= float(input ("Entrez la longueur occupée par les rangées d'ombrières: "))
        espace= float (input("Entrez l'inter rang en mètre: "))
    
    else:
        print("Type d'information invalide")
    
    return (type_info, lon_serre, larg_serre, nbr_chap, petit_angle, grand_angle, grand_cote, petit_cote, espace, damier, puit_lux)


def cartes_assolement(printemps, ete, hiver, automne):

    seuil_min = 15
    seuil_max = 25
    print_zone = segmentation_zones(printemps, seuil_min, seuil_max)
    ete_zone = segmentation_zones(ete, seuil_min, seuil_max)
    seuil_min = 15
    seuil_max = 20
    hiver_zone = segmentation_zones(hiver, seuil_min, seuil_max)
    automne_zone = segmentation_zones(automne, seuil_min, seuil_max)

    plt.figure(figsize=(12, 10))

    plt.subplot(2, 2, 1)
    im = plt.imshow(print_zone, cmap='viridis', interpolation='none', vmin=1, vmax=3)
    cbar = plt.colorbar(im, ticks=[1, 2, 3])
    cbar.ax.set_yticklabels(['Zone 1', 'Zone 2', 'Zone 3'])
    plt.title('''Carte d'assollement conseillée pour le Printemps''')

    plt.subplot(2, 2, 2)
    im = plt.imshow(ete_zone, cmap='viridis', interpolation='none', vmin=1, vmax=3)
    cbar = plt.colorbar(im, ticks=[1, 2, 3])
    cbar.ax.set_yticklabels(['Zone 1', 'Zone 2', 'Zone 3'])
    plt.title('''Carte d'assollement conseillée pour l'été''')

    plt.subplot(2, 2, 3)
    im = plt.imshow(hiver_zone, cmap='viridis', interpolation='none', vmin=1, vmax=3)
    cbar = plt.colorbar(im, ticks=[1, 2, 3])
    cbar.ax.set_yticklabels(['Zone 1', 'Zone 2', 'Zone 3'])
    plt.title('''Carte d'assollement conseillée pour l'hiver''')

    plt.subplot(2, 2, 4)
    im = plt.imshow(automne_zone, cmap='viridis', interpolation='none', vmin=1, vmax=3)
    cbar = plt.colorbar(im, ticks=[1, 2, 3])
    cbar.ax.set_yticklabels(['Zone 1', 'Zone 2', 'Zone 3'])
    plt.title('''Carte d'assollement conseillée pour l'automne''')

    # Affichage des cartes
    plt.show()



def afficher_carte(matrice, titre):
    plt.figure(figsize=(8, 6))
    plt.subplot(1, 2, 1) 
    im = plt.imshow(matrice, cmap='viridis', interpolation='none', vmin=1, vmax=3)
    plt.colorbar(im, ticks=[1, 2, 3], ticklabels=['Zone 1', 'Zone2', 'Zone 3'])
    plt.title(titre)



def ajouter_texte():
    # Ajustez la taille de la figure selon vos besoins
    fig, axs = plt.subplots(2, 1, figsize=(10, 6))

    # Texte pour le premier paragraphe
    texte_automne_hiver = '''
        Automne, Hiver:
        Zonage conseillé des principales espèces en maraîchage. Ne sont pas pris en compte les facteurs autres que la lumière: durée d'ensolleillement, température, humidité...

        Zone 1: DLI<10
        Zone trop sombre pour la plupart des cultures, plantules compris

        Zone 2: 10<DLI<15
        Zone plus ombragée: légumes à feuilles (épinard, chou, laitue), Herbes aromatiques (basilique, persil, coriandre), Racines et tubercules (Carottes, pomme de terre, oignons)

        Zone 3: DLI>15
        Zone à bonne luminosité
    '''

    # Texte pour le deuxième paragraphe
    texte_ete_printemps = '''
        Été, Printemps:
        Zonage conseillé des principales espèces en maraîchage. Ne sont pas pris en compte les facteurs autres que la lumière: durée d'ensolleillement, température, humidité...

        Zone 1: DLI<15
        Zone plus ombragée: légumes à feuilles (épinard, chou, laitue), Herbes aromatiques (basilique, persil, coriandre), Racines et tubercules (Carottes, pomme de terre, oignons)

        ZOne 2: 15<DLI<25
        Zone intermédiaire à ensolleillée: Légumes fruits (Tomates, poivrons, concombres), fruits à baie (fraise, framboise, mûres)

        Zone 3: DLI>30
        Zone à même luminosité que l'extérieur: risque plus important de brûlure ou de dessèchement
    '''

    # Affichage du texte dans les sous-plots
    axs[0].text(0.05, 0.95, texte_automne_hiver, color='black', fontsize=10, transform=axs[0].transAxes, verticalalignment='top', bbox=dict(facecolor='white', edgecolor='none', boxstyle='round,pad=0.5'), wrap=True)
    axs[1].text(0.05, 0.95, texte_ete_printemps, color='black', fontsize=10, transform=axs[1].transAxes, verticalalignment='top', bbox=dict(facecolor='white', edgecolor='none', boxstyle='round,pad=0.5'), wrap=True)

    # Désactiver les axes
    axs[0].axis('off')
    axs[1].axis('off')

    plt.tight_layout()
    plt.show()

# Appeler la fonction pour afficher le texte
ajouter_texte()

    
def segmentation_zones(matrice, seuil_min, seuil_max):
    ''' Reçoit une matrice et renvoie les zones qui correspondent aux seuils donnés '''
    # Créer une matrice de masque pour les valeurs comprises entre les seuils
    masque_entre = np.logical_and(matrice >= seuil_min, matrice <= seuil_max)

    # Créer une matrice de masque pour les valeurs inférieures à seuil_min
    masque_inf = matrice < seuil_min

    # Créer une matrice de masque pour les valeurs supérieures à seuil_max
    masque_sup = matrice > seuil_max

    # Initialiser une matrice pour le zonage
    zonage = np.zeros_like(matrice)

    # Remplir les zones délimitées par les masques
    zonage[masque_entre]= 2  # Zone "Entre"
    zonage[masque_inf] = 1   # Zone "Inférieur à"
    zonage[masque_sup] = 3   # Zone "Supérieur à"

    return zonage


#nbr_PV= recherche_nbr_PV(30, 2, 'damier', 3)

#4.41 105.67  3.346  12 
#PV= position_PV (10, 2.5, 5, 1, 0.5, 0, 20, nbr_PV, 2, 1, 0, True)  
#calcul_ombre (10, 5, 1, 0.5, nbr_PV, 0, 20, 40.121310, 9.010441, 2.5, '2023/08/08', PV, 2, 1) 

#carte_lux (40.121310, 9.010441, 50, 19.2, 1.665, 0.991, 1, 0, nbr_PV, '2023/08/08', '2023/08/09', 20, PV, 2.5, 5 )    