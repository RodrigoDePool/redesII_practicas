/**
 * Autores: Rodrigo De Pool y Lucia Asencio
 * 
 * Libreria para el procesamiento de peticiones http
 */


#ifndef HTTP_SERVICE_H
#define HTTP_SERVICE_H

#include "config.h"

/**
 * Estructura que guarda todos los campos
 * necesarios para elaborar la response.
 */                          
typedef struct _Response Response;
 
 /**
  * Funcion encargada de procesar peticion http, realizando comprobaciones
  * necesarias
  * @param int cl_sock: fd del socket del cliente
  * @param conf: Configuracion del servidor
  *
  * @return  OK si la peticion se proceso correctamente
  *          ERROR si hubo un error en el proceso de la peticion
  *          CLOSED_CONNECTION si el cliente cerro la conexion
  *          TIMEOUT_ERR si el cliente no respondio en TIMEOUT segundos
  */
int procesar_peticion(int cl_sock, Config *conf);



#endif

