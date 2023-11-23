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

from Assolement import recherche_nbr_PV, recherche_rang, position_PV, angles, carte_lux
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
    type_info : str = Field(default=None)
    damier : bool = Field(default=False)
    puit_lux : str = Field(default=None)
    lon_serre : float = Field(default=None)
    larg_serre : float = Field(default=None)
    nbr_chap : float = Field(default=None)
    petit_angle : float = Field(default=None)
    grand_angle : float = Field(default=None)
    grand_cote : float = Field(default=None)
    petit_cote : float = Field(default=None)
    espace : float = Field(default=None)
    LAT : float = Field(default=None)
    LON : float = Field(default=None)
    lon_PV : float = Field(default=1.722)
    larg_PV : float = Field(default=1)
    precision : float = Field(default=1)
    alpha_PV : str = Field(default=None)
    date_debut : str = Field(default="2023/01/01")
    date_fin : str = Field(default="2023/12/31")
    beta_PV : float = Field(default=22)
    h_serre : float = Field(default=None)
    couverture : int = Field(default=None)
    
    

@app.route('/assolement', methods=['POST'])
def calculte_assolement():

    configuration_data = request.get_json()
    configuration = Configuration(**configuration_data)

    cos = math.cos
    sin = math.sin
    tan = math.tan
    
    if configuration.alpha_PV == 'Sud':
        alpha_PV= 0
    if configuration.alpha_PV =='Nord':
        alpha_PV= 180
    if configuration.alpha_PV =='Est':
        alpha_PV=90
    if configuration.alpha_PV=='Ouest':
        alpha_PV=270
    if configuration.alpha_PV=='Sud-Est':
        alpha_PV=45
    if configuration.alpha_PV=='Sud-Ouest':
        alpha_PV=315
    if configuration.alpha_PV=='Nord-Est':
        alpha_PV=   135 
    if configuration.alpha_PV=='Nord-Ouest':
        alpha_PV=225

    alphaPV=math.radians(alphaPV) 
    betaPV= math.radians(betaPV)

    if nbr_chap==None: #pour que le reste fonctionne, si on a une monochapelle on prend la valeur 1 
        nbr_chap=1 
    if espace != None: #on a affaire avec une ombrière 
        larg_ombriere = configuration.larg_PV*cos(betaPV)
        nbr_chap = int(larg_serre/(larg_ombriere+espace)) #nombre de rangées qu'on peut mettre 
        nbr_rang= 1
    else:
        espace= 0 

    if configuration.type_info == 'monochapelle symétrique' or configuration.type_info== 'multichapelle symétrique':
        nbr_PV= recherche_nbr_PV(configuration.lon_serre,
                                 configuration.lon_PV,
                                 configuration.damier,
                                 configuration.puit_lux)
        (nbr_rang, couv_real)= recherche_rang(configuration.larg_PV,
                                              configuration.couverture,
                                              larg_serre, betaPV)
        #print("Couverture effectivement réalisée: ", couv_real)
        h_toit= larg_serre/2*tan(betaPV) 
        grand_cote= larg_serre/2
        PV= position_PV (configuration.lon_serre,
                         larg_serre, grand_cote,
                         configuration.lon_PV,
                         configuration.larg_PV,
                         alphaPV, betaPV, nbr_PV,
                         nbr_rang, nbr_chap, espace,
                         configuration.damier,
                         configuration.puit_lux)

    elif configuration.type_info == 'monochapelle asymétrique' or configuration.type_info=='multichapelle asymétrique' :

        betaPV= math.radians(configuration.petit_angle)
        h_toit= grand_cote *tan(betaPV)
        nbr_PV= recherche_nbr_PV(configuration.lon_serre,
                                 configuration.lon_PV,
                                 configuration.damier,
                                 configuration.puit_lux)
        (nbr_rang, couv_real)= recherche_rang(configuration.larg_PV,
                                              configuration.couverture,
                                              larg_serre, betaPV)
        print("Couverture effectivement réalisée: ", couv_real)
        PV= position_PV (configuration.lon_serre,
                         larg_serre, grand_cote,
                         configuration.lon_PV,
                         configuration.larg_PV,
                         alphaPV, betaPV, nbr_PV,
                         nbr_rang, nbr_chap, espace,
                         configuration.damier,
                         configuration.puit_lux)

    elif configuration.type_info == 'ombrière':
        #NB dans le cas de l'ombrière, lon_serre correspond à celle du projet
        #(l'ombrière faisant par defaut les dimensions d'un PV)
        nbr_PV= recherche_nbr_PV(configuration.lon_serre,
                                 configuration.lon_PV,
                                 configuration.damier,
                                 configuration.puit_lux)
        h_toit= larg_ombriere*tan(betaPV)
        PV= position_PV (configuration.lon_serre,
                         larg_ombriere, larg_ombriere,
                         configuration.lon_PV,
                         configuration.larg_PV,
                         alphaPV, betaPV, nbr_PV,
                         nbr_rang, nbr_chap, espace,
                         configuration.damier,
                         configuration.puit_lux)
        larg_serre= larg_ombriere


    nbr_PV = recherche_nbr_PV(configuration.lon_serre,
                              configuration.lon_PV,
                              configuration.damier,
                              configuration.puit_lux)

    angles_df= angles (configuration.LAT, configuration.LON)
    (cubes, cubes_pourcent, ete,
     ete_pourcent, hiver, hiver_pourcent,
     printemps, print_pourcent, automne,
     auto_pourcent ) = carte_lux(configuration.LAT, configuration.LON,
                                configuration.lon_serre, larg_serre,
                                configuration.lon_PV, configuration.larg_PV,
                                configuration.precision, alphaPV,
                                nbr_PV, configuration.date_debut,
                                configuration.date_fin, betaPV, PV,
                                configuration.h_serre, nbr_rang,
                                nbr_chap, h_toit,
                                espace, configuration.damier,
                                angles_df)

    data = {"cubes": cubes, "cubes_pourcent": cubes_pourcent, "hiver_pourcent": hiver_pourcent,
            "hiver": hiver, "ete_pourcent": ete_pourcent, "ete": ete, "printemps": printemps,
            "print_pourcent": print_pourcent, "automne": automne, "auto_pourcent": auto_pourcent}
    
    return jsonify(data)
    
if __name__ == "__main__":
    app.run(debug=True)