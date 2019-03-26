# import the library
from tkinter import *
from appJar import gui
from PIL import Image, ImageTk
import numpy as np
import cv2
import time
import heapq
from socket import *
from protocolo import Protocolo
from usuario import Usuario
from threading import Thread, Event, Lock

########################################################################################
#       ESTRUCTURA DEL FICHERO ACTUALMENTE 2018-4-11
#       PRESERVAR EN LA MEDIDA DE LO POSIBLE PARA QUE ESTOS COMENTARIOS
#       PUEDAN SEGUIR TENIENDO SENTIDO
#
#   1º Muchas macros (states, nombres de frames y otros componentes)
#   2º Funcion init, que dibuja la pantalla base del estado LOGGED
#   3º Mil funciones de crean todos los frames que se dibujan en init
#   4º Func q se activan ante eventos en la pantalla (press buttons y eso)
#   5º A partir de aqui, sin orden ni concierto (1º cosas rodri,2º de oscar)
#
############################################################################

# Macros utiles para el programa
STATE_LOGIN='LOGIN'
STATE_LOGGED='LOGGED'
STATE_CALL='INCALL'
STATE_WAIT_ANSWER='WAITING'
STATE_HOLD='ONHOLD'
STATE_END='END' #FIN DE APLICACION

MAX_QUEUE_SIZE = 100

class VideoClient(object):

    NAME='HOLA'
    # this variable MUST be protected with a mutex
    STATE=STATE_LOGIN   

    # MAS O MENOS EN ORDEN VISUAL, MACROS PARA LOS COMPONENTES
    # Panel izquierdo,
    USERS_PANE = 'usersPane'
    # donde cada user tiene su frame (label + button)
    USER_FRAME = 'userFrame'
    # Panel dcho,
    RIGHT_FRAME = 'right'
    # en cuya mitad inferior
    RESULTS_FRAME = 'resultsFrame'
    # tenemos el cuadro de busqueda (entry + button)
    BUSQUEDA_FRAME = 'busquedaFrame'
    BUSQUEDA_ENTRY = 'busquedaEntry'
    BUSQUEDA_BUTTON = 'Buscar'
    # y el scroll con los resultados
    RESULTS_PANE = 'resultsPane'
    # cada resultado con su frame (label + button)
    RESULT_FRAME = 'resultFrame_'
    # Al final, un frame con botones (log out, salir)
    BUTTONS_FRAME = 'buttonsFrame'
    LOGOUT = 'Log out'
    QUIT = 'Salir'
    WE_COOL = 'Somos guays'
    # Que seran botones de colgar/ pausar en caso de estar en
    # una llamada
    LLAMADA_BUTTONS_FRAME = 'llamadaButtonsFrame'
    HOLD = 'Llamada en espera'
    RESUME = 'Reanudar llamada'
    HANG = 'Colgar'
    # Y unas ultimas para las macros que usan las funciones 
    # que cambian entre los botones que se muestran cuando estas
    # en una llamada y cuando no estas en una llamada
    TO_CALL = 'changeToCall'
    FROM_CALL = 'changeFromCall'
    # Es el tiempo en segundos que tardara el hilo de escucha de puertos en revisar
    #  cada flag del sistema para saber cuando debe salir 
    TIMEOUT=3
    # Maximo de paquete a recibir
    MAX_LISTEN = 8192
    #SubWindow waiting for answer
    WAITING_WINDOW='waiting_window'
    # Subwindow for information
    INFO = 'info'
    # Este diccionario contendra los usuarios resultado de la ultima busqueda
    searchDic = {}
    # Y este la lista de todos los usuarios despues de la ultima busqueda
    usersDic = {}



    def __init__(self, window_size):
        # Creamos una variable que contenga el GUI principal
        self.app = gui(self.NAME, window_size)
        self.app.setBg('#e6ffff')
 
        # Panel izquierdo: lista usuarios
        self.__left_frame()
        # Panel derecho: video, busquedas, botones inferiores
        self.__right_frame()       
        # Barra de estado
        # Debe actualizarse con información útil sobre la llamada (duración, FPS, etc...)
        self.app.addStatusbar(fields=2)
        # Agregamos funcion de cerrado
        self.app.setStopFunction(self.__cerrar)

    ########################################################################
    #
    #       A CONTINUACION, MIL FUNCIONES CREADORAS DE FRAMES. 
    #      RODRI: SI BUSCAS DOCUMENTACION, ESTAN EN ESTE ORDEN:
    #
    #  left_frame:          mitad izda de la pantalla (scroll con users)
    #
    #  right_frame:         mitad dcha de la pantalla
    #       video_frame:    frame que con la pantalla del video
    #       search_frame:   frame con la entrada de texto, boton de buscar
    #                       y scrollPane con los resultados de busqueda
    #       logged_buttons: frame con los botones de salir y log out,
    #                       que son los que corresponden al estadp LOGGED
    #       incall_buttons: frame con los botones de colgar y pausar, 
    #                       que son los que corresponden al estado INCALL
    #
    ########################################################################

    # Crea label frame a la izqda de la pantalla con un scroll pane con los 
    # usuarios registrados, al lado cada uno de un boton que permite llamar
    def __left_frame(self):
        self.app.startLabelFrame('Registered users', row=0, column=0)
        self.app.setSticky('we')
        self.app.startScrollPane(self.USERS_PANE, column=0, row=0, rowspan=2)

        self.usersDic = Protocolo.list_users()
        for user, i in zip(self.usersDic, range(len(self.usersDic))):
            #Aniadimos i-esimo frame
            self.app.startFrame(self.USER_FRAME + user, row = i, column = 0, colspan = 2)
            self.app.setSticky("nws")
            self.app.setExpand("both")
            #Metemos dentro button y label
            self.app.addIconButton('call.' + user,
                    self.__call,
                    'md-camera-video', i, 0,1)
            self.app.addLabel(user, user, i, 1, 1)            
            self.app.stopFrame()
        
        self.app.stopScrollPane()       
        self.app.stopLabelFrame()
    
    # Crea frame con toda la info de la derecha (video, busqueda, botones)
    def __right_frame(self): 
        self.app.startFrame(self.RIGHT_FRAME, row=0, column=1)
        # Panel derecho: video
        self.__videoFrame()
        # Panel derecho: busqueda (entry, boton, resultados de busqueda)
        self.__search_frame()
        # Panel derecho: buttons de abajo (salir, log out)
        self.__logged_buttons()
        # Alternativa para estado de llamada:
        # Panel derecho: buttons de llamada (colgar, pausar)
        self.__incall_buttons()
        self.app.stopFrame()
        
    # Incluye en el frame padre la reproduccion de video 
    def __videoFrame(self):
        # Aniadimos la pantalla del video
        self.app.addImage('video', 'imgs/webcam.gif')
        
        # Registramos la función de captura de video
        # Esta misma función también sirve para enviar un vídeo
        # La variable video controla que se va a reproducir 
        # (0 es camara o path a video)
        self.video = 0
        self.our_video = cv2.VideoCapture(self.video)
        # Set fps with poll time (fps = 1000/poll_time)
        self.poll_time = 20
        self.app.setPollTime(self.poll_time)
        self.app.registerEvent(self.capturaVideo)
        #self.app.events.remove(self.capturaVideo)

        
    # Crea frame con una entry de texto y un boton de buscar en la parte
    # superior, y un scroll con los resultados de busqueda en la inferior,
    # cada resultado al lado de un boton que permite llamar al usuario
    def __search_frame(self):
        self.app.startFrame(self.RESULTS_FRAME, row=1, column=0)

        # Aniadimos un frame para el boton buscar y la entrada de texto
        self.app.startFrame(self.BUSQUEDA_FRAME, row=0, column=0)
        self.app.addButton(self.BUSQUEDA_BUTTON, self.__pressBusqueda, 0, 0)
        self.app.addEntry(self.BUSQUEDA_ENTRY, 0, 1)
        self.app.stopFrame()

        # Y el scroll pane con los resultados de busqueda
        self.app.startScrollPane(self.RESULTS_PANE, column=0, row=1, rowspan=2)
        self.app.stopScrollPane()
        self.app.stopFrame()
    
    # Crea frame con los botones de logout, somos guays y salir
    def __logged_buttons(self):
        self.app.startFrame(self.BUTTONS_FRAME, row = 2, column = 0)
        self.app.addButton(self.LOGOUT, self.__logout, 0, 0)
        self.app.addButton(self.WE_COOL, None, 0, 1)
        self.app.addButton(self.QUIT, self.__salir, 0, 2)
        self.app.stopFrame()
    
    # Crea frame con los botones de colgar y pausar/reanudar llamada
    def __incall_buttons(self):
        self.app.startFrame(self.LLAMADA_BUTTONS_FRAME, row = 2, column = 0)
        self.app.addButton(self.RESUME, self.hold_resume, 0, 0) 
        self.app.addButton(self.HOLD, self.hold_resume, 0, 0)
        self.app.addButton(self.HANG,  self.__hang, 0, 1)
        self.app.stopFrame()
        # Lo escondemos por ahora
        self.app.hideWidgetType(gui.C_FRAME, self.LLAMADA_BUTTONS_FRAME)
          





    ########################################################################
    #
    #   ADIOS CREADORES DE FRAMES INICIALES, HOLA MANEJADORES DE EVENTOS
    #
    #   En orden:
    #   press_busqueda      (eso que ocurre cuado presionas buscar)
    #   update_results_pane (auxiliar para press_busqueda)
    #   change_buttons      (swap entre frames con los botones inferiores)
    #   capturar_video      (permite ir mostrando las imagenes de la camara)
    #   salir               (salida de la aplicacion)
    #   logout              (vuelta a la pantalla de login)
    #   change_call_buttons (cambia botones inferiores para estado de llamada)
    #   
    #   Hay mas, pero como no estan implementadas pues me callo
    #
    ########################################################################    
    

    # Cuando se presiona el boton buscar, hay que borrar el scroll pane de 
    # resultados de ese momento, ver cuantos usuarios matchean con el crite
    # rio de busqueda y redibujar el scroll pane con los nuevos resultados
    def __pressBusqueda(self, busquedaButton):
        search = self.app.getEntry(self.BUSQUEDA_ENTRY)
        # Borramos info antigua: frame, label y button, y el scrollPane
        self.app.openFrame(self.RESULTS_FRAME)
        try:
            for nick in self.searchDic:
                self.app.removeWidgetType(gui.BUTTON, 'callResult.' + nick)
                self.app.removeWidgetType(gui.FRAME, self.RESULT_FRAME + nick)
                self.app.removeWidgetType(gui.LABEL, 'result_' + nick)
            self.app.removeWidgetType('scrollPane', self.RESULTS_PANE)

        except Exception as e:
            print(e)
        # No usamos los users de usersDic in case hay nuevos registrados
        # Aprovechamos para actualizar el diccionario de todos los users
        self.searchDic = {} 
        self.usersDic = Protocolo.list_users()
        for nick in self.usersDic:
            # Si la string buscada coincide con el nick, lo aniadimos al diccionario
            if search in nick:
                self.searchDic[nick] = self.usersDic[nick]
        
        # Y actualizamos el scroll pane de los resultados con los nuevos resultados  
        self.__update_results_pane()

    # Redibuja el scroll pane de los resultados con los usuarios que haya en ese 
    # momento en el diccionario searchDic. Para cada usuario, un frame con una
    # label con su nombre y un botoncito de llamada
    def __update_results_pane(self):
        self.app.openFrame(self.RESULTS_FRAME)
        self.app.startScrollPane(self.RESULTS_PANE, column=0, row=1, rowspan=2)
        for nick, i in zip(self.searchDic, range(len(self.searchDic))):
            #Aniadimos i-esimo frame
            self.app.startFrame(self.RESULT_FRAME+ nick, row = i, column = 0, colspan=2)
            self.app.setSticky("nws")
            #Metemos dentro button y label
            self.app.addIconButton('callResult.'+nick, 
                    self.__call,
                    'md-camera-video',row=i)
            self.app.addLabel('result_' + nick, nick, row=i, column=2)
            self.app.stopFrame()
        self.app.stopScrollPane()
        self.app.stopFrame()
        
    # Funcion de prueba para ver que tal va eso de congelar el video y 
    # hacer swap de botones
    def hold_resume(self, button):
        nick = self.calling_user
        tcp_port = int(self.usersDic[nick]['port'])
        ip = self.usersDic[nick]['ip']
        tcp_socket = socket(AF_INET, SOCK_STREAM)
        tcp_socket.settimeout(5)

        if str(button) == self.HOLD:
            # Intercambiamos
            self.app.hideWidgetType(gui.BUTTON, self.HOLD)
            self.app.showWidgetType(gui.BUTTON, self.RESUME)
            # Congelamos
            self.on_hold.set()
            # Notificamos al otro usuario
            try:
                tcp_socket.connect((ip,tcp_port))
                Protocolo.call_hold(Usuario.APP_USER.nick ,tcp_socket)
                tcp_socket.close()
            except:
                pass
        if str(button) == self.RESUME:
            # Intercambiamos
            self.app.hideWidgetType(gui.BUTTON, self.RESUME)
            self.app.showWidgetType(gui.BUTTON, self.HOLD)
            # Descongelamos
            self.on_hold.clear()
            # Notificamos al otro usuario 
            try:
                tcp_socket.connect((ip,tcp_port))
                Protocolo.call_resume(Usuario.APP_USER.nick ,tcp_socket)
                tcp_socket.close()
            except:
                pass
        return

    # Intercambia los 2 frames inferiores en los estados de in call/logged
    # Su funcionalidad cambiara, es solo para probar botonsitos
    def __change_buttons(self, button):
        if str(button) == self.WE_COOL:
            self.app.hideWidgetType(gui.C_FRAME, self.BUTTONS_FRAME)
            self.app.showWidgetType(gui.C_FRAME, self.LLAMADA_BUTTONS_FRAME)
        elif str(button) == self.HANG:
            self.app.hideWidgetType(gui.C_FRAME, self.LLAMADA_BUTTONS_FRAME)
            self.app.showWidgetType(gui.C_FRAME, self.BUTTONS_FRAME)
    
    # Función que captura el frame a mostrar en cada momento en la pantalla
    # de video
    def capturaVideo(self):
        # Try por si la camara esta en uso
        try:
            if self.STATE != STATE_CALL and self.STATE != STATE_HOLD:
                # Reestablecemos el firstLoad para la siguiente llamada
                self.firstLoad = True
                # Si no  estamos en una llamada
                # Capturamos un frame de la cámara o del vídeo
                ret, frame = self.our_video.read()
            else:
                # Recibimos frames
                # Configurar tam
                self.our_frame = cv2.resize(self.our_frame, (250,150))
                
                lon = len(self.queue)
                
                # Comprobamos que al principio de la llamada el buffer se llena
                # yn minimo
                if self.firstLoad:
                    if lon > MAX_QUEUE_SIZE/32: 
                        self.firstLoad = False
                        ts, frame = heapq.heappop(self.queue)
                        self.last_ts = ts
                    else:
                        frame = None 
                else:
                    if lon == 1:
                        ts, frame = self.queue[0]
                    elif lon > 1: 
                        ts, frame = heapq.heappop(self.queue)
                    
                    # Cambiamos los fps (equivale a cambiar el polltime) segun 
                    # la diferencia de los 2 ultimos paquetes recibidos
                    self.setfps(ts)
                    self.last_ts = ts 

                # Try para el caso concreto en la que el primer paquete udp no ha llegado
                try:        
                    frame[0:self.our_frame.shape[0], 0:self.our_frame.shape[1]] = self.our_frame
                except:
                    frame = self.our_frame
          
            # Imprimimos el fotograma por pantalla
            frame = cv2.resize(frame, (400,300))
            #Formato gui
            cv2_im = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            img_tk = ImageTk.PhotoImage(Image.fromarray(cv2_im))
            # Mostrar en gui
            self.app.setImageData('video', img_tk, fmt = 'PhotoImage')
        except:
            pass
        return

    
    # Salida de la aplicacion cuando presionas boton salir
    def __salir(self, button=None):
        # Marcamos el cambio de estado a END 
        self.state_lock.acquire()
        VideoClient.STATE = STATE_END
        self.state_lock.release()
        # Cerramos
        self.app.stop()
    

    # Funcion para cerrar la gui
    def __cerrar(self):
        #Indicamos a los hilos de escucha y llamada que deben cerrarse
        self.end_gui.set()
        self.end_call.set()
        # Cerramos el uso de la camara
        self.our_video.release()
        # Indicamos que se cierre la gui
        return True

    # Sale de la pantalla de logged y vuelve a la pantalla
    # de login
    def __logout(self, button):
        # Marcamos el cambio de estado a LOGIN 
        self.state_lock.acquire()
        VideoClient.STATE = STATE_LOGIN
        self.state_lock.release()
        # Quitamos el usuario ya que hacemos logout
        Usuario.APP_USER = None
        # Cerramos app
        self.app.stop()

    # Funcion para cambiar los botones (dcha, abajo) entre llamada
    # y no llamada (en caso de llamada permiten pausar o colgar)
    # El cambio se hace en funcion del argumento changeToOrFromCall
    # (TO_CALL pone los botones de la llamada)
    def __change_call_buttons(self, changeToOrFromCall):
        if changeToOrFromCall == self.TO_CALL:
            self.app.hideWidgetType(gui.C_FRAME, self.BUTTONS_FRAME)
            self.app.showWidgetType(gui.C_FRAME, self.LLAMADA_BUTTONS_FRAME)
        elif changeToOrFromCall == self.FROM_CALL:
            self.app.hideWidgetType(gui.C_FRAME, self.LLAMADA_BUTTONS_FRAME)
            self.app.showWidgetType(gui.C_FRAME, self.BUTTONS_FRAME)

    ###############################################################
    #             A PARTIR DE AQUI, NADA ORGANIZADO
    ###############################################################

    ###############################################################
    #             ESTO ES DE RODRI
    ###############################################################
    

    # Se encarga de gestionar el presionado de un boton de llamada. Es necesario
    # que se de el nick del usuario a llamar para esto quizas se pueda usar una 
    # lambda del tipo lambda x: self.__call(self, x, nick).
    # Esta funcion se encarga mandar el paquete de llamada, abrir socket udp en variable
    #  self.sock_udp, cambiar el estado y la variable de usuario llamado.
    # Finalmente abre un popup WAITING_WINDOW donde se le informa al usuario de que esta
    # ocurriendo (esta ventana sera luego modificada por el hilo de control. 
    def __call(self, button):
        # Solo podemos llamar cuando estamos en estado de logged
        self.state_lock.acquire()
        if self.STATE != STATE_LOGGED:
            self.state_lock.release()
            return
        self.state_lock.release()


        nick = button[button.find('.')+1:]
        # Variable utiles del usuario a llamar
        tcp_port = int(self.usersDic[nick]['port'])
        ip = self.usersDic[nick]['ip']
        
        self.state_lock.acquire()
        # Abrimos un socket UDP
        self.sock_udp = socket(AF_INET, SOCK_DGRAM)
        udp_port = int(Usuario.APP_USER.udp_port)
        self.sock_udp.bind(('',udp_port))
        # Intentamos abrir el puerto y enviar paquete de llamada 
        # si fallamos solo cerramos la comunicacion (posibles ips o puertos malformados)
        try:
            tcp_socket = socket(AF_INET, SOCK_STREAM)
            # Timeout para conectar con el otro usuario
            tcp_socket.settimeout(5)
            tcp_socket.connect((ip, tcp_port))
            Protocolo.call(Usuario.APP_USER.nick , udp_port, tcp_socket)
            tcp_socket.close()
        except Exception as e:
            print(e)
            # Borramos info anterior
            try:
                self.app.destroySubWindow(self.INFO)
            except:
                pass
            # Indicamos que el servidor no logra conectarse
            self.app.startSubWindow(self.INFO, modal=True)
            self.app.addLabel('Indicacion2','El usuario esta offline')
            self.app.stopSubWindow()
            self.app.showSubWindow(self.INFO)
            # Cerramos
            self.sock_udp.close()
            self.state_lock.release()
            return
        
        # Indicamos que estamos a la espera de respuesta por parte del usuario con nick
        self.STATE = STATE_WAIT_ANSWER
        self.state_lock.release()
        self.calling_user_lock.acquire()
        self.calling_user = nick
        self.calling_user_lock.release()
        
        # Creamos una nueva ventana  (recordar que hay que destruir la anterior)
        try:
            self.app.destroySubWindow(self.WAITING_WINDOW)
        except:
            pass

        self.app.startSubWindow(self.WAITING_WINDOW, modal=True)
        self.app.addLabel('Indicacion','Esperando respuesta de la llamada')
        self.app.addButton('Cancelar', self.cancel_call)
        self.app.stopSubWindow()
        # Lanzamos la subwindow
        self.app.showSubWindow(self.WAITING_WINDOW)
        return

    def __hang(self, button):
        nick = self.calling_user
        self.state_lock.acquire()
     
        # Enviamos fin de conexion
        try:
            tcp_socket = socket(AF_INET, SOCK_STREAM)
            # Timeout para conexion con el otro usuario
            tcp_socket.settimeout(5)
            tcp_socket.connect((self.usersDic[nick]['ip'], int(self.usersDic[nick]['port'])))
            Protocolo.call_end(Usuario.APP_USER.nick, tcp_socket)
            tcp_socket.close()
        except Exception as e:
            pass

        self.__change_call_buttons(self.FROM_CALL)
        # Finalizamos la llamada
        self.end_call.set()
        self.STATE = STATE_LOGGED
        self.state_lock.release()
        return




    # Funcion de manejador del boton de cancelacion de una llamada.
    # Se encarga de reestablecer variables de estado y llamada de usuario
    # Ademas, destruye la ventana popup
    def cancel_call(self, button=None):
        # Volvemos a estado de login y cambiamos usuario a NOne
        self.state_lock.acquire()
        self.calling_user_lock.acquire()
        self.STATE=STATE_LOGGED
        self.calling_user = None
        self.calling_user_lock.release()
        self.state_lock.release()
        # Destruimos ventana
        self.app.destroySubWindow(self.WAITING_WINDOW)
        return




    ###############################################################
    #             Y ESTO COSAS QUE YA ESTABAN
    ###############################################################
    
    # Establece la resolución de la imagen capturada
    def setImageResolution(self, resolution):        
        # Se establece la resolución de captura de la webcam
        # Puede añadirse algún valor superior si la cámara lo permite
        # pero no modificar estos
        if resolution == "LOW":
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 160) 
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 120) 
        elif resolution == "MEDIUM":
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320) 
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240) 
        elif resolution == "HIGH":
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640) 
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480) 

    def start(self):
        VideoClient.STATE = STATE_LOGGED
       
        # Creamos eventos que nos serviran de flags para indicar acciones a los hilos:
        #  Uno para indicar que la aplicacion debe finalizar (end_gui).
        #  Uno para indicar que la llamada se debe finalizar (end_call).
        #  Uno para indicar que la llamada deebe poner en espera (on_hold)
        self.end_gui =  Event()
        self.end_call = Event()
        self.on_hold = Event()
        # Las inicializamos a falso
        self.end_gui.clear()
        self.end_call.clear()
        self.on_hold.clear()
       
        # Inicializamos la variable del firstLoad
        self.firstLoad = True

        # Creamos una variable que nos indica el usuario con el que estamos o queremos
        #  establecer una comunicacion. Ademas de un Lock para esa variable
        self.calling_user = None
        self.calling_user_lock = Lock()
        # Creamos un Lock para la variable de estado
        self.state_lock = Lock()
        
          # Creamos un hilo para escuchar por el puerto de control y lo corremos
        tcp_listener = Thread(target=self.control_port_listen)
        tcp_listener.start()

        # Creamos unas variables para que el evento de la interfaz actualice 
        # los frames cuando estamos en llamada
        self.our_frame = None
        self.their_frame = None
        # Creamos cola para la recepcion de mensajes
        self.queue = []

        self.last_ts = 0


        # Lanzamos la gui
        self.app.go()
        



    ###############################################################
    # A partir de aqui tenemos las funciones que seran utilizadas
    #  por los multiples hilos que abre la interfaz
    ###############################################################
 
    # Esta funcion se encarga de leer del socket de control TCP y  manejar los mensajes
    # recibidos. Para manejar los mensajes llamara a funciones auxiliares que en caso de
    # ser una llamada aceptada generara un hilo para gestionarlo.
    # Ademas, prueba periodicamente los flags para observar si el usuario solicito 
    # un cierre de la aplicacion
    def control_port_listen(self):
        user_tcp_port = Usuario.APP_USER.tcpPort

        # Preparamos el socket
        server_socket = socket(AF_INET, SOCK_STREAM)
        server_socket.bind(('', int(user_tcp_port)))
        server_socket.listen(5)
        server_socket.settimeout(self.TIMEOUT)
        
        # Bucle de lectura de puerto
        while True:

            # Abrimos el mensaje/listen con timeout para probar los flags periodicamente
            try:
                conection_socket, addr = server_socket.accept()
                msg = conection_socket.recv(self.MAX_LISTEN)
                msg = msg.decode('utf-8')
                # Actualizamos la lista de usuarios cada vez que nos llaman
                self.usersDic = Protocolo.list_users()
                if 'CALLING' in msg:
                    self.called_manager(msg)
                elif 'CALL_HOLD' in msg:
                    self.call_hold_manager(msg)
                elif 'CALL_RESUME' in msg:
                    self.call_resume_manager(msg)
                elif 'CALL_END' in msg:
                    self.call_end_manager(msg)
                elif 'CALL_ACCEPTED' in msg:
                    self.call_accepted_manager(msg)
                elif 'CALL_DENIED' in msg:
                    self.call_denied_manager(msg)
                elif 'CALL_BUSY' in msg:
                    self.call_busy_manager(msg)
                # Cualquier otro caso es descartado por malformacion
                
            except Exception as e:
                # Salimos en caso de que el  hilo maestro lo indique
                if self.end_gui.is_set():
                    return



    # Esta funciona lanza una ventana emergente que nos permite aceptar o rechazar
    #  una llamada entrante. Iniciara el popup y cuando el usuario presione
    #  en Aceptar o Rechazar se indicara en la variable self.value con un boolean.
    #  Finalmente se cierra el popup
    def called_subwindow(self):
        # Definimos la ventana
        # Modal previene que se toque la ventana padre hasta que se termine el uso de
        #  la subventana
        self.app.startSubWindow('Llamada entrante', modal=True)
        self.app.addLabel('L1', 'Llamada de '+self.calling_user)
        self.app.addButtons(['Aceptar', 'Rechazar'], self.called_buttons)
        self.app.stopSubWindow()
        self.esperar_resultado = Lock()
        self.esperar_resultado.acquire()
        # Lanzamos la subwindow
        self.app.showSubWindow('Llamada entrante')



    # Esta funcion es la que maneja los botones de la subventana anterior. 
    #  Actualizara el valor de value como se indica antes. Tambien se 
    #  encarga de cerrar la subventana
    def called_buttons(self, button):
        if button == 'Aceptar':
            self.value = True
        else:
            self.value = False

        self.esperar_resultado.release()
        # Eliminamos subventana
        self.app.destroySubWindow('Llamada entrante')


    
    # Esta funcion se ejecuta cuando tenemos una llamada entrante. Se encarga de gestionar
    # el popup para preguntarle al usuario si quiere aceptar la llamada. En caso afir-
    #  mativo pone en marcha la llamada
    def called_manager(self, msg):
        campos = msg.split(' ')
        # Caso de paquete mal formado
        if len(campos)!=3: return
        
        nick = campos[1]
        dst_udp_port = campos[2]
        # Intentamos abrir un socket de control, sino lo logramos no hacemos nada
        try:
            tcp_socket = socket(AF_INET, SOCK_STREAM)
            # Timeout para conexion con el otro usuario
            tcp_socket.settimeout(10)
            tcp_socket.connect((self.usersDic[nick]['ip'], int(self.usersDic[nick]['port'])))
        except Exception as e:
            print(e)
            return

        # Comprobamos que estamos en login, sino mandamos un paquete de ocupado
        self.state_lock.acquire()
        if self.STATE != STATE_LOGGED:
            # Nos protegemos contra casos de error al enviar un BUSY
            try:
                # Abrimos conexion con el puerto de control del usuario
                Protocolo.call_busy(Usuario.APP_USER.nick, tcp_socket)
                tcp_socket.close()
            except Exception as e:
                print(e)
            # Caso de algun fallo de ip, puerto o conexion no peta el programa
            self.state_lock.release()
            return
         
        # Creamos esta variable para comunicarnos con el subventana cuando nos llamen
        # Con value sabemos la decision del usuario
        self.value = False
        # Establecemos el usuario y llamamos a la ventana emergente 
        self.calling_user_lock.acquire()
        self.calling_user = nick
        self.called_subwindow()
        # Esperamos a que responda el usuario
        self.esperar_resultado.acquire()
        # Caso de aceptar de llamada
        if self.value == True:
            # Abrimos un socket UDP en el que recibir el video (pedimos puerto al OS)
            # Lo guardamos en una variable de clase para que pueda acceder el hilo
            self.sock_udp = socket(AF_INET, SOCK_DGRAM)
            udp_port = int(Usuario.APP_USER.udp_port)
            self.sock_udp.bind(('',udp_port))
            # Enviamos paquete de llamada aceptada
            Protocolo.call_accept(Usuario.APP_USER.nick, udp_port, 
                                  tcp_socket)
            # Inciamos el thread con el inicio de la llamada
            t = Thread(target=self.video_managing_thread, args=(dst_udp_port, ))
            t.start()
            self.STATE = STATE_CALL
            self.__change_call_buttons(self.TO_CALL)
        else:
            # Caso de rechazar eliminamos el calling user
            self.calling_user = None
            Protocolo.call_deny(Usuario.APP_USER.nick, tcp_socket)
        tcp_socket.close()
        self.calling_user_lock.release()
        self.state_lock.release()
        return
   


    # Esta funcion auxiliar nos permite comprobar si un paquete tiene UNICAMENTE DOS
    # campos y si el segundo campo (nick) corresponde con el campo del usuario con el
    # que se esta mateniendo la comuncacion
    def __campo_nick_correcto(self,msg):
        campos = msg.split(' ')
        # Caso de paquete malformado
        if len(campos) != 2: return False
        
        nick = campos[1]
        # Ahora comprobamos que el nick en el mensaje corresponde con el de nuestra 
        # llamada, sino indicamos False
        self.calling_user_lock.acquire()
        if (self.calling_user is None) or (self.calling_user != nick):
            self.calling_user_lock.release()
            return False
        self.calling_user_lock.release()
        return True



    # Esta funcion recibe un mensaje que contiene 'CALL_HOLD'. Se encarga de hacer
    # comprobaciones sobre el paquete y en caso de que se legitimo pone a la llamada
    # en estado de HOLD
    def call_hold_manager(self,msg):
        # Caso del campo nick incorrecto simplemente tiramos el mensaje
        if not self.__campo_nick_correcto(msg):
            return

        # Comprobamos que estamos en una llamada, sino simplemente tiramos el mensaje
        #  (esta comprobacion evita posibles ataques)
        self.state_lock.acquire()
        if self.STATE != STATE_CALL:
            self.state_lock.release()
            return
        
        # Ponemos la llamada en hold
        self.STATE = STATE_HOLD
        self.on_hold.set()
        self.swap_hold_resume()
        
        self.state_lock.release() 
        return



    # Esta funcion recibe un mensaje que contiene 'CALL_RESUME'. Se encarga de hacer
    # comprobaciones sobre el paquete y en caso de que se legitimo pone a la llamada
    # de nuevo (la descongela)
    def call_resume_manager(self, msg):
        # Caso del campo nick incorrecto simplemente tiramos el mensaje
        if not self.__campo_nick_correcto(msg):
            return
        
        # Comprobamos que estamos en HOLD, sino simplemente tiramos el mensaje
        #  (esta comprobacion evita posibles ataques)
        self.state_lock.acquire()
        if self.STATE != STATE_HOLD:
            self.state_lock.release()
            return
        
        # Reestablecemos la llamada
        self.STATE = STATE_CALL
        self.on_hold.clear() 
        # Reestablecemos boton de HOLD
        self.swap_hold_resume() 
        
        self.state_lock.release() 
        return 
    
    # Funcion que usan las dos funciones anteriors
    # Intercambia los botones de hold y resume en funcion
    # del estado. No se protege el acceso porque esta funcion se llama
    # desde lugares en los que se ha accedido a state de forma segura
    # (con el mutex)
    def swap_hold_resume(self):
        if self.STATE == STATE_CALL:
            self.app.hideWidgetType(gui.BUTTON, self.RESUME)
            self.app.showWidgetType(gui.BUTTON, self.HOLD)
        if self.STATE == STATE_HOLD:
            self.app.hideWidgetType(gui.BUTTON, self.HOLD)
            self.app.showWidgetType(gui.BUTTON, self.RESUME)
        return

    
    # Esta funcion recibe un mensaje que contiene 'CALL_END'. Sen encarga de hacer 
    # comprobacion y en el caso correspondiente termina la llamada
    def call_end_manager(self, msg):
        # Caso del campo nick incorrecto simplemente tiramos el mensaje
        if not self.__campo_nick_correcto(msg):
            return
        
        # Comprobamos que estamos en llamada o hold, sino simplemente tiramos el mensaje
        #  (esta comprobacion evita posibles ataques)
        self.state_lock.acquire()
        if self.STATE != STATE_CALL and self.STATE != STATE_HOLD:
            self.state_lock.release()
            return
        
        # Sino, cerramos la llamada
        self.end_call.set()
        self.__change_call_buttons(self.FROM_CALL)
        self.STATE = STATE_LOGGED
        self.state_lock.release()
        return



    # Esta funcion debe recibir la aceptacion de una llamada del usuario e inciar
    # la transmision en caso de que todo sea correcto
    def call_accepted_manager(self,msg):
        campos = msg.split(' ')
        # Caso de paquete malformado
        if len(campos) != 3: return
        nick = campos[1]
        dst_udp_port = campos[2]
        # Ahora comprobamos que el nick en el mensaje corresponde con el de nuestra 
        # llamada, sino indicamos tiramos el mensaje 
        self.calling_user_lock.acquire()
        if (self.calling_user is None) or (self.calling_user != nick):
            self.calling_user_lock.release()
            return
        self.calling_user_lock.release()
        # Comprobamos que estamos en espera de respuesta, sino simplemente 
        # tiramos el mensaje (esta comprobacion evita posibles ataques)
        self.state_lock.acquire()
        if self.STATE != STATE_WAIT_ANSWER:
            self.state_lock.release()
            return
        
        # Cambiamos estado a estado en llamada
        self.STATE = STATE_CALL 
        # Cerramos la ventana emergente 
        try:
            self.app.destroySubWindow(self.WAITING_WINDOW)
        except:
            pass
        self.__change_buttons(self.TO_CALL)
        # Iniciamos la llamada
        t = Thread(target=self.video_managing_thread, args=(dst_udp_port, ))
        t.start()
        # Cambiamos botones de la parte inferior derecha a botones de llamada
        self.__change_call_buttons(self.TO_CALL)
        self.state_lock.release()
        return


    # Esta funcion gestiona el rechazo de una llamada.
    def call_denied_manager(self,msg):
        # Caso del campo nick incorrecto simplemente tiramos el mensaje
        if not self.__campo_nick_correcto(msg):
            return

        # Comprobamos que estamos en espera, sino simplemente tiramos el mensaje
        #  (esta comprobacion evita posibles ataques)
        self.state_lock.acquire()
        if self.STATE != STATE_WAIT_ANSWER:
            self.state_lock.release()
            return
        
        # Indicamos en la gui
        self.app.getLabelWidget('Indicacion').config(text='El usuario ha rechazado la llamada.')
        # Indicamos cambio de estado en variable de estado y usuario de llamada
        # se deja el popup abierto para que el propio usuario cierre la llamada
        self.calling_user_lock.acquire()
        self.calling_user = None
        self.STATE = STATE_LOGGED
        self.calling_user_lock.release()
        self.state_lock.release() 
        return
   
   

    # Maneja la respuesta en caso de que el usuario que se quiere llamar este ocupado 
    def call_busy_manager(self,msg):
        # Comprobamos que estamos en espera, sino simplemente tiramos el mensaje
        #  (esta comprobacion evita posibles ataques)
        self.state_lock.acquire()
        if self.STATE != STATE_WAIT_ANSWER:
            self.state_lock.release()
            return
       
        # Indicamos en la gui
        self.app.getLabelWidget('Indicacion').config(text='El usuario esta ocupado.')
        # Indicamos cambio de estado en variable de estado y usuario de llamada
        # se deja el popup abierto para que el propio usuario cierre la llamada
        self.calling_user_lock.acquire()
        self.calling_user = None
        self.STATE = STATE_LOGGED
        self.calling_user_lock.release()
        self.state_lock.release() 
        return

    

    # Esta funcion se encarga de mostrar el video recibido por el usuario y enviar el
    #  video captado por la camara. Para enviar el video lo hara a traves del puerto UDP
    #  dado en los argumentos.
    # Para recibir el video lo hara a traves del socket en la variable self.sock_udp. Esta
    # variable debera haber sido inicializada al presionar el boton de la llamada o al
    # haber aceptado una llamada entrante
    def video_managing_thread(self, dst_port):
        # Llamamos al thread de recepcion
        t = Thread(target=self.video_receiving_thread)
        t.start()
        # Nos quedamos enviando video durante la llamada
        self.video_sending_thread(dst_port)
        # Fin de llamada, esperamos a que finalice el hilo
        t.join() 
        # Reestablecemos flags
        self.end_call.clear()
        self.on_hold.clear()
        return


    # Esta funcion se mantiene enviando enviando el video de la camara
    # por el puerto dado. Si la llamada esta en espera no envia nada
    # Ademas, va actualizando la variable our_frame para que la utilice
    # el evento. Esta funcion finaliza con la llamada
    def video_sending_thread(self, dst_port):
        continuar = True
        
        # Vars utiles
        nick = self.calling_user
        ip = self.usersDic[nick]['ip']
        dst_port = int(dst_port)
        client_sock = socket(AF_INET, SOCK_DGRAM)
        
        # Compresión JPG al 50% de resolución (se puede variar)
        encode_param = [cv2.IMWRITE_JPEG_QUALITY,50]
       
        sec = 1
        width = 400
        height = 300
        
        # Conutinuamos enviando hasta que se acabe la llamada
        while(continuar):
            ret, self.our_frame = self.our_video.read()
            
            # Si esta en hold no enviamos ni recibimos nada
            if not self.on_hold.is_set():
                result,encimg = cv2.imencode('.jpg',self.our_frame,encode_param)
                # Preparamos mensaje
                timestamp = time.time()
                fps = int(1000/self.poll_time)
    
                msg = str(sec)+'#'+str(timestamp)+'#'+str(width)+'x'+str(height)+'#'+str(fps)+'#'
                msg = msg.encode() + encimg.tobytes()
                
                # Enviamos datos
                client_sock.sendto(msg, (ip,dst_port))
                sec = sec + 1
            if self.end_call.isSet():
                continuar = False

        # Cerramos socket de envio
        client_sock.close()
        return



    # Esta funcion se encarga de la recepcion de video por socket
    # self.sock_udp que tiene que haber sido previamente abierto.
    # Va recibiendo los mensajes con un timeout y los escribe en
    # self.their_frame. Cuando termina la llamada, se termina
    # la funcion y se cierra el socket self.sock_udp
    def video_receiving_thread(self):
        continuar = True
        # Vars utiles
        nick = self.calling_user
        ip = self.usersDic[nick]['ip']
        # Ponemos timeout a socket de recepcion
        self.sock_udp.settimeout(0.3)
        # Compresión JPG al 50% de resolución (se puede variar)
        encode_param = [cv2.IMWRITE_JPEG_QUALITY,50]
        
        # Mientras no acabe la llamada
        while(continuar): 
            # Si esta en hold no recibimos nada
            if not self.on_hold.is_set():
                try:
                    (msg, ancmsg, msg_flags, clientAddr) = self.sock_udp.recvmsg(65536)
                    # Parseamos
                    msg = msg.split(b'#')
                    sec = int(msg[0].decode())
                    timestamp = float(msg[1].decode())
                    width = int(msg[2].decode().split('x')[0])
                    height = int(msg[2].decode().split('x')[1])
                    fps = int(msg[3].decode())
                    encimg = b'#'.join(msg[4:])
                    # Descompresión de los datos, una vez recibidos
                    # El mensaje puede ser None si se pierde el primer paquete udp
                    self.their_frame = cv2.imdecode(np.frombuffer(encimg,np.uint8), 1)
                    lon = len(self.queue)
                    if lon >= MAX_QUEUE_SIZE:
                        rand = randint(0, lon-1)
                        del(self.queue[rand])
                      
                    else:
                        heapq.heappush(self.queue, (timestamp, self.their_frame))
                
                except Exception as e:
                    pass
            
            if self.end_call.isSet():
                continuar = False
     
        # Cerramos el socket
        self.sock_udp.close()
        return
    


    # Funcion para cambiar los fps de la llamada
    def setfps(self, current_ts):
        diff = current_ts - self.last_ts
        if diff == 0:
            return
        # Calculamos polltime actual
        # polltime = 1000/fps = 1000/(1/current_ts - last_ts)
        # Adaptativo: damos alpha importancia al poll_time recien calculado
        # y (1 - alpha) importancia al poll_time anterior
        alpha = 0.02
        poll_time = 1000 * diff 
        poll_time = (alpha * poll_time) + ((1 - alpha) *  self.poll_time)
        # Aproximamos

        if poll_time < 15 and self.poll_time != 15:
            self.poll_time = 15
            self.app.setPollTime(15)
        elif poll_time < 33 and self.poll_time != 25:
            self.poll_time = 25
            self.app.setPollTime(25)
        elif self.poll_time != 33:
            self.poll_time = 33
            self.app.setPollTime(33)



