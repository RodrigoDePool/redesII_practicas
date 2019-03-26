#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <syslog.h>
#include "../includes/server.h"
#include "../includes/config.h"



/*EJECUTABLE*/
int main(){
    Config *conf;
    int port, max_connections, sock;

	/*Abrimos log*/
	openlog(LOG_NAME, LOG_PID | LOG_NDELAY, LOG_USER);
    
    /*Codigo de fichero de configuracion*/
    conf = server_configuration();
    if(conf == NULL){
        return -1;
    }
    port = get_listen_port(conf);
    max_connections = get_max_clients(conf);
    
    /*Demonizamos*/
    do_deamon();
  
    /*Inicializamos el servidor*/
    if( server_ini(port, max_connections, &sock) == ERROR){
        free_config(conf);
        return -1;
    }
    syslog (LOG_INFO, "Servidor correctamente inicializado, esperando clientes\n");
    
    if(server_execute_pool(sock, conf) == ERROR){
        syslog (LOG_ERR, "Error con el pool de procesos/ejecucion del servidor\n");
        free_config(conf);
        close(sock);
        return -1;
    }
    return 1;
}


