/**
 * Autores: Rodrigo De Pool y Lucia Asencio
 * Libreria para funcionalidad del servidor
 */
#ifndef  SERVER_H
#define SERVER_H

#include "utils.h" /*Defines utiles*/
#include "config.h"

/**
 *  Se encarga de abrir un socket en el servidor y configurarlo con los argumentos
 *
 *  @param int port_no: numero de puerto
 *  @param int max_connections: tamaño de la cola de peticiones al servidor
 *  @param int *sock: puntero identificador al socket que se va a abrir
 *
 *  @return OK todo bien, ERROR error
 *  NOTA: recordar al final de la ejecucion del servidor cerrar el socket con 
 *        close(*sock);
 */
int server_ini(int port_no, int max_connections, int* sock);

/**
 * Aceptamos un cliente - ejecuta servicio
 * Con un semaforo esta funcion tambien controla el numero maximo de conexiones
 * simultaneas. Se permitira max_conexiones en paralelo y max_conexiones encoladas.
 * Se encarga de cuidar la funcion accept() con un semaforo y despertar al padre
 * para indicarle que el tamano del pool de procesos libres ha disminuido en 1
 *
 * @param int serv_sock: descriptor del socket del servidor
 * @param mutex: Semaforo para proteger a accept
 * @param despertador: Semaforo que le indica al proceso padre
 *                     que el pool de procesos libres se ha disminuido
 *                     en uno
 * @param conexiones: Semaforo que controla el maximo numero de conexiones
 *                    simultaneas
 * @param conf: Configuracion del servidor necesaria en el servicio
 *
 * @return OK Si la conexion la cierra el cliente
 *         ERROR conexion cerrada inesperadamente
 *         TIMEOUT_ERR conexion cerrada por timeout
 */
int server_accept(int sock,int mutex, int despertador, int conexiones, Config *conf);


/**
 * Funcion que se encarga de ejecutar el servicio del servidor a un cliente.
 * Esta funcion llamara a la correspondiente funcion de procesamiento de 
 * peticiones http
 *
 * @param sock: Descriptor a traves del cual se establece la comunicacion
 * @param conf: Configuracion del servidor utilizada en procesar http
 *
 * @return OK Si la conexion la cierra el cliente
 *         ERROR conexion cerrada inesperadamente
 *         TIMEOUT_ERR conexion cerrada por timeout
 */

int servicio(int sock, Config *conf);

/**
 * Funcion que envia un paquete a traves de un socket con la informacion dada
 * Util para el envio de paqutes desde otras librerias
 *
 * @param socket_id: Socket por el que se va enviar el paquete
 * @param cadena: Informacion que se va a enviar en el paquete
 * @param len: Tamano de la cadena a enviar
 *
 * @return OK o ERROR
 */
int enviar_paquete(int socket_id, char *cadena, int len);

/**
 * Esta funcion se encarga de enviar un fichero por un socket
 * 
 * @param socket_id: Socket por el que se quiere enviar el fichero
 * @param path: Ruta hasta el fichero
 * 
 * @return OK o ERROR.
 */
int enviar_fichero(int socket_id, char *path);


/**
 * Funcion que se encarga de la ejecucion del servidor. Esta funcion 
 * inicializa un pool de procesos que iran atendiendo las peticiones
 * de conexion de los clientes. El pool mantendra en todo momento una
 * cantidad constante de procesos libres para atender las conexiones
 * (fijada por POOL_SIZE). Una vez esta funcion se ejecute el programa
 * se quedara bloqueado en ella.
 *
 * Ademas, esta funcion creara un handler para que sea seguro cerrar
 * el programa con SIGINT.
 *
 * @param serv_sock: Socket por el cual se iran atendiendo clientes
 * @param conf: Puntero a la configuracion del servidor
 *
 * @return  ERROR en caso de que haya un error de inicializacion
 */
int server_execute_pool(int serv_sock, Config *conf);


#endif
