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
                        cubes[long][larg]+= 0.8* Itot [heure+24*jour]                       
                        
                    if jour<80 or jour >=356:
                        if presence_ombre:
                            hiver[long][larg]+=  taux_couv*Ir[heure+24*jour]
                            
                        else: 
                            hiver[long][larg]+= 0.8* Itot[heure+24*jour]
                            
                    if 172<=jour<267:
                        if presence_ombre: 
                            ete [long][larg]+=  taux_couv*Ir[heure+24*jour] 
                        else: 
                            ete [long][larg]+= 0.8*Itot [heure+ 24*jour]
                        
                    if 267<=jour<356:
                        if presence_ombre:
                            automne [long][larg]+= taux_couv* Ir[heure+24*jour] 
                           
                        else: 
                            automne [long][larg]+= 0.8* Itot[heure+24*jour] 
                        
                    if 80<=jour<172:
                        if presence_ombre:
                            printemps [long][larg]+=  taux_couv*Ir[heure+24*jour]
                        else:
                            printemps [long][larg]+= 0.8* Itot[heure+24*jour] 
                        
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
