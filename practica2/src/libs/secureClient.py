from libs.secureWrapper import SecureWrapper
from libs.cifrador import Cifrador
from Crypto.PublicKey import RSA
import json
import os
from Crypto.Cipher import PKCS1_OAEP, AES
unpad = lambda s: s[:-ord(s[len(s) - 1:])]

class SecureClient():
   
    #Inicializamos strings
    with open('libs/objects/help_string') as f:
        help_string = f.read()

    # Inicializa un cliente de SecureBox.
    #
    # :Excepciones: Puede dar en caso de que el fichero del token este danado o no este
    def __init__(self):
        #Objeto que nos abstrae del api
        self.wrapper = SecureWrapper()
        #Creamos un cifrador si es que hay algun usuario inicializado
        try:
            self.cifrador = Cifrador()
            self.has_user = True
        except:
            self.has_user = False
        #Creamos diccionario de comandos asociados a funciones
        self.commands={}
        self.commands['create_id']=self.__register
        self.commands['search_id']=self.__search
        self.commands['delete_id']=self.__delete_user
        self.commands['upload']=self.__upload
        self.commands['list_files']=self.__list
        self.commands['download']=self.__download
        self.commands['delete_file']=self.__delete_file
        self.commands['encrypt']=self.__encrypt
        self.commands['sign']=self.__sign
        self.commands['enc_sign']=self.__enc_sign


    # Esta funcion se encarga de toda la ejecucion del cliente. Imprimira por pantalla
    # tanto en caso de error como en caso de exito. No devuelve excepciones
    #
    # :param args lista de argumentos y flags
    def ejecutar_comando(self, args):
        dic, state = self.__flags_parser(args)
        #Caso de error en el parseo
        if(state == False):
            #imprimimos string de ayuda para comandos
            print(SecureClient.help_string)
            return
        
        #Caso en el que el comando a ejecutar no es create y no hay usuario creado
        if(not self.has_user and dic['comando'] != 'create_id'):
            print('No se puede ejecutar', dic['comando'], 'sin haber creado un usuario')
            print('Puede crear una usuario con: --create_id <nombre> <email>')
        else:
            #Ejecutamos el comando parseado en nuestro diccionario de comandos
            self.commands[dic['comando']](dic)
        return


    ##################
    # METODOS PRIVADOS
    ##################

    ##
    # FUNCIONES DE PARSEO
    ##

    # Esta funcion comprueba si los argumentos corresponden con un comando de crear id.
    # 
    # :param args argumentos de entrada del programa
    # :return [state, dic]: state False indica que el comando esta mal formado (dic None)
    #         state True indica que es del tipo crear id y dic tiene el formato
    #         { 'comando': 'create_id', 'nombre': ... , 'email':...}
    def __flag_create_id(self, args):
        l = len(args)
        command = '--create_id'

        if(l != 4 or args.index(command) != 1):
            return [None,False]

        dic = {'comando':command[2:], 'nombre':args[2], 'email':args[3]}
        return [dic,True]

    # Esta funcion comprueba si los argumentos corresponden con un comando de search id.
    # 
    # :param args argumentos de entrada del programa
    # :return [state, dic]: state False indica que el comando esta mal formado (dic None)
    #         state True indica que es del tipo search id y dic tiene el formato
    #         { 'comando': 'search_id', 'cadena': ... }
    def __flag_search_id(self, args):
        l = len(args)
        command = '--search_id'

        if(l != 3 or args.index(command) != 1):
            return [None,False]

        dic = {'comando':command[2:], 'cadena':args[2]}
        return [dic,True]


    # Esta funcion comprueba si los argumentos corresponden con un comando de delete id.
    # 
    # :param args argumentos de entrada del programa
    # :return [state, dic]: state False indica que el comando esta mal formado (dic None)
    #         state True indica que es del tipo delete id y dic tiene el formato
    #         { 'comando': 'delete_id', 'id': ... }
    def __flag_delete_id(self, args, command='--delete_id'):
        l = len(args)

        if(l != 3 or args.index(command) != 1):
            return [None,False]

        dic = {'comando':command[2:], 'id':args[2]}
        return [dic,True]

    # Esta funcion comprueba si los argumentos corresponden con un comando de upload.
    # 
    # :param args argumentos de entrada del programa
    # :return [state, dic]: state False indica que el comando esta mal formado (dic None)
    #         state True indica que es del tipo upload y dic tiene el formato
    #         { 'comando': 'upload', 'file': ..., 'dst_id': .... }
    def __flag_upload(self, args, command='--upload'):
        l = len(args)
        dst = '--dest_id'

        if(l != 5 and l != 3):
            #Tiene que tener 5 o 3 argumentos
            return [None,False]
        elif(l == 5 and dst not in args):
            #Si tiene 5 tiene que tener dst
            return [None,False]

        command_ind = args.index(command)
        if(l == 5):
            dst_ind = args.index(dst)
            id_destino = args[dst_ind+1]
            
            #Para el caso de que haya mas de un flag
            #Comprobamos que los siguientes a flags son argumentos y no otros flags o nada
            if(command_ind == l-1 or dst_ind == l-1 or command_ind+1 == dst_ind
                   or dst_ind+1 == command_ind):
                return [None, False]

        else:
            id_destino = None

       
        dic = {'comando':command[2:], 'file':args[command_ind+1], 'dst_id':id_destino}
        return [dic,True]


    # Esta funcion comprueba si los argumentos corresponden con un comando list.
    # 
    # :param args argumentos de entrada del programa
    # :return [state, dic]: state False indica que el comando esta mal formado (dic None)
    #         state True indica que es del tipo list y dic tiene el formato
    #         { 'comando': 'list_files' }
    def __flag_list(self, args):
        l = len(args)
        command = '--list_files'

        if(l != 2):
            return [None,False]

        dic = {'comando':command[2:]}
        return [dic,True]


    # Esta funcion comprueba si los argumentos corresponden con un comando de download.
    # 
    # :param args argumentos de entrada del programa
    # :return [state, dic]: state False indica que el comando esta mal formado (dic None)
    #         state True indica que es del tipo download y dic tiene el formato
    #         { 'comando': 'download', 'file_id': ..., 'src_id': .... }
    def __flag_download(self, args):
        l = len(args)
        command = '--download'
        src = '--source_id'

        if(l != 5 and l != 3):
            #Tiene que tener 5 o 3 argumentos
            return [None,False]
        elif(l == 5 and src not in args):
            return [None,False]
        
        command_ind = args.index(command)
        if(l == 5):
            src_ind = args.index(src)
            id_fuente = args[src_ind+1]

            #Para el caso de mas de un flag
            #Comprobamos que los siguientes a flags son argumentos y no otros flags o nada
            if(command_ind == l-1 or src_ind == l-1 or command_ind+1 == src_ind
                    or src_ind+1 == command_ind):
                return [None, False]
        else:
            id_fuente = None

        dic = {'comando':command[2:], 'file_id':args[command_ind+1], 'src_id':id_fuente}
        return [dic,True]

    # Esta funcion comprueba si los argumentos corresponden con un comando de delete file.
    # 
    # :param args argumentos de entrada del programa
    # :return [state, dic]: state False indica que el comando esta mal formado (dic None)
    #         state True indica que es del tipo delete file y dic tiene el formato
    #         { 'comando': 'delete_file', 'id': ... }
    def __flag_delete_file(self, args):
        #Parseo igual al de delete_id con otro comando
        return self.__flag_delete_id(args,'--delete_file')

    # Esta funcion comprueba si los argumentos corresponden con un comando de encrypt.
    # 
    # :param args argumentos de entrada del programa
    # :return [state, dic]: state False indica que el comando esta mal formado (dic None)
    #         state True indica que es del tipo encrypt y dic tiene el formato
    #         { 'comando': 'encrypt', 'file': ..., 'dst_id': .... }
    def __flag_encrypt(self, args):
        #El parseo es identico al de upload pero cambiando el comando
        return  self.__flag_upload(args,'--encrypt')

 
    # Esta funcion comprueba si los argumentos corresponden con un comando de sign.
    # 
    # :param args argumentos de entrada del programa
    # :return [state, dic]: state False indica que el comando esta mal formado (dic None)
    #         state True indica que es del tipo sign file y dic tiene el formato
    #         { 'comando': 'sign', 'id': ... }
    def __flag_sign(self, args):
        #Parseo igual al de delete_id con otro comando
        return self.__flag_delete_id(args,'--sign')


    # Esta funcion comprueba si los argumentos corresponden con un comando de encrypt sign
    # 
    # :param args argumentos de entrada del programa
    # :return [state, dic]: state False indica que el comando esta mal formado (dic None)
    #         state True indica que es del tipo encrypt sign y dic tiene el formato
    #         { 'comando': 'enc_sign', 'file': ..., 'dst_id': .... }
    def __flag_encrypt_sign(self, args):
        #El parseo es identico al de upload pero cambiando el comando
        return  self.__flag_upload(args,'--enc_sign')
   

    # Esta funcion se encarga del parseo de los argumentos de entrada del cliente.
    # 
    # :param args lista de argumentos con args[0] nombre del programa
    # :return [dic,bool]  bool es False si los argumentos son incorrectos (dic sera None)
    #         Si bool es True el parseo fue correcto y dic sera un diccionario con los
    #         argumentos de entrada. {'comando': comando (create_id,...), ...}
    #         la estructura del diccionario sera especificada en cada funcion __flag_*
    def __flags_parser(self, args):
        #Probamos si es un comando de creacion
        aux_list, state = self.__flag_create_id(args)
        if('--create_id' in args):
            return self.__flag_create_id(args)
        elif('--search_id' in args):
            return self.__flag_search_id(args)
        elif('--delete_id' in args):
            return self.__flag_delete_id(args)
        elif('--upload' in args):
            return self.__flag_upload(args)
        elif('--list_files' in args):
            return self.__flag_list(args)
        elif('--download' in args):
            return self.__flag_download(args)
        elif('--delete_file' in args):
            return self.__flag_delete_file(args)
        elif('--encrypt' in args):
            return self.__flag_encrypt(args)
        elif('--sign' in args):
            return self.__flag_sign(args)
        elif('--enc_sign' in args):
            return self.__flag_encrypt_sign(args)
        else:
            return [None,False]
        
        
    ##
    # FUNCIONES DE CLIENTE
    ##

    # Esta funcion crea un usuario nuevo. Informa en caso de error
    #
    # :param Recibe un diccionario con la estructura indicada en __flag_create_id
    def __register(self, dic): 
        try:
            #Creamos nuevas claves
            try:
                print('Generando claves RSA de 2048 bits...', sep='')
                Cifrador.generador_claves_rsa()
                self.cifrador = Cifrador()
            except Excepcion as e:
                print('ERROR\nError en la generacion de claves RSA para el nuevo usuario. Excepcion: ',e)
                return
            print('OK')
            self.wrapper.registrar_usuario(dic['nombre'],dic['email'],
                                           self.cifrador.key.publickey())
            self.has_user = True
            # dado un email, nos quedamos con el usuario mas reciente (con mayor
            # time stamp)
            busqueda = self.wrapper.busqueda_usuarios(dic['email'])
            ts = 0
            for resultado in busqueda:
                if resultado['email'] == dic['email'] and float(resultado['ts']) > ts:
                    ts = float(resultado['ts'])
                    id = resultado['userID']
            print('Identidad con ID#',id, ' creada correctamente', sep='')
        except Exception as e:
            print('ERROR\n', e)
        return

    # Esta funcion se encarga del comando search. INforma en caso de error
    def __search(self,dic):
        try:
            print('Buscando usuario ' + dic['cadena'] + ' en el servidor...', sep = '')
            data = self.wrapper.busqueda_usuarios(dic['cadena'])
            n_resultados = len(data)
            print('OK.\n', n_resultados, ' usuarios encontrados:')
            for user, i in zip(data, range(n_resultados)):
                print('[', i,  '] ', user['nombre'], ', ', user['email'], sep='', end='')
                print(', ID: ', user['userID'])
            
            if(not data):
                print('No hay usuarios que contengan en mail o nombre la cadena ', dic['cadena'])
        except Exception as e:
            print(e)
        return

    # Esta funcion se encarga del comando de borrado de un usuario
    def __delete_user(self,dic):
        try:
            print('Requesting removal of identity #',dic['id'], '...', end='')
            self.wrapper.borrar_usuario(dic['id'])
            print('OK\nIdentity with ID#', dic['id'], 'successfully deleted')
            os.remove('libs/objects/key.pem')
        except Exception as e:
            print(e)
        return

    #Esta funcion se encarga del cifrado y la subida del fichero
    def __upload(self,dic):
        print('Solicitado envio de fichero a SecureBox')
        enc_file = dic['file'] + '.upload'
        
        #Ciframos el fichero y lo firmamos
        if(not self.__enc_sign(dic,verbose=False, upload=True)):
            #Caso de error en cifrado
            return

        #Enviamos el fichero cifrado al servidor
        try:
            print('-> Subiendo fichero a servidor...', end='')
            file_id = self.wrapper.subir_fichero(enc_file)
            print('OK\nSubida realizada correctamente, ID del fichero: ', file_id)
        except Exception as e:
            print(e)
        finally:
            os.remove(enc_file)

        return
    
    #Esta funcion se encarga del comando de listar ficheros
    def __list(self,dic):
        print('Obteniendo lista de ficheros...', end='')
        data = self.wrapper.listar_ficheros()
        print('OK\n', data['num_files'], 'ficheros obtenidos')
        for files, i in zip(data['files_list'], range(data['num_files'])):
            print('[', i, '] Nombre de fichero: ', files['fileName'],', identificador de fichero: ', files['fileID'], sep='')
        
        if(not data['files_list']):
            print('No hay ficheros subidos.')
        return
    
    def __download(self,dic):

        #Bajamos el fichero
        try:
            print('Descargando fichero de SecureBox...', end='')
            file_path, enc_file = self.wrapper.bajar_fichero(dic['file_id'])
            print('OK')
            print('->', len(enc_file), 'bytes descargados correctamente')
        except Exception as e:
            print(e)
            return

        file_path = 'files/' +file_path

        #Bajamos la clave publica del usuario
        try:
            if dic['src_id'] == None:
                print('-> Recuperando clave pública propia...', end='')
                public = self.cifrador.key.publickey()
            else:    
                print('-> Recuperando clave pública de ID', dic['src_id'], '...', end='')
                public = RSA.importKey(self.wrapper.obtener_clave_publica(dic['src_id']))
            print('OK')
            
        except Exception as e:
            print(e)
            return

        #Desciframos el fichero
        try:
            print('-> Descifrando fichero y verificando firma...', end='')
            self.cifrador.descifrar(enc_file, file_path, public)
            print('OK\nFichero', file_path,'descargado y verificado correctamente')
        except Exception as e:
            print(e)
        return
   
    #Esta funcion se encarga del comando de borrado de ficheros
    def __delete_file(self,dic):
        try:
            self.wrapper.borrar_fichero(dic['id'])
            print('Requesting removal of file', dic['id'],'...', end='')
            print('OK\nIdentity with ID#', dic['id'], 'sucessfully deleted')
        except Exception as e:
            print(e)
        return
    
    # Se encarga de cifrar y firmar un fichero utilizando la clave publica 
    # de un usuario con id dado.
    # Va informando del proceso, tambien informa en caso de error.
    # El fichero cifrado esta en el mismo path dado con la terminacion '.enc_signed' 
    # por defecto, dado upload=True entonces la terminacion es '.upload'
    #
    # Por defecto, informa del path en el que el fichero ha sido cifrado, se puede
    # desactivar colocando verbose a False
    def __enc_sign(self,dic, verbose=True, upload=False):
        src_file = dic['file']
        if(upload):
            enc_file = dic['file'] + '.upload'
        else:
            enc_file = dic['file'] + '.enc_signed'
        
        #Obtenemos clave publica
        try:
            if dic['dst_id'] == None:
                print('-> Recuperando clave pública propia...', end='')
                public_key = self.cifrador.key.publickey()
            else:    
                print('-> Recuperando clave pública de ID', dic['dst_id'], '...', end='')
                public_key = RSA.importKey(self.wrapper.obtener_clave_publica(dic['dst_id']))
            print('OK')
        except Exception as e:
            print('ERROR\n', e)
            return False
        
        #Ciframos el fichero
        try:
            print('-> Firmando y cifrando fichero...', end = '')
            self.cifrador.prepara_fichero(src_file, enc_file, public_key)
            print('OK')
        except Exception as e:
            print('ERROR\n', e)
            return False

        if(verbose):
            print('El fichero cifrado y firmado tiene path ',enc_file)
        return True

    # Esta funcion se encarga de firmar un fichero.
    # Devuelve el fichero firmado en el mismo path con terminacion '.signed'
    #
    # Si verbose es True indica donde esta el fichero firmado
    def __sign(self,dic, verbose=True):
        signed_file = dic['id'] + '.signed'
        
        #Abrimos y realizamos firma
        try:
            f = open(dic['id'], 'rb')
            mensaje = f.read()
            print('-> Firmando fichero...', end = '')
            firma = self.cifrador.firmar(mensaje)
            print('OK')
        except Exception as e:
            print(e)
            return
        finally:
            f.close()

        #Abrimos fichero para guardar la firma
        try:
            f = open(signed_file, 'wb')
            print('-> Guardando firma...', end = '')
            f.write(firma + mensaje)
            print('OK')
        except Exception as e:
            print(e)
            return
        finally:
            f.close()
        
        if(verbose):
            print('Firma escrita con exito en ',signed_file)
        
        return
    
    # Cifra el fichero dic['file'] con la clave dic['dst_id'], que por defecto sera
    # la clave del propio usuario
    def __encrypt(self,dic):
        enc_file = dic['file'] + '.enc'
        
        #Obtenemos clave publica
        try:
            if dic['dst_id'] == None:
                print('-> Recuperando clave pública propia...', end='')
                public_key = self.cifrador.key.publickey()
            else:    
                print('-> Recuperando clave pública de ID', dic['dst_id'], '...', end='')
                public_key = RSA.importKey(self.wrapper.obtener_clave_publica(dic['dst_id']))
            print('OK')
            
        except Exception as e:
            print(e)
            return
        
        #Ciframos el fichero
        try:
            print('-> Cifrando fichero...', end = '')
            self.cifrador.prepara_fichero(dic['file'], enc_file, public_key, sign=False)
            print('OK')
        except Exception as e:
            print(e)
            return

        print('-> El fichero cifrado en el path ', enc_file)
        return         

