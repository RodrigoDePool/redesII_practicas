
/**
 * Autores: Rodrigo De Pool y Lucia Asencio
 *
 * Implementacion de server.h
 */

#include "../includes/server.h"
#include "../includes/semaforos.h"
#include "../includes/http_service.h"
#include <stdio.h>
#include <errno.h>
#include <string.h> /*For strerror*/
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/time.h> /*Para configurar el timeout*/
#include <stdlib.h>
#include <signal.h>
#include <syslog.h>
#include <string.h>

/**
 * Comentarios detallados sobre las funciones en server.h
 */


/**
 * Implementacion de server_ini
 */
int server_ini(int port_no, int max_connections, int* sock){
    struct sockaddr_in dir;
    struct timeval tv;

    /*Probamos argumentos*/
    if(port_no < 1 || port_no > 65535|| max_connections < 0 || sock == NULL){
        syslog (LOG_ERR, "Error en parametros entrada a server ini\n");
        return ERROR;
    }

    /*Abrimos socket*/
    *sock = socket(AF_INET, SOCK_STREAM, 0);
    if(*sock < 0){
        syslog (LOG_ERR, "Error en la apertura socket para servidor: %s\n ", strerror(errno));
        return ERROR;
    }

    /*Configuracion del socket*/
    dir.sin_family = AF_INET;                     /*Familia TCP/IP*/
    dir.sin_port = htons(port_no);                /*Numero de puerto en orden de red*/
    dir.sin_addr.s_addr = htonl(INADDR_ANY);      /*Acepta cualquier ip*/
    bzero(&(dir.sin_zero), 8);
    
    /*Configuramos el timeout del socket*/
    tv.tv_sec = TIMEOUT;
    tv.tv_usec = 0;
    if(setsockopt(*sock, SOL_SOCKET, SO_RCVTIMEO, (const char *)&tv, sizeof(tv)) < 0){
        syslog (LOG_ERR, "Error en setsockopt: %s\n", strerror(errno));
        close(*sock);
        return ERROR;
    }


    /*Establecemos configuracion*/
    if(bind(*sock, (struct sockaddr *)&dir, sizeof(dir)) < 0){
        syslog (LOG_ERR, "Error en el bind entre serv_sock y serv_dir. Error:%s\n", strerror(errno));
        close(*sock);
        return ERROR;
    }
    
    /*Dispuestos a escuchar peticiones*/
    if(listen(*sock, max_connections) < 0){
        syslog (LOG_ERR, "Error en la funcion listen. Error: %s\n",strerror(errno));
        close(*sock);
        return ERROR;
    }
    return OK;
}

/**
 * Implementacion de server accept
 */
int server_accept(int serv_sock, int mutex, int despertador, int conexiones, Config *conf){
    int cl_sock, aux;
    struct sockaddr cl_dir;
    socklen_t len; 
    len = sizeof(cl_dir);
    
    /*Limitamos el numero de conexiones simultáneas*/
    Down_Semaforo(conexiones, 0, 0);
    /*Protejemos funcion accept con semaforo*/
    Down_Semaforo(mutex, 0, 0);
    
    cl_sock = accept(serv_sock, &cl_dir, &len);
    /*En caso de timeout en accept, repetimos accept*/
    while(cl_sock == -1 && (errno == EAGAIN || errno == EWOULDBLOCK)){
        cl_sock = accept(serv_sock, &cl_dir, &len);
    }
    
    /*Le indicamos al padre que el pool libre disminuye en uno*/
    Up_Semaforo(despertador, 0, 0);
    
    Up_Semaforo(mutex, 0, 0);
    

    if(cl_sock == -1){ /*Caso de error*/
        syslog (LOG_ERR, "Error en el accept de una peticion. Error: %s\n",strerror(errno));
        free_config(conf);
        return ERROR;
    }
    
    /*Lanzamos el servicio*/
    aux = servicio(cl_sock, conf);
    /*Cerramos la conexion*/
    close(cl_sock);
    /*Cerramos configuracion*/
    free_config(conf);
    /*Permitimos una nueva conexion ya que esta se cierra*/
    Up_Semaforo(conexiones, 0, 0);
    return aux;
}


/**
 * Implementacion de servicio
 *
 * Por ahora solo realizara un echo
 */
int servicio(int cl_sock, Config *conf){
    int ret;
    
    /*Establecemos conexion persistente*/
    while(1){ 
        ret = procesar_peticion(cl_sock, conf);
        if(ret == TIMEOUT_ERR) return TIMEOUT_ERR; /*CASO DE TIMEOUT*/
        else if(ret == CLOSED_CONNECTION) return OK; /*CASO DE CIERRE DE CONEXION*/
    }
}




/**
 * Envia un paquete con la informacion de cadena.
 */

int enviar_paquete(int cl_sock, char *cadena, int len){
    
    if( cadena == NULL || len < 0){
        syslog (LOG_ERR, "Error en parametros entrada en enviar_cadena\n");
        return ERROR;
    }

    if(send(cl_sock, cadena, sizeof(char)*len, 0) < 0){
        syslog (LOG_ERR, "Error en send. Error: %s\n", strerror(errno));
        return ERROR;
    }

    return OK;
}

/**
 * Dado un path enviamos un fichero por un socket
 */
int enviar_fichero(int socket_id, char *path){
    int desc, len, buf_size;
    char buf[MAX_LEN];

    /*Probamos argumentos*/
    if(socket_id < 0 || path == NULL ){
        syslog(LOG_ERR, "Error en argumentos de enviar_fichero.\n");
        return ERROR;
    }
    
    /*Abrimos ficherp*/
    desc = open(path, O_RDONLY);
    if(desc < 0){
        syslog(LOG_ERR,"Error en la apertura de fichero %s. Error: %s\n",
                path, strerror(errno));
        return ERROR;
    }
    
    /*Enviamos*/
    buf_size = MAX_LEN*sizeof(char);
    len = buf_size;
    while(len  == buf_size){
        len = read(desc, buf, buf_size);
        
        if(len < 0){
            syslog(LOG_ERR,"Error leyendo fichero %s. Error: %s\n",
                    path, strerror(errno));
            return ERROR;
        }else if(len > 0){
            if(send(socket_id,buf,len,0) < 0){
                syslog(LOG_ERR,"Error en el envio de fichero %s. Error: %s\n",
                        path, strerror(errno));
                return ERROR;
            }
        }/*Caso de aux==0 No se envia nada*/
    }
    close(desc);
    return OK;
}



/*FUNCIONES AUXILIARES*/

/**
 * Esta funcion se encarga de crear e inicializar un semaforo.
 *
 * @param semid: El int en el que se guardara el identificador del semaforo
 *        ini: Valor inicial que tendra el semaforo
 *
 * @return ERROR o OK
 */

int configuracion_semaforo(int *semid, int ini){
    unsigned short array[1];
    
    /*Creamos el semaforo*/
    if(Crear_Semaforo(rand(), 1, semid) == ERROR){
        syslog (LOG_ERR, "Error en crear semaforo\n");
        return ERROR;
    }

    /*Inicializamos el valor*/
    array[0]=ini;
    Inicializar_Semaforo(*semid,array);
    return OK;
}

/**
 * El siguiente handler y las variables globales seran usadas EXCLUSIVAMENTE
 * para permitir el cierre del programa mediante un SIGINT sin que suponga
 * perdida de memoria
 */
Config *conf_global;
int server_sock_global, mutex_global, despertador_global, conexiones_global;
/*handler*/
void handler(int signum){
    Borrar_Semaforo(mutex_global);
    Borrar_Semaforo(despertador_global);
    Borrar_Semaforo(conexiones_global);
    close(server_sock_global);
    free_config(conf_global);
    closelog (); 
    exit(EXIT_SUCCESS);
}

/**
 * Funcion que ejecuta toda la funcionalidad de los procesos hijo.
 * Desactiva el handler del proceso padre
 * acepta una peticion - ejecuta servicio
 * cierra y libera
 * exit
 */
void child_execute(int serv_sock, int mutex, int despertador, int conexiones, Config *conf){
    /*Quitamos handler para los hijos*/
    signal(SIGINT, SIG_DFL);
    /*Ejecutamos accept*/
    server_accept(serv_sock, mutex, despertador, conexiones, conf);
    /*Cerramos y liberamos duplicados del hijo*/
    close(serv_sock);
    free_config(conf);
    exit(EXIT_SUCCESS);
} 

/**
 * Implementacion de server_execute_pool()
 */
int server_execute_pool(int serv_sock, Config *conf){
   int mutex, despertador, conexiones, i;

   /*Configuramos mutex que proteje al accept*/
   if(configuracion_semaforo(&mutex, 1) == ERROR){
       return ERROR;
   }
   
   /*Configuramos despertador que indica al padre que tiene que crear proceso*/
   if(configuracion_semaforo(&despertador, 0) == ERROR){
       Borrar_Semaforo(mutex);
       return ERROR;
   }

   /*Configuramos el semaforo que controla el maximo de conexiones*/
   if(configuracion_semaforo(&conexiones, get_max_clients(conf)) == ERROR){
       Borrar_Semaforo(mutex);
       Borrar_Semaforo(despertador);
       return ERROR;
   }

   /*Permitimos el cierre del servidor con un SIGINT sin perdida de memoria*/
   mutex_global = mutex;
   despertador_global = despertador;
   conexiones_global = conexiones;
   server_sock_global = serv_sock;
   conf_global = conf;
   signal(SIGINT, handler);
   
   /*Inicializamos pool*/
   for(i=0; i < POOL_SIZE; i++){
       if(fork() == 0){
           /*Operaciones de hijos*/
           child_execute(serv_sock, mutex, despertador, conexiones, conf);
      }
   }

   /*Mantenemos el pool con una cantidad constante de procesos*/
   while(1){
       Down_Semaforo(despertador,0,0);
       if(fork() == 0){
           child_execute(serv_sock, mutex, despertador, conexiones, conf);
       }
   }
}

