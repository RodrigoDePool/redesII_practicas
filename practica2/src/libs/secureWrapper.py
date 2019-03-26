import requests
import json

"""
    Esta clase se encarga de la comunicacion HTTP con el servidor
"""
class SecureWrapper():

    token_file = 'libs/objects/token'

    # Inicializa el wrapper para la aplicacion SecureBox
    #
    # :Excepciones: Puede saltar una excepcion en la lectura del fichero del
    #              token.
    def __init__(self):
        #Url basico que se concatena en cada llamada
        self.basic_url = 'https://vega.ii.uam.es:8080/api'

        #Cargamos la cabecera del token al wrapper
        with open(SecureWrapper.token_file) as f:
            data = json.load(f)

        self.headers = {'Authorization':'Bearer ' + data['token']}

    # Devuelve nombre y ts
    # Esta funcion se encarga de registrar un usuario con los argumentos
    # correspondientes.
    #
    # En caso de error devuelve una excepcion con la string indicando el fallo.
    # Si no da error devuelve el timestamp del paquete HTTP
    # Nota la publicKey que se espera es en el formato de Cryptodome
    def registrar_usuario(self, nombre, email, publicKey):
        url = self.basic_url + '/users/register'
        args = {'nombre':nombre, 'email':email, 'publicKey':publicKey.exportKey().decode()}
        
        response = requests.post(url, json=args, headers=self.headers)
        if(response.status_code != 200):
            raise Exception('Error: No se pudo registrar el usuario') 
        data = response.json()
        return data['ts']

    # Dado un identificador de usuario nos devuelve su clave publica.
    #
    # :Excepciones: En caso de error devuelve una excepcion indicando el error
    # :param userID identificador del usuario del que se quiere la clave publica
    # :return clave publica del usuario como la devuelve el servidor
    # NOTA: es importante considerar que una clave subida al servidor puede no estar
    #       bien formateada. Hay que ser cuidadosos con las funciones que manejen claves
    def obtener_clave_publica(self, userID):
        url = self.basic_url + '/users/getPublicKey'
        args = {'userID':userID}

        response = requests.post(url, json=args, headers=self.headers)
        if(response.status_code != 200):
            raise Exception('Usuario con id '+userID+' no encontrado')

        data = response.json()
        return data['publicKey']



    # Respuesta con: userID, nombre, email, publicKey, ts
    # Dada una string busca todos los usuarios que contengan esa string en el nombre
    # de usuario o en su email.
    #
    # :param data_search string de busqueda
    # :return Devuelve una lista de diccionarios. Cada diccionario corresponde a un
    #         usuario: Los diccionarios contienen nombre, userID, email, ts y publicKey
    def busqueda_usuarios(self, data_search):
        url = self.basic_url + '/users/search'
        args = {'data_search':data_search}

        response = requests.post(url, json=args, headers=self.headers)
        if(response.status_code != 200):
            raise Exception('La busqueda con '+data_search+' no se ha podido realizar')

        data = response.json()
        return data

    # Esta funcion borrar el usuario con ID userID
    # 
    # Excepciones: En caso de error devuelve una excepcion indicandolo.
    # :param userID  identificador del usuario que se quiere borrar
    def borrar_usuario(self, userID):
        url = self.basic_url + '/users/delete'
        args = {'userID':userID}

        response = requests.post(url, json=args, headers=self.headers)
        if(response.status_code != 200):
            raise Exception('El usuario con ID '+userID+' no existe, no puede ser eliminado')
        return

    #Se puede hacer esta ejecutando el comando curl (VER ENUNCIADO)
    # Esta funcion se encarga de subir ficheros al servidor.
    #
    # :Excepciones: Si hay un error al abrir el fichero o si hay un error en el envio.
    # :param encrypted_file path hasta el fichero que se quiere enviar
    # :return ID del fichero que fue subido al servidor
    def subir_fichero(self, encrypted_file):
        url = self.basic_url + '/files/upload'
        
        with open(encrypted_file,'rb') as f:
            response = requests.post(url, headers=self.headers, files={'ufile':f})
        
        if(response.status_code != 200):
            raise Exception('Error, no se subio el fichero con exito.')
        data = response.json()
        return data['file_id']

    # Respuesta directa con el fichero y su nombre
    # Esta funcion se encarga de bajar un fichero del servidor.
    #
    # :Excepciones: Devuelve una excepcion si el id de fichero es incorrecto 
    # :param file_id ID del fichero que se quiere bajar
    # :return devuelve la lista [filename, mensaje]
    #         donde filename es el nombre del fichero y
    #         mensaje es el contenido del fichero en binario
    def bajar_fichero(self, file_id):
        url = self.basic_url + '/files/download'
        args = {'file_id':file_id}   
        response = requests.post(url, json=args, headers=self.headers)
        if (response.status_code != 200):
            raise Exception('Error el id '+file_id+' no es correcto.')
        #Obtenemos el nombre
        disposition = response.headers['Content-Disposition']
        index = disposition.index('"')
        filename = disposition[index+1:-1]
        return [filename, response.content]

    # Esta funcion lista los ficheros que estan disponibles en el servidor
    #
    # :return Devuelve un diccionario con files_list (lista de IDs de ficheros disponibles)
    #         y num_files (numero de ficheros disponibles)
    def listar_ficheros(self):
        url = self.basic_url + '/files/list'
        response = requests.post(url, headers=self.headers)
        data = response.json()
        return data

    # Esta funcion borra un fichero del servidor.
    #
    # Excepciones: En caso de error se indica con una excepcion
    # :param file_id identificador del fichero que se borra
    def borrar_fichero(self, file_id):
        url = self.basic_url + '/files/delete'
        args = {'file_id':file_id}
        response = requests.post(url, json=args, headers=self.headers)
        if(response.status_code != 200):
            raise Exception('Error el fichero con id '+file_id+' no existe, no se puede borrar')
        return























