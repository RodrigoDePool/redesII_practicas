/**
 * Autores: Rodrigo De Pool y Lucia Asencio
 *
 * Implementacionde config.h
 */

#include <stdlib.h>
#include <unistd.h>
#include <confuse.h>
#include <syslog.h>
#include <string.h>
#include "../includes/config.h"



struct _Config {
    char *server_root;
    char *server_signature;
    long int max_clients;
    long int listen_port;    
};


/*FUNCION AUXILIARES*/

/**
 * Prueba el argumentos de funciones get y en caso de error escribe en el syslog
 * @return    OK o ERROR
 */
int args_get(Config *conf){
    if(conf == NULL){ 
        syslog(LOG_ERR,"Error, conf NULL en instruccion get.\n");
        return ERROR;
    }
    return OK;
}



/*FUNCIONES PRINCIPALES*/

/**
 * Demoniza el proceso
 */
void do_deamon(){
    pid_t pid;

    pid = fork();
    /*caso de error*/
    if(pid < 0) exit(EXIT_FAILURE);
    /*cerramos proceso padre*/
    if(pid > 0) exit(EXIT_SUCCESS);
    
    /*Creamos una nueva sesion para el proceso*/
    if(setsid()<0){
        syslog(LOG_ERR,"Error al crear nueva sesion de proceso.\n");
        exit(EXIT_FAILURE);
    }

    /*Cerramos los descriptores de standard in,out y err*/
    close(STDIN_FILENO);
    close(STDOUT_FILENO);
    close(STDERR_FILENO);
    syslog(LOG_INFO,"Proceso demonizado correctamente");
    return;
}


/**
 * Devuelve la configuracion del servidor
 */
Config *server_configuration(){
    Config *conf;
    int len, ret;

    /*Alocamos memoria para config*/
    conf = (Config *)malloc(sizeof(Config));
    if(conf == NULL){
        syslog(LOG_ERR,"Error en la alocacion de memoria para config.\n");
        return NULL;
    }
    /*Inicializacion necesaria por cfg*/
    conf->server_root = NULL;
    conf->server_signature=NULL;

    /*NOTA: la strings se alocan a traves de la libreria confuse*/

    /*Inicializamos y leemos el fichero de configuracion*/
    cfg_opt_t opts[] = {
        CFG_SIMPLE_STR("server_root", &conf->server_root),
        CFG_SIMPLE_STR("server_signature", &conf->server_signature),
        CFG_SIMPLE_INT("listen_port", &conf->listen_port),
        CFG_SIMPLE_INT("max_clients", &conf->max_clients),
        CFG_END()
    };
    cfg_t *cfg;
   
    /*Leemos y parseamos*/
    cfg = cfg_init(opts, 0);
    ret = cfg_parse(cfg, CONFIG_FILE);

    /*Liberamos la estructura, las strings se mantienen en Config*/
    cfg_free(cfg);
    
    /*casos de error de parseo*/
    if(ret == CFG_FILE_ERROR){
        syslog(LOG_ERR,"Error al abrir fichero de configuracion.\n");
        free_config(conf);
        return NULL;
    }else if(ret == CFG_PARSE_ERROR){
        syslog(LOG_ERR, "Error en parseo de fichero configuracion.\n");
        free_config(conf);
        return NULL;
    }

    /*Si el server root acaba en barra, la quitamos*/
    len = strlen(conf->server_root);
    if(conf->server_root[len - 1] == '/'){
        conf->server_root[len - 1] = '\0';
    }
    
    /*Control de argumentos correctos en config*/
    if(conf->listen_port < 1 || conf->listen_port > 65535){
        syslog(LOG_ERR, "Numero de puerto invalido\n");
        free_config(conf);
        return NULL;
    }else if(access(conf->server_root,F_OK) < 0){
        syslog(LOG_ERR, "Error, server_root invalido\n");
        free_config(conf);
        return NULL;
    }else if( conf->max_clients < 1){
        syslog(LOG_ERR, "Maximo de clientes invalido\n");
        free_config(conf);
        return NULL;
    }


    return conf;
}


void free_config(Config *conf){
    if(conf == NULL) return;
    if( conf->server_root != NULL) free(conf->server_root);
    if( conf->server_signature != NULL) free(conf->server_signature);
    free(conf);
}


/*FUNCIONES GET*/

long int get_max_clients(Config *conf){
    if(args_get(conf) == ERROR) return ERROR;
    return conf->max_clients;
}

long int get_listen_port(Config *conf){
    if(args_get(conf) == ERROR) return ERROR;
    return conf->listen_port;
}

char *get_server_root(Config *conf){
    if(args_get(conf) == ERROR) return NULL;
    return conf->server_root;
}

char *get_server_signature(Config *conf){
    if(args_get(conf) == ERROR) return NULL;
    return conf->server_signature;
}

