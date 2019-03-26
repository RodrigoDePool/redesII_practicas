from socket import *
import requests

# Macros utiles en esta clase
UTF='utf-8'

"""
    Esta clase se encarga de la funcionalidad del protocolo, tanto la comunicacion con
    el servidor como la comunicacion p2p.
"""
class Protocolo:

    SERVER_PORT=8000
    MAX_SERVER_RESPONSE=8192
    VERSION='V1'
    SERVER_NAME='vega.ii.uam.es'



    # Esta funcion notifica al servidor el cierre de la conexion y cierra
    # el socket dado
    #
    # :param socket: Socket por el que se notifica y que se cierra
    @staticmethod
    def quit_server(socket):
        query = 'QUIT'
        socket.send(query.encode(UTF))
        socket.close()



    # Esta funcion se encarga de registrar un usuario. Para ello establece conexion
    # TCP con el servidor y manda la query al servidor con los argumentos dados.
    #
    # :param nick: Nombre del usuario a crear/renovar
    # :param pas:  Clave del usuario a crear/renovar
    # :param port: Puerto del usuario a crear/renovar
    # :param ip:   Ip que utilizara el usuario
    # :return Devuelve False si la respuesta de la query fue negativa, en caso contrario
    #         devuelve True
    @staticmethod
    def register(nick, pas, port, ip):
        # Abrimos conexion con el servidor
        client = socket(AF_INET, SOCK_STREAM)
        client.connect((Protocolo.SERVER_NAME, Protocolo.SERVER_PORT))
        
        # Mandamos query
        query = 'REGISTER ' + nick + ' ' + ip + ' '
        query = query + str(port) + ' ' + pas + ' ' + Protocolo.VERSION

        # Enviamos y recibimos la respuesta del servidor
        res = Protocolo.__manage_query(client, query)
        
        # Notificamos al servidor el cierre de la conexion y cerramos sock
        Protocolo.quit_server(client)
        
        # Indicamos cual es el error
        if 'OK WELCOME' in res:
            return True
        else:
            return False



    # Dado un nombero de usuario se busca en el servidor informacion sobre
    # ese usuario
    #
    # :param nick: nombre del usuario que se busca
    # :return Si no existe el usuario o caso de error devuelve None
    #         Si el usuario existe devuelve una lista con la siguiente info:
    #           [nick, ip_addr, TCPport, protocols_supported]
    @staticmethod
    def server_query(nick):
        # Abrimos conexion con el servidor
        client = socket(AF_INET, SOCK_STREAM)
        client.connect((Protocolo.SERVER_NAME, Protocolo.SERVER_PORT))
        
        # Establecemos la query y la enviamos
        query = 'QUERY ' + nick 
        res = Protocolo.__manage_query(client, query)
        
        # Comprobamos si hubo error
        if 'NOK USER_UNKNOWN' in res:
            return None

        # Parseamos la respuesta recibida y terminamos
        res = res.split(' ')
        nick = res[2]
        ip = res[3]
        port = res[4]
        protocols = res[5]
        # Indicamos fin de conexion al servidor y cerramos sock
        # TODO habria que considerar varios protocolos, no?
        Protocolo.quit_server(client)
        return [nick, ip, port, protocols]

    # Devuelve una estructura con la lista de usuarios de manera que podemos acceder
    # a la ip del usuario con nick = 'pepito' como users['pepito']['ip'] y a su puerto
    # como users['pepito']['port']:D
    #
    # :return   users Un diccionario de diccionarios. 
    #           En el diccionario exterior, las claves son nicks (dic['pepito']) y
    #           y los valores son diccionarios con 2 claves: dic['ip'] = string con la ip
    #           y dic['port'] = string con el puerto
    @staticmethod
    def list_users():
        # Abrimos conexion con el servidor
        client = socket(AF_INET, SOCK_STREAM)
        client.connect((Protocolo.SERVER_NAME, Protocolo.SERVER_PORT))
        
        # Hacemos query
        query = 'LIST_USERS'
        # Esta query no la maneja manage_query por toda la historia de saber
        # si el paquete esta leido segun la cantidad de usuarios leidos
        res = Protocolo.__manage_list(client, query)
       
        users =  {}
        # pasamos lo que nos devuelven a un diccionario de diccionarios
        for user in res.split('#'):
            fields= user.split(' ')
            # nuestra manera guarra de evitar users con almohadillas de por medio es 
            # descartar aquellos users con menos de 3 campos: en ese caso, users como
            # 'paquito#perez 1.1.1.1 8080' quedarian reducidos a 'perez 1.1.1.1 8080'
            # como su nick no sera valido, entonces no podremos llamarle. pero vamos, 
            # que tampoco se lo merece si se ha puesto ese nombre. 
            # con esta solucion garantizamos poder seguir leyendo nombres a partir de
            # este usuario puñetero.
            # no tenemos solucion al caso de que el usuario ponga espacios en su nombre
            # asumimos 4 campos: name, ip, port, ts
            if len(fields) == 4:
                nick = fields[0]
                ip = fields[1]
                port = fields[2]
                
                # creamos un diccionario para cada usuario
                userDic = {}
                userDic['ip'] = ip
                userDic['port'] = port
                # Y asociamos a la key 'nick' como value ese diccionario
                users[nick] = userDic  
        
        # Indicamos fin de conexion al servidor y cerramos sock
        Protocolo.quit_server(client)
        #for nick, info in users.items():
        #    print(nick + ' ' +  info['ip'] + ' ' + info['port'])
        #    print('')
        return users

 
 
    # Dada una query(string) esta funcion la codifica y la envia al servidor
    # luego recibe la respuesta del servidor, la convierte en string y lo
    # devuelve.
    #
    # :param sock: Socket para comunicacion con el servidor
    # :param query: string con el query a enviar
    # :return El string de la respuesta del servidor
    @staticmethod
    def __manage_query(sock, query):
        # Mandamos query
        sock.send(query.encode(UTF)) 
        # Recibimos respuesta
        res = sock.recv(Protocolo.MAX_SERVER_RESPONSE)
        res = res.decode(UTF)
        return res
    
    ##############################################################################
    # NO ES UNA SOLUCION EFICIENTE, PERO AL MENOS NO NOS FASTIDIA EL PROGRAMA CADA
    # VEZ QUE ALGUIEN METE UNA ALMOHADILLA EN SU NOMBRE :D
    ##############################################################################
    # Una funcion que se encargue de recibir la respuesta de list_users
    # y devolverla ya decodificada. 
    # Devuelve tantos usuarios como LIST_USERS le ha dicho que iban a llegar, 
    # teniendo en cuenta que los usuarios paco#perez... quedan registrados como
    # un solo usuario #perez... invalido
    #
    # :param sock: Socket para comunicacion con el servidor
    # :param query: string con el query a enviar
    # :return El string de la respuesta del servidor
    @staticmethod 
    def __manage_list(sock, query):
        
        # mandamos query
        sock.send(query.encode(UTF)) 
        # recibimos respuesta
        res = sock.recv(Protocolo.MAX_SERVER_RESPONSE)
        res = res.decode(UTF) 

        # si hubo error, no podemos continuar
        if 'nok user_unknown' in res:
            return None

        # Ahora vamos a averiguar cuantos usuarios esperamos leer, e ir recibiendo querys
        # mientras no leemos el numero esperado
        # Nuestro metodo (que usa count_users)
        # falla cuando queda recortado el ultimo campo del ultimo usuario (piensa que ya
        # se han leido todos los usuarios completos) pero como el ultimo campo es ts, no
        # nos importa

        # 14 es la posicion en la que acaba la cadena 'ok users_list' y empiezan los users
        res = res[14:]
        # Pillamos el numero de usuarios devueltos por la query, justo antes del primer ' '
        space = res.find(' ')
        expectedNUsers = int(res[:space])
        # Y los users se encuentran en el resto de la cadena
        usersList = res[space+1:]
        
        receivedNUsers = Protocolo.__count_users(usersList)
        while receivedNUsers < expectedNUsers:
            # Seguimos recibiendo info
            res = sock.recv(Protocolo.MAX_SERVER_RESPONSE)
            res = res.decode(UTF) 
            usersList += res 
            # Y actualizamos cuantos usuarios tenemos ahora
            receivedNUsers = Protocolo.__count_users(usersList)
        return usersList
    
    # Esta funcion, dado un trozo de la query de list_users, devuelve 
    # cuantos usuarios reales (con 4 campos, cada usuario separado por
    # almohadillas) hay realmente en ese trozo de query
    # 
    # :param users string con los usuarios separados por #
    # :return nUsers numero real de usuarios en el trozo de query
    @staticmethod 
    def __count_users(users):
        splitted = users.split('#')
        nUsers = len(splitted)
        for user in splitted:
            # Si tenemos un usuario punietero con almohadillas  'paquito#perez ...'
            # O un usuario cuyo nombre son almohadillas '#### ip ...' (en este caso,
            # el primer trozo del split sera vacio ('')
            spl = user.split(' ') 
            l = len(spl)
            if l != 4:
            #if l != 4 or (l == 4 and (spl[0] == '' or spl[l-1] == '')):
                # Esto cuenta solo como haber leido 1 usuario, no 2.
                # Restamos 1 al nUsers q split nos dice que tenemos :D
                nUsers -= 1
        return nUsers

    # NOTA: muchas de las funciones a continuacion piden un socket. Es necesario que
    #    este socket venga dado externamente. Ya que el socket que establece la comu-
    #    nicacion es necesario tanto para enviar como para recibir los mensajes. En
    #    cualquier caso tiene que ser abierto por una funcion superior
    
    # Manda una peticion de llamada por el socket dado
    @staticmethod
    def call(nick, srcUdp, socket):
        call = 'CALLING '+ nick + ' ' + str(srcUdp)
        socket.send(call.encode(UTF))               



    # Manda por el socket dado un mensaje para rechazar una peticion de llamada 
    @staticmethod
    def call_deny(nick, socket):
        deny = 'CALL_DENIED '+nick
        socket.send(deny.encode(UTF))



    # Manda por el socket dado un mensaje para rechazar una peticion de llamada cuando
    # se esta ocupado en otra llamada
    @staticmethod
    def call_busy(nick, socket):
        busy = 'CALL_BUSY '+nick
        socket.send(busy.encode(UTF))


    # Manda por el socket dado un mensaje para pausar una llamada 
    @staticmethod
    def call_hold(nick, socket):
        hold = 'CALL_HOLD '+nick
        socket.send(hold.encode(UTF))



    # Manda por el socket dado un mensaje para reanudar una llamada 
    @staticmethod
    def call_resume(nick, socket):
        resume = 'CALL_RESUME '+nick
        socket.send(resume.encode(UTF))



    # Manda por el socket de control dado que se acepta la conexion
    @staticmethod
    def call_accept(nick, udp_port, socket):
        accept = 'CALL_ACCEPTED '+nick+' '+str(udp_port)
        socket.send(accept.encode(UTF))




    # Manda por el socket dado un mensaje para finalizar una llamada 
    @staticmethod
    def call_end(nick, socket):
        end = 'CALL_END '+nick
        socket.send(end.encode(UTF))








