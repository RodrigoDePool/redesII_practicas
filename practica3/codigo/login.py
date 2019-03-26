# import the library
from tkinter import *
from appJar import gui
from PIL import Image, ImageTk
from protocolo import Protocolo
from usuario import Usuario
import numpy as np
import cv2
import json

"""
    Esta clase se encarga de gestionar todo el proceso de logueo de la
    aplicacion.
"""
class Login(object):

    NAME='LOGIN'
    USERS='data/users'
    


    # Esta funcion inicializa la gui para el login
    def __init__(self, window_size):
        
        # Creamos una variable que contenga el GUI del login
        self.app = gui(self.NAME, window_size)
       
        # Cargamos fichero de usuarios ya registrados
        try:
            f = open(self.USERS)
            self.users = json.load(f)
            f.close()
        except:
            self.users = {}

        # Establecemos gui inicial
        self.set_initial_window()
        
        # Establecemos tiempo para refrescado de la gui y el evento para bloquear y desbloquear botones
        self.app.setPollTime(20)
        self.app.registerEvent(self.unblock_button)
    
        # Diccionario que relaciona funciones con botones (forma elegante de elifs)
        self.button_funcs = { 'Registrarse': self.registrarse,
                                'Conectarse': self.conectarse,
                                'Salir': self.salir,
                                'Registrar': self.registrar,
                                'Entrar': self.entrar,
                                'Atras': self.atras}



    # Esta funcion inicia la gui de login
    def start(self):
        self.app.go()



    # Esta funcion se encarga de inicializar la gui para que muestra el estado 
    # inicial de la aplicacion
    def set_initial_window(self):
        self.app.removeAllWidgets()
        self.app.addButtons(['Registrarse', 'Conectarse', 'Salir'], self.buttons_call)
        # Indicamos que no queremos bloquear botones
        self.consider_port = None



    # Esta funcion se encarga de eliminar todos los widgets y agregar las entradas
    # de texto comunes para el panel de registro y de conexion
    def __set_common_entries(self):
        self.app.removeAllWidgets()
        # Preparacion del interfaz
        self.app.addLabel('Indicador','')
        self.app.addLabelEntry('Usuario')
        self.app.addLabelSecretEntry('Clave') 
        self.app.setFocus('Usuario')



    # Esta funcion se encarga de mostrar la gui para poder registrar un usuario en la
    # aplicacion
    def set_register_window(self):
        # Establecemos interfaz
        self.__set_common_entries()
        self.app.addLabelEntry('Puerto de control')
        self.app.addLabelEntry('Puerto de video')
        self.app.addLabelEntry('IP')
        self.app.addButtons(['Registrar', 'Atras', 'Salir'], self.buttons_call)
        # Indicamos que queremos bloquear botones considerando el puerto
        self.consider_port = True



    # Esta funcion se encarga de mostrar al usuario el panel para acceder con una cuenta
    # ya creada previamente
    def set_conection_window(self):
        # Configuramos la interfaz
        self.__set_common_entries()
        self.app.addButtons(['Entrar', 'Atras', 'Salir'], self.buttons_call)
        # Indicamos bloqueo de botones sin considerar el puerto
        self.consider_port = False



    # Esta funcion es un evento que se encarga de bloquear o desbloquear botones
    # dependiendo de la ventana en que se este.
    # Si consider_port es None entonces este evento no hace nada
    # Si consider_port es True se asume que se esta en la ventana de registrarse
    #  (que tiene ademas entradas para ip y puerto)
    # Si consider_port es False se asume que se esta la ventana de conectarse
    def unblock_button(self):
        # Si no hay que bloquear botones
        if self.consider_port is None: return
        
        # Configuramos si estamos en la ventana de registrarse (con puerto) o de conexion
        if self.consider_port:
            aux = ('' == self.app.getEntry('Puerto de control')) or ('' == self.app.getEntry('Puerto de video')) or ('' == self.app.getEntry('IP'))
            button = 'Registrar'
        else:
            aux = False
            button = 'Entrar'
        
        # Bloqueamos en caso de que algun campo este vacio
        if '' == self.app.getEntry('Usuario') or '' == self.app.getEntry('Clave') or aux:
            self.app.getButtonWidget(button).config(state=DISABLED)
        else:
            self.app.getButtonWidget(button).config(state=NORMAL)
    


    # Funcion que gestiona los callbacks de los botones.
    def buttons_call(self, button):
        # Para gestionar los callbacks aprovechamos el diccionario que nos indica la
        # funcion a utilizar
        return self.button_funcs[button]()
        
     

    # Funcion auxiliar para registrar un usuario (o renovarlo) en el servidor.
    # Tambien se encarga de actualizar el diccionario de usuarios y guardarlo en USERS
    # En caso de registro con exito cierra la gui e indica el usuario en Usuario.APP_USER
    # En caso de error lo indica en la interfaz
    def __user_register(self, usuario, clave, port, ip, udp_port):
        # Llamamos al protocolo para que registre/renueve el usuario
        result = Protocolo.register(usuario,clave,port,ip)
        
        if result:
            # Caso efectivo
            # Guardamos el nuevo diccionario con el usuario registrado
            self.users[usuario]={'port': port, 'ip': ip, 'udp_port': udp_port}
            with open(self.USERS, 'w') as f:
                json.dump(self.users, f)

            # Indicamos el usuario que se ha creado y cerramos el interfaz
            Usuario.APP_USER = Usuario(usuario, port, udp_port)
            self.app.stop()
        else:
            # Caso de fallo
            # indicamos error
            ind = self.app.getLabelWidget('Indicador')               
            ind.config(text='Usuario o clave invalido.')



    # Funcion a ejecutar cuando hay que salir. Simplemente cierra la interfaz
    def salir(self):
        self.app.stop()



    # Funcion que se ejecuta cuando se presiona el boton de registrarse
    # Establece la ventana de registrarse
    def registrarse(self):
        self.set_register_window()



    # Funcion que se ejecuta cuando se presiona el boton de conectarse
    # Establece la ventana de conexion
    def conectarse(self):
        self.set_conection_window()



    # Esta funcion se encarga de registrar un usuario utilizando los campos de texto
    # de la interfaz.
    # Si hay fallo se indica en la interfaz
    # Si se registrar entonces se guarda el usuario en Usuario.APP_USER, se actualiza 
    #  el diccionario y se  se cierra la interfaz
    def registrar(self):
        # Obtenemos valores
        usuario = self.app.getEntry('Usuario')
        clave = self.app.getEntry('Clave')
        port = self.app.getEntry('Puerto de control')
        ip = self.app.getEntry('IP')
        udp_port = self.app.getEntry('Puerto de video')
        # Registramos
        self.__user_register(usuario, clave, port, ip, udp_port)



    # Esta funcion se ejecuta al presionar el boton Atras. Se encarga de volver 
    # a la ventana inicial
    def atras(self):
        self.set_initial_window()



    # Esta funcion se encarga de obtener el usuario y la clave de los campos de la
    # interfaz. Posteriormente busca en el diccionario de usuarios registrados el puerto.
    # Luego renueva en el servidor este usuario, indica en la aplicacion el usuario a
    # utilizar (Usuario.APP_USER) y cierra la interfaz.
    # En caso de fallo lo indica en un texto.
    def entrar(self):
        # Obtenemos valores de campos
        usuario = self.app.getEntry('Usuario')
        clave = self.app.getEntry('Clave')
        
        # Buscamos el usuario en el diccionario para obtener el puerto.
        if usuario not in self.users.keys():
            # Caso en que el usuario no esta en el dicc. Se indica en la interfaz.
            ind = self.app.getLabelWidget('Indicador')
            ind.config(text='Este usuario no ha sido registrado desde este ordenador, no tenemos el puerto correspondiente. Intente registrar un nuevo usuario')
            return
        
        port = self.users[usuario]['port']
        ip = self.users[usuario]['ip']
        udp_port = self.users[usuario]['udp_port']
        # Renovamos el usuario y cerramos la interfaz.
        self.__user_register(usuario, clave, port, ip, udp_port)
        return

