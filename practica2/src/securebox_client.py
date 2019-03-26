#!/usr/bin/python3
import sys
try:
    from libs.secureClient import SecureClient
except Exception as e:
    print('Error en la inicializacion: Fallo al carga fichero help_string')
    print(e)
    exit()

def main():
    #Intentamos crear un cliente
    try:
        cliente = SecureClient()
    except Exception as e:
        print('ERROR no se ha podido extraer el token del fichero.')
        return
    
    cliente.ejecutar_comando(sys.argv)


if __name__ == "__main__":
    main()
