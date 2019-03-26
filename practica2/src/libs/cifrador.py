from Crypto.Hash import SHA256
from Crypto.Util.Padding import pad, unpad
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.PublicKey import RSA
from Crypto.Signature import pss
from Crypto import Random


class Cifrador():

    BLOCK_SIZE = 16
    key_file = 'libs/objects/key.pem'

    # Funcion que genera clave RSA. Esta funcion genera una clave y la guarda
    # en el fichero Cifrador.key_file, borrando cualquier contenido previo 
    # 
    # :Excepciones: Posible excepcion en escritura de fichero
    @staticmethod
    def generador_claves_rsa():
        #Genera clave rsa con 2048 bits
        key = RSA.generate(2048)

        #Guardamos la key en objects/key.pem en formate PEM (por defecto)
        with open(Cifrador.key_file,'wb') as f:
            f.write(key.exportKey())
        return


    # Genera un nuevo cifrador con la clave en key_file.
    #
    # :Excepciones: Si el fichero de claves no esta inicializado FileNotFoundError
    def __init__(self):
        #Recuperamos la clave (flag rb porque el formato es binario)
        with open(Cifrador.key_file, 'rb') as f:
            self.key = RSA.importKey(f.read())


    # Este metodo se encarga de firmar y cifrar un fichero con esquema hibrido
    # de RSA-AES.
    # 
    # :param src_file Es el fichero que se quiere preparar
    # :param dst_file Esl fichero en el que se escribirar el src_file cifrado, firmado
    # :param dst_key (RsaKey object) Es la clave RSA publica con la que se cifrara. 
    # :param sign por defecto firma el fichero, si se pone a False entonces no se firma
    def prepara_fichero(self, src_file, dst_file, dst_key, sign=True):
        with open(src_file, 'rb') as f:
            mensaje = f.read()
        key = Random.get_random_bytes(32)
        # Como no especificamos IV, se genera unno aleatorio
        aes = AES.new(key, AES.MODE_CBC)
        # Preparamos clave sim cifrada + iv
        rsa = PKCS1_OAEP.new(dst_key)
        simetrica_cifrada = rsa.encrypt(key)
        sobre = simetrica_cifrada + aes.iv
        # ciframos con aes la firma y el mensaje
        if(sign):
            firma = self.firmar(mensaje)
            padded = pad(firma + mensaje, Cifrador.BLOCK_SIZE)
        else:
            padded = pad(mensaje, Cifrador.BLOCK_SIZE)
        contenido = aes.encrypt(padded)
        # Unimos 
        cadena = sobre + contenido
        with open(dst_file, 'wb') as f:
            f.write(cadena)
        return
    
    # Esta funcion descifra un mensaje cifrado con  esquema hibrido RSA-AES
    # 
    # :param cifrado string con el mensaje cifrado en binario 
    # :param dst_file fichero donde esrcibir el mensaje descifrado
    # :param src_key clave publica del autor del mensaje, para poder descifrar
    # la clave simetrica

    def descifrar(self, cifrado, dst_file, src_key):
        
        # Desciframos clave simetrica
        clave_sim = cifrado[:256]
        rsa = PKCS1_OAEP.new(self.key)
        clave_sim = rsa.decrypt(clave_sim)
        # Desciframos mensaje conociendo clave simetrica e iv
        iv = cifrado[256:272] #16 bytes de vector de inicializacion
        aes = AES.new(clave_sim, AES.MODE_CBC, iv)
        descifrado = aes.decrypt(cifrado[272:])
        # Autenticamos
        #Eliminamos el padding
        descifrado = unpad(descifrado, Cifrador.BLOCK_SIZE)
        #Sacamos los 256 bytes de firma
        firma = descifrado[:256]
        mensaje = descifrado[256:]
        
        if not self.autenticar_firma(mensaje, firma, src_key):
            raise Exception('ERROR\nFirma no autentica el mensaje')
        
        # Escribimos en el destino
        with open(dst_file, 'wb') as f:
            f.write(mensaje)
        return         

    # Funcion que se encarga de firmar un mensaje con la clave privada del cifrador
    # para ello utilizamos el hash sha 256
    #
    # :param mensaje con el bytes a firmar
    # :return Devuelve la firma del mensaje
    def firmar(self, mensaje):
        #Creamos el hash
        hash_msj = SHA256.new(data=mensaje)
        #Ciframos el hash con nuestra clave privada
        return pss.new(self.key).sign(hash_msj)


    # Funcion que autentica una firma de un mensaje.
    #
    # :param mensaje Mensaje que fue firmado (en formato binario!!)
    # :param firma Firma en binario dada
    # :param publickey Clave publica del usuario que lo firmo
    # :return True si la firma es correcta o False
    def autenticar_firma(self, mensaje, firma, publickey):
        #Hacemos hash del mensaje
        hash_msj = SHA256.new(data=mensaje)
        
        #Verificamos la firma con el hash y la clave publica
        try:
            pss.new(publickey).verify(hash_msj,firma)
            return True
        except:
            return False












