#!/usr/bin/env python3
# -*- coding:utf-8 -*-

# -------------------------------- Importation ------------------------------- #

import os
import subprocess
import json
import sys
from PIL import ImageTk, Image
import ctypes

import tkinter as tk
from tkinter import messagebox

import pygame

# ------------------- Amélioration de la qualité graphique ------------------- #

if 'win' in sys.platform:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)

# --------------------------------- Dossiers --------------------------------- #
# permet de se réferrer au bon dossier dans lequel est compris l'application ou le 
# script en fonction de ce qui lance l'application --> utile pour cx_freeze
if getattr(sys, 'frozen', False):
    # frozen
    script_dir = os.path.dirname(sys.executable)
else:
    # unfrozen
    script_dir = os.path.dirname(os.path.realpath(__file__))

# --------------------------------- Curseurs --------------------------------- #
# on nomme les curseurs pour plus de facilité
glassnormal = "@cursors/glassnormal.cur"
cursor_plus = "@cursors/7p.cur"
cursor_black = "@cursors/7n.cur"
cursor_vertical = "@cursors/7vs.cur"
cursor_horizontal = "@cursors/7hs.cur"
cursor_end = "@cursors/7u.cur"
cursor_wait = "@cursors/7w.ani"

# ------------------------------ Initialisation ------------------------------ #
# ouverture du fichier path.json pour lire le chemin d'accès à Focusrite Control
with open('path.json', encoding="utf-8") as json_file: # path to Focusrite Control.exe
    path = json.load(json_file)

# lancement d'une grande page Tkinter, avec titre et logo, configuration du curseur
root = tk.Tk() #initialise l'application
root.title("Merspeakers")
root.iconbitmap(default=os.path.join(script_dir, "logo","icon.ico"))
root.config(cursor=glassnormal) #curseur souris de l'appli
root.state('zoomed')

width_screen  = root.winfo_screenwidth() # récupère les information de l'écran
height_screen = root.winfo_screenheight()

active_buttons = [] # liste des boutons actifs
paused_buttons = [] # liste des boutons en pause
name_sounds = [] # liste des noms sans .wav des sons 
holder_class = {} # nom sans .wav : objet de la classe Make_sound

# réglage de la taille de polie en fonction du nombre de pixels de largeur
if  1000 <= width_screen <= 1300 :  
    fontfamily = {'normal' : ('Helvetica', '13'), 'petit': ('Helvetica', '9')}
elif width_screen < 1000:  
    fontfamily = {'normal' : ('Helvetica', '9'), 'petit': ('Helvetica', '7')}
elif width_screen > 1300:
    fontfamily = {'normal' : ('Helvetica', '15'), 'petit': ('Helvetica', '11')}

# ----------------------- Creation of a list of sounds ----------------------- #
# chemin d'accès au dossier sounds
soundpath = os.path.join(script_dir, "sounds")

# création d'une liste par ordre alphabétique de tous les noms de sons
wav_files = [f for f in os.listdir(soundpath) if os.path.isfile(os.path.join(soundpath, f))] 
wav_files.sort()

# initialisation d'un mixage audio avec un nombre de canaux égal au nombre de sons
pygame.mixer.init()
pygame.mixer.set_num_channels(len(wav_files))

# ---------------------------------------------------------------------------- #
#                               Hovering buttons                               #
# ---------------------------------------------------------------------------- #
class HoverButton(tk.Button):
    """classe de button qui change d'apparance en survolant"""    
    def __init__(self, master, enter, leave,**kw):
        tk.Button.__init__(self,master=master,**kw)
        self.enter = enter
        self.leave = leave
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        self['background'] = self.enter

    def on_leave(self, e):
        self['background'] = self.leave

class HoverCheckButton(tk.Checkbutton):
    """classe de button cochable qui change d'apparance en survolant"""

    def __init__(self, master, enter, leave,**kw):
        tk.Checkbutton.__init__(self,master=master,**kw)
        self.enter = enter
        self.leave = leave
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        self['background'] = self.enter

    def on_leave(self, e):
        self['background'] = self.leave

# ---------------------------------------------------------------------------- #
#                            Vertical scrolled frame                           #
# ---------------------------------------------------------------------------- #
# classe inspirée d'un code de l'utilisateur "Gonzo" de StackOverflow
class VerticalScrolledFrame(tk.Frame):
    """cadre possédant une barre de défilement vertical"""    
    def __init__(self, parent, *args, **kw):
        tk.Frame.__init__(self, parent, *args, **kw)
        self.parent=parent

        # création d'une toile et d'une barre de défilement verticale
        vscrollbar = tk.Scrollbar(self, orient=tk.VERTICAL)
        vscrollbar.pack(fill="y", side="right",expand=True)
        self.canvas = tk.Canvas(self, bd=0, highlightthickness=1,
                        yscrollcommand=vscrollbar.set)
        self.canvas.pack(fill="both", expand=True)
        vscrollbar.config(command=self.canvas.yview)
        
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # création d'un cadre dans la toile qui va défiler avec elle
        self.interior = interior = tk.Frame(self.canvas,bg="gray70")
        interior_id = self.canvas.create_window(0, 0, window=interior,
                                           anchor="nw")
        # repère les changements appliqués à la toile et au cadre ; les synchronise
        # met aussi à jour la barre de défilement
        def _configure_interior(event):
            # met à jour la barre pour correspondre à la taille du cadre interne
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            self.canvas.config(scrollregion="0 0 %s %s" % size)
            if interior.winfo_reqwidth() != self.canvas.winfo_width():
                # met à jour la largeur de toile pour correspondre au cadre interne
                self.canvas.config(width=interior.winfo_reqwidth())

        interior.bind('<Configure>', _configure_interior)
        
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != self.canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                self.canvas.itemconfigure(interior_id, width=self.canvas.winfo_width())
        self.canvas.bind('<Configure>', _configure_canvas)

    def _on_mousewheel(self, event):
        if len(wav_files) > 25:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

# ---------------------------------------------------------------------------- #
#                               Focusrite Control                              #
# ---------------------------------------------------------------------------- #
class Focusrite:
    """classe répertoriant callbacks pour les boutons de Focusrite Control"""
    def openfocusritecallback(self):
        """callback pour le bouton d'ouverture"""
        try:
            self.Focusrite_control = subprocess.Popen(path["focusrite_control"])
        except:
            messagebox.showerror(u"Erreur à l'ouverture de Focusrite Control",
                                 "Erreur dans l'ouverture de Focusrite Control,"
                                 " veuillez vérifier le chemin d'accès à l'application"
                                 "dans le fichier path.json")
    def endfocusritecallback(self):
        """callback pour le bouton de fermeture"""
        try:
            self.Focusrite_control.terminate()
        except:
            pass

# ---------------------------------------------------------------------------- #
#                                 Sound Buttons                                #
# ---------------------------------------------------------------------------- #
class Make_sound:
    """Classe utile à l'initialisation de buttons en fonction des 
    sons répertoriés, et de buttons lorsque les sons sont actifs.
    """    
    def __init__(self, name, parent, parent2, i, i2=False):
        """Initialisation

        Args:
            name (str): nom du son
            parent : frame parent de gauche
            parent2 : frame parent de droite
            i (int) : nombre colonnes de gauche
            i2 (bool, int): nombre colonnes de droite. Defaults to False.
        """        
        # variable de contrôle
        self.varbutton = tk.StringVar()

        self.name = name
        self.parent = parent
        self.parent2 = parent2
        self.soundpath = os.path.join(script_dir, "sounds","{}.wav".format(self.name))

        self.num = i
        # création d'images qui seront invisibles et qui règleront la taille des boutons tkinter
        self.pixel_button = tk.PhotoImage(width=int(width_screen/8), height=int(height_screen/8))
        self.pixel_setting = tk.PhotoImage(width=int(width_screen/11), height=int(height_screen/13))
        # valeurs par défaut des barres (volume, fader gauche-droite)
        self.vol = 100
        self.fader = 0.0
        # liste des couleurs dans le dégradé utilisé pour le volume, pas entre les couleurs 
        self.scale_color = ["forest green","green2","green yellow","yellow green",
                            "yellow3","orange","dark orange","orange red","red2","red4"]
        self.step_color = (len(self.scale_color)-1)/100

        self.soundbuttoncreator()

    def soundbuttoncreator(self):
        """Crée les boutons de gauche"""
        # création d'un cadre pour les boutons
        self.frame_button = tk.Frame(self.parent,bg="gray70", bd=3, relief="flat")
        # nombre de buttons par longeur/largeur
        self.rows_button = self.num//4 
        self.columns_button = self.num%4
        # création du bouton
        self.button = HoverCheckButton(self.frame_button, text=self.name.capitalize(), 
                                     indicatoron=False, selectcolor="DeepSkyBlue3", 
                                     background="light slate gray", 
                                     activebackground="LightSteelBlue3",
                                     variable=self.varbutton, command=self.launchsound, 
                                     cursor=cursor_plus, image=self.pixel_button,
                                     font=fontfamily["normal"], enter='chartreuse3',
                                     compound="c", leave='light slate gray') 
        self.button.pack()

        self.frame_button.grid(row=self.rows_button, column=self.columns_button)


    def play(self):
        """Joue le son"""
        self.sound = pygame.mixer.Sound(self.soundpath)
        self.chan = pygame.mixer.find_channel() # trouve un canal libre
        self.chan.play(self.sound,loops=-1) # boucle pour répéter le son indéfiniment

    def launchsound(self): 
        """Pilote ce qu'il faut faire quand un bouton de gauche est appuyé"""
        # si le son n'est pas en pause
        if self.name not in paused_buttons:
            # si le button est inactif
            if self.varbutton.get() == "1":
                # on le lance et on le note comme actif --> création du bouton
                self.button["cursor"] = cursor_black
                self.play()
                active_buttons.append(self.name)
                sounds_setting_buttons()

            else:
                # sinon on stop le bouton
                self.button["cursor"]=cursor_plus
                self.chan.stop()
                self.vol = 100
                self.fader = 0.0  
                active_buttons.remove(self.name)
                sounds_setting_buttons()    

        else:
            # sinon il va falloir gérer la pause (autre fonction)
            self.command_button_setting()

    def soundbuttonsettingcreator(self,i2,parent):
        """Crée les boutons de droite"""
        # création d'un cadre pour les boutons                
        self.frame_setting = tk.Frame(parent,bg="gray70", bd=3, relief="ridge")
        # nombre de buttons par longeur/largeur
        self.rows_setting = i2//3
        self.columns_setting = i2%3
        # échelle de volume
        self.volumescale = tk.Scale(self.frame_setting, orient='vertical', from_=100, 
                                    to=0, resolution=0.1,command=self.setvolume, 
                                    cursor=cursor_vertical,fg=self.scale_color[-1])
        self.volumescale.grid(row=0,column=1, rowspan=2, sticky="nsew")
        self.volumescale.set(self.vol)
        # échelle de spatialisation gauche-droite
        self.faderscale = tk.Scale(self.frame_setting, orient='horizontal', from_=-1, 
                                   to=1, resolution=0.01, command=self.setbalance, 
                                   cursor=cursor_horizontal)
        self.faderscale.grid(row=1,column=0, sticky="nsew")
        self.faderscale.set(self.fader)
        # bouton qui se crée quand le son est actif
        self.button_setting = HoverCheckButton(self.frame_setting, text=self.name.capitalize(), 
                                     indicatoron=False, selectcolor="DeepSkyBlue3", 
                                     background="light slate gray",
                                     activebackground="LightSteelBlue3",
                                     variable=self.varbutton, leave='light slate gray',
                                     cursor=cursor_black, image=self.pixel_setting,
                                     font=fontfamily["petit"], enter='chartreuse3',
                                     compound="c", command=self.command_button_setting) 

        self.button_setting.grid(row=0, column=0, sticky="nsew")

        self.frame_setting.grid(row=self.rows_setting, column=self.columns_setting)

    def setvolume(self,event):
        """Règle le volume en fonction de l'échelle"""
        self.vol = self.volumescale.get()
        self.volumescale["fg"] = self.scale_color[int(round(self.step_color*self.vol))]

        if self.varbutton.get() == "1":
            self.sound.set_volume(self.vol/100)


    def setbalance(self,event):
        """Règle la spatialisation gauche-droite en fonction de l'échelle"""
        if self.varbutton.get() == "1":
            self.fader = self.faderscale.get()
            if self.fader < 0:
                volLeft = 0.5-self.fader/2
                volRight = 1-volLeft
                self.chan.set_volume(volLeft,volRight)
            elif self.fader > 0:
                volRight = 0.5+self.fader/2
                volLeft = 1-volRight
                self.chan.set_volume(volLeft,volRight)
            else:
                self.chan.set_volume(0.5,0.5)

    def command_button_setting(self):
        """Pilote ce qu'il faut faire quand un bouton de droite est appuyé"""
        # si le button est inactif
        if self.varbutton.get() == "1":
            # on l'enlève de la pause
            self.button["cursor"] = cursor_black
            self.play()
            paused_buttons.remove(self.name)
            sounds_setting_buttons() 

        else:
            # sinon on le met sur pause
            self.button["cursor"] = cursor_plus
            self.chan.stop()
            paused_buttons.append(self.name)
            sounds_setting_buttons() 


# ---------------------------------------------------------------------------- #

def sounds_buttons(parent, parent2):
    """Crée une liste de sons sans le .wav et initialises des objets de la classe
    Make_sound qui sont rangés dans holder_class"""
    # pour i allant dans la liste des sons wav
    for i in range(len(wav_files)):
        # on remplit la liste de sons en enlevant le .wav
        name_sounds.append(wav_files[i][:-4])
   
    # pour i dans la liste de sons
    for i in range(len(name_sounds)):
        # on range dans une liste les objets de la classe Make_sound que l'on crée
        holder_class[name_sounds[i]] = Make_sound(name_sounds[i],parent,parent2,i)

def sounds_setting_buttons():
    """Crée les boutons de droite"""    
    # création d'un cadre contenant les boutons
    parent = tk.Frame(frame_fac_buttons, bg="gray70")
    parent.grid(row=0, rowspan=7, sticky="nsew", padx=5, pady=10)   
    # pour i dans la liste de sons actifs
    for i in range(len(active_buttons)):
        # on lance la méthode soundbuttonsettingcreator relative au son en question
        holder_class[active_buttons[i]].soundbuttonsettingcreator(i2=i,parent=parent)

def end_all():
    """Éteint tous les sons"""
    global active_buttons, paused_buttons # redéfinition globale de ces listes
    # pour i dans la liste de sons actifs
    for i in range(len(active_buttons)):
        try: #essaye de tout éteindre et remet les paramètres à 0
            holder_class[active_buttons[i]].varbutton.set("0")
            holder_class[active_buttons[i]].chan.stop()
            holder_class[active_buttons[i]].vol = 100
            holder_class[active_buttons[i]].fader = 0.0
        except: #il ne pourra pas y arriver si les sons sont en pause
            pass
    # on enlève tous les sons actifs et en pause
    active_buttons = []
    paused_buttons = []
    sounds_setting_buttons() # on recrée un cadre pour contenir des boutons (vide)

def pause_all():
    """Met en pause tous les sons"""
    # pour i dans la liste de sons actifs
    for i in range(len(active_buttons)):
        # met tout en pause
        holder_class[active_buttons[i]].varbutton.set("0")
        holder_class[active_buttons[i]].chan.stop()
        holder_class[active_buttons[i]].button["cursor"] = cursor_plus
        paused_buttons.append(active_buttons[i])

# ---------------------------------------------------------------------------- #
#                                   Creation                                   #
# ---------------------------------------------------------------------------- #

# ------------------------------ Initialisation ------------------------------ #

# parent : création d'un cadre pour contenir celui qui défile les boutons à gauche
frame_buttons = tk.Frame(root,bd=5,bg="gray70")
frame_buttons.grid(row=1, column=0, rowspan=8, columnspan=6, padx=5, pady=0, sticky="nsew")
scframe_1 = VerticalScrolledFrame(frame_buttons)
scframe_1.pack(fill="both", expand=True)

#parent2 : création d'un cadre pour contenir celui qui range les boutons à droite
frame_fac_buttons = tk.Frame(root,bd=5,bg="gray70") 
frame_fac_buttons.grid(row=1, column=6, rowspan=8, columnspan=4, padx=5, sticky="nsew")

# --------------------------------- Focusrite -------------------------------- #

focusrite = Focusrite() # on récupère les callbacks 
# on crée les deux boutons de Focusrite Control
Button_open_focusrite = HoverButton(root, text="Ouvrir Focusrite Control", 
                                  command=focusrite.openfocusritecallback, 
                                  cursor=cursor_plus, background="light slate gray", 
                                  activebackground="LightSteelBlue3", 
                                  leave='light slate gray', enter='purple1',
                                  font=fontfamily["petit"])
Button_open_focusrite.grid(row=9, column=0, columnspan=5, sticky="wens", padx=5, pady=3)
Button_end_focusrite = HoverButton(root, text="Fermer Focusrite Control", leave='light slate gray',
                                 command=focusrite.endfocusritecallback, cursor=cursor_end, 
                                 background="light slate gray", activebackground="LightSteelBlue3",
                                 font=fontfamily["petit"], enter='purple1')
Button_end_focusrite.grid(row=9, column=5, columnspan=5, sticky="wens", padx=5, pady=3)

# ------------------------------ Boutons gauche ------------------------------ #
# on lance la création des boutons à gauche
sounds_buttons(scframe_1.interior,frame_fac_buttons)

# ----------------------------------- logo ----------------------------------- #
# on rajoute le logo HUG
hug = Image.open(os.path.join(script_dir, "logo","hug.png"))  
hug = hug.resize((int(2273/11), int(583/11)), Image.ANTIALIAS)
img = ImageTk.PhotoImage(hug)
panel = tk.Label(root, image=img)
panel.grid(row=0,column=0,sticky="nw") 

# ------------------------------ Boutons droite ------------------------------ #
# on crée les boutons à droite
sounds_setting_buttons()

# ----------------------------- Arrêter les sons ----------------------------- #
# on crée les boutons de pause/arrêt
#pause
Button_pause = HoverButton(root, text="Mettre sur pause tous les sons", command=pause_all, 
                           cursor=cursor_wait, background="light slate gray", enter='yellow2',
                           activebackground="LightSteelBlue3", font=fontfamily["normal"],
                           leave='light slate gray')
Button_pause.grid(row=7, column=6,padx=5,rowspan=1, columnspan=4,sticky="nsew")

#arrêt
Button_end_all = HoverButton(root, text="Arrêter tous les sons", command=end_all, leave='light slate gray',
                           cursor=cursor_end, background="light slate gray", enter='red',
                           activebackground="LightSteelBlue3", font=fontfamily["normal"])
Button_end_all.grid(row=8, column=6,padx=5,rowspan=1, columnspan=4,sticky="nsew")

# ---------------------------------------------------------------------------- #
#                               Responsive Desgin                              #
# ---------------------------------------------------------------------------- #
# on autorise l'augmentation de colomnes et lignes selon l'écran
for i in range(1, 9):
    root.grid_rowconfigure(i, weight=1)
for i in range(6,10):
    root.grid_columnconfigure(i, weight=1)

# ---------------------------------------------------------------------------- #
#                               Volume de Windows                              #
# ---------------------------------------------------------------------------- #

def askvolume():
    """boite de dialogue qui permet de s'assurer que l'utilisateur a bien réglé 
    le volume de son ordinateur"""
    result = messagebox.askyesno("Attention au volume !",
                                 u"Avez-vous bien correctement réglé le volume "
                                 "principal de Windows ? Cela pourrait dans le "
                                 "cas contraire être très dangeureux pour le/la "
                                 "patient(e) et vous-même !")
    if result:
        pass
    else:
        root.destroy() # quitte l'application

askvolume() # on ajoute la boite de dialogue au lancement de l'application

# ---------------------------------------------------------------------------- #
#                                     ROOT                                     #
# ---------------------------------------------------------------------------- #
# on lance l'application
root.mainloop()
