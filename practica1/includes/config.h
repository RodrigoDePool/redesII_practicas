/**
 * Autores: Rodrigo De Pool y Lucia Asencio
 *
 * Libreria para manejar la configuracion desde un fichero del servidor
 * Ademas, se encarga de la demonizacion con do_deamon
 */

#ifndef CONFIG_H
#define CONFIG_H

#include "utils.h" /*Para macros OK y ERROR*/

#define CONFIG_FILE "server.conf"


/* Variable donde se almacena la configuracion del servidor
 * Puerto, numero de cliente, ruta y signatura
 */
typedef struct _Config Config;

/**
 * Esta funcion devuelve la configuracion del servidor que esta almacenada en el
 * fichero "server.conf" que DEBE estar en el mismo directorio que el ejecutable/
 * 
 * @return Puntero a config en caso de que se haya realizado todo correctamente
 *         NULL en caso de que haya habido un error. Detalles en syslog
 */
Config *server_configuration();


/**
 * Se encarga de demonizar el proceso
 */
void do_deamon();

/*FUNCIONES GET*/

/**
 * @return  -1 en caso de error
 */
long int get_max_clients(Config *conf);


/**
 * @return  -1 en caso de error
 */
long int get_listen_port(Config *conf);

/**
 * @return String con server_root o NULL en caso de error
 * NOTA: NO se debe liberar la string dada
 */
char *get_server_root(Config *conf);

/**
 * @return String con server_signature o NULL en caso de error
 * NOTA: NO se debe liberar la string dada
 */
char *get_server_signature(Config *conf);

/**
 * Libera la estructura de configuracion
 */
void free_config(Config *conf);



#endif
