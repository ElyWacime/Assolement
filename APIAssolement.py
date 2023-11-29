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
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from pydantic import BaseModel, Field
from logging.handlers import RotatingFileHandler
import json

from Assolement import recherche_nbr_PV, recherche_rang, position_PV, angles, carte_lux, recherche_rang_asymetrique
#from affichage import *

app = Flask(__name__)
CORS(app)

if not app.debug:
    file_handler = RotatingFileHandler(
        'flask.log', maxBytes=1024 * 1024 * 100, backupCount=20)
    file_handler.setLevel(logging.ERROR)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)

class Configuration(BaseModel):
    type_info : str = Field(default="monochapelle symétrique")
    damier : str = Field(default="non")
    puit_lux : float = Field(default=0)
    lon_serre : float = Field(default=20)
    larg_serre : float = Field(default=10)
    nbr_chap : float = Field(default=1)
    petit_angle : float = Field(default=22)
    grand_angle : float = Field(default=45)
    grand_cote : float = Field(default=0)
    petit_cote : float = Field(default=0)
    espace : float = Field(default=0)
    LAT : float = Field(default=44.68)
    LON : float = Field(default=0.55)
    alphaPV : str = Field(default="Sud")
    '''precision : float = Field(default=1)
    date_debut : str = Field(default="2023/01/01")
    date_fin : str = Field(default="2023/12/31")'''
    #betaPV : float = Field(default=22)
    h_serre : float = Field(default=5)
    couverture : int = Field(default=50)
    
    

@app.route('/assolement', methods=['POST'])
def calculte_assolement():

    configuration_data = request.get_json()
    configuration = Configuration(**configuration_data)
    
    betaPV = 22
    precision = 1
    date_debut = "2023/01/01"
    date_fin = "2023/12/31"
    lon_PV = 1.772
    larg_PV = 1.134
    
    cos = math.cos
    sin = math.sin
    tan = math.tan
    rad = math.radians
    
    if configuration.alphaPV == 'Sud':
        alphaPV= 0
    if configuration.alphaPV =='Nord':
        alphaPV= 180
    if configuration.alphaPV =='Est':
        alphaPV=90
    if configuration.alphaPV=='Ouest':
        alphaPV=270
    if configuration.alphaPV=='Sud-Est':
        alphaPV=45
    if configuration.alphaPV=='Sud-Ouest':
        alphaPV=315
    if configuration.alphaPV=='Nord-Est':
        alphaPV=135 
    if configuration.alphaPV=='Nord-Ouest':
        alphaPV=225

    alphaPV=math.radians(alphaPV)
    betaPV= math.radians(betaPV)

    '''if configuration.nbr_chap==None: #pour que le reste fonctionne, si on a une monochapelle on prend la valeur 1 
        configuration.nbr_chap=1 '''
    if configuration.espace != 0: # original if statement: configuration.espace != None: #on a affaire avec une ombrière 
        larg_ombriere = larg_PV*cos(betaPV)
        nbr_chap = int(configuration.larg_serre/(larg_ombriere+configuration.espace)) #nombre de rangées qu'on peut mettre 
        nbr_rang= 1
    '''else:
        configuration.espace= 0''' 

    if configuration.type_info == 'monochapelle symétrique' or configuration.type_info== 'multichapelle symétrique':
        nbr_PV= recherche_nbr_PV(configuration.lon_serre,
                                 lon_PV,
                                 configuration.damier,
                                 configuration.puit_lux)
        (nbr_rang, couv_real)= recherche_rang(larg_PV,
                                              configuration.couverture,
                                              configuration.larg_serre, betaPV)
        #print("Couverture effectivement réalisée: ", couv_real)
        h_toit= configuration.larg_serre/2*tan(betaPV) 
        grand_cote= configuration.larg_serre/2
        PV= position_PV (configuration.lon_serre,
                         configuration.larg_serre, grand_cote,
                         lon_PV,
                         larg_PV,
                         alphaPV, betaPV, nbr_PV,
                         nbr_rang, configuration.nbr_chap, configuration.espace,
                         configuration.damier,
                         configuration.puit_lux)

    elif configuration.type_info == 'monochapelle asymétrique' or configuration.type_info=='multichapelle asymétrique' :

        betaPV= math.radians(configuration.petit_angle)
        h_toit= grand_cote *tan(betaPV)
        nbr_PV= recherche_nbr_PV(configuration.lon_serre,
                                 lon_PV,
                                 configuration.damier,
                                 configuration.puit_lux)
        (nbr_rang, couv_real)= recherche_rang_asymetrique(larg_PV=larg_PV, couverture=configuration.couverture,
                                                          petit_cote=configuration.petit_cote,
                                                          grand_cote=configuration.grand_cote,
                                                          petit_angle=configuration.petit_angle,
                                                          grand_angle=configuration.grand_angle)
        print("Couverture effectivement réalisée: ", couv_real)
        PV= position_PV (configuration.lon_serre,
                         configuration.larg_serre, grand_cote,
                         lon_PV,
                         larg_PV,
                         alphaPV, betaPV, nbr_PV,
                         nbr_rang, nbr_chap, configuration.espace,
                         configuration.damier,
                         configuration.puit_lux)
        configuration.grand_cote = configuration.larg_serre*sin(rad(configuration.grand_angle))/sin(rad(180-configuration.grand_angle-configuration.petit_angle))*cos(rad(configuration.petit_angle))
        configuration.petit_angle = configuration.larg_serre-configuration.grand_cote
    elif configuration.type_info == 'ombrière':
        #NB dans le cas de l'ombrière, lon_serre correspond à celle du projet
        #(l'ombrière faisant par defaut les dimensions d'un PV)
        nbr_PV= recherche_nbr_PV(configuration.lon_serre,
                                 lon_PV,
                                 configuration.damier,
                                 configuration.puit_lux)
        h_toit= larg_ombriere*tan(betaPV)
        PV= position_PV (configuration.lon_serre,
                         larg_ombriere, larg_ombriere,
                         lon_PV,
                         larg_PV,
                         alphaPV, betaPV, nbr_PV,
                         nbr_rang, nbr_chap, configuration.espace,
                         configuration.damier,
                         configuration.puit_lux)
        configuration.larg_serre= larg_ombriere


    nbr_PV = recherche_nbr_PV(configuration.lon_serre,
                              lon_PV,
                              configuration.damier,
                              configuration.puit_lux)

    angles_df= angles (configuration.LAT, configuration.LON)
    (cubes, cubes_pourcent, ete,
     ete_pourcent, hiver, hiver_pourcent,
     printemps, print_pourcent, automne,
     auto_pourcent ) = carte_lux(LAT=configuration.LAT,
                                LON=configuration.LON,
                                lon_serre=configuration.lon_serre,
                                larg_serre=configuration.larg_serre,
                                lon_PV=lon_PV,
                                larg_PV=larg_PV,
                                precision=precision,
                                alphaPV=alphaPV,
                                nbr_PV=nbr_PV,
                                date_debut=date_debut,
                                date_fin=date_fin,
                                betaPV=betaPV,
                                PV=PV,
                                h_serre=configuration.h_serre,
                                nbr_rang=nbr_rang,
                                nbr_chap=configuration.nbr_chap,
                                h_toit=h_toit,
                                espace=configuration.espace,
                                damier=configuration.damier,
                                angles_df=angles_df,
                                couverture=configuration.couverture)

    '''data = {"cubes": cubes, "cubes_pourcent": cubes_pourcent, "hiver_pourcent": hiver_pourcent,
            "hiver": hiver, "ete_pourcent": ete_pourcent, "ete": ete, "printemps": printemps,
            "print_pourcent": print_pourcent, "automne": automne, "auto_pourcent": auto_pourcent}
    for key in data:
        key = key.tolist()

    return jsonify(data)'''
    data = {
        "cubes": cubes,
        "cubes_pourcent": cubes_pourcent,
        "hiver_pourcent": hiver_pourcent,
        "hiver": hiver,
        "ete_pourcent": ete_pourcent,
        "ete": ete,
        "printemps": printemps,
        "print_pourcent": print_pourcent,
        "automne": automne,
        "auto_pourcent": auto_pourcent
    }
    
    for key, value in data.items():
        if isinstance(value, np.ndarray):
            data[key] = value.tolist()
    
    return jsonify(data)
    
if __name__ == "__main__":
    app.run(threaded=True, debug=True)