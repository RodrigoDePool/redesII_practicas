/**
 * Autores: Rodrigo De Pool y Lucias Asencio
 * 
 * Implementacion de la funcionalidad http
 *
 */

#include "../includes/http_service.h"
#include "../includes/picohttpparser.h"
#include "../includes/server.h"
#include "../includes/utils.h"
#include <string.h>
#include <stdio.h>
#include <syslog.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <errno.h>
#include <sys/socket.h>

struct _Response{
    char start_line[MAX_STRING]; /*Version + codigo*/ 
    char date[MAX_STRING]; /* https://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.3.1 */
    char signature[MAX_STRING];
    char last_modif[MAX_STRING];
    char content_type[MAX_STRING];
    char content_length[MAX_STRING];
    char * fname;
    char *args;
    char *ext; 
    char *body;
    int socket_id;
};

/********** DECLARACION FUNCIONES PRIVADAS EN ORDEN DE IMPLEMENTACION ***********/

			/*************************************/
			/*********** PARA LA FECHA ***********/
			/*************************************/
			
/*Estas 3 funciones sirven para rellenar, segun el formato http,
 * las cabeceras Date y Last-Modified de una HTTP response
 */
int last_modified(Response *response);
int date(Response *response);
int std_http_date(struct tm* mytime, char *dest );

			/**************************************/
			/******** PARA COMPROBACIONES *********/
			/**************************************/
/**
 * int uri_bienformada(char* path, Response *response)
 *
 * @param Response* response: estructura con la info de response
 * @param char* path: puntero a la uri
 * @param char* method: metodo de la peticion (si la uri es '*', el metodo debe
 * ser options)
 *
 * @return OK si uri bien formada, ERROR en otro caso
 */
int uri_bienformada(const char *path, Response *response, char* method);


/**
 * int verbo_soportado(char* method, Response *response)
 *
 * @param char* method: verbo de la peticion
 * @param Response *response: estructura con la response
 * 
 * @return OK si el metodo es soportadoi (GET/POST/OPTIONS), ERROR
 * en otro caso
 */

int verbo_soportado(const char* method, Response *response);

/**
 * int file_exists(char *path, int path_len, Response *response);
 *
 * 1. Esta funcion comprobara si el fichero path (direccion relativa al
 * directorio donde se ejecuta el servidor) existe. 
 * 2. Esta funcion rellena el campo fname de response con la dir absoluta del fich
 * 3. Esta funcion rellena el campo last_modified de response 
 * 4. Esta funcion rellena el campo content-length de response
 *
 * @param char* path: path de la peticion
 * @param int path_len: longitud de la string que contiene el path
 * @param Response *response: estructura con la response
 * @param conf: Configuracion del servidor para ssaber el server root
 *
 * SI RETURN ERROR, NO HACE FALTA LIBERAR RESPONSE->FNAME. SI RETURN OK, SI
 *
 * @return OK/ERROR
 */
int file_exists(const char *path, int path_len, Response *response, Config *conf);



			/*************************************************/
			/****** RELLENAN CAMPOS ESTRUCTURA RESPONSE ******/
			/*************************************************/

/**
 * int separa_path(Response *response)
 * 
 * Esta funcion coloca un \0 en la '?' que separa response->fname de argumentos.
 * Con esto, rellena en reponse los punteros a ext (extension) y args (argumentos)
 * En caso de que '?' sea el ultimo caracter, devolvemos un paquete de error
 *
 * @param Response *response: estructura con la response
 *
 * @return OK, ERROR
 */
 
int separa_path(Response *response);			

/**
 * int get_contenttype(Response *response)
 *
 * Esta funcion asocia un content-type a response en funcion de su campo ext
 *
 * @param Response *response: estructura con la response
 * 
 * @return OK 
 */
int get_contenttype(Response *response);

/**
 * int get_contentlength(Response *response)
 *
 * Rellena el campo content_length de la Response con el tamanio del fichero
 * de nombre response->fname
 *
 * @param Response *response: estructura con la response
 *
 * @return OK/ERROR
 */
int get_contentlength(Response *response);

			/****************************************/
			/****** PARA DIFERENTES RESPUESTAS ******/
			/****************************************/

/**
 * Funcion que se encarga de formatear la cabecera del paquete http.
 * Se escribe en cadena.
 *
 * @param int last_mod_bool: si es 1 se escribira el campo last modification,
 * si es otro numero no se escribira.
 * @param int allow_bool: si es 1, se asume metodo options: se incluye cabecera
 * allow y se excluyen content type y last modified. Si es 0, not a todo lo anterior.
 */
void format(Response *response,char *cadena, int last_mod_bool, int allow_bool);

/**
 * int gestiona_error(Response *response, int code)
 *
 * Gestiona las responses con codigos de error.
 * Ajusta el content-type a html y se asegura de que no se envia la cabecera
 * last-modified.
 *
 * @param Response *response: estructura response de la peticion
 * @param int code: codigo de error. Por ahora soporta 400, 404, 500, 501
 *
 * @return OK/ERROR
 */
int gestiona_error(Response *response, int code);

/**
 * Gestiona la peticion en funcion del verbo y del fichero
 *
 * @param char* method: verbo de la peticion
 * @param Response *response: estructura response de la peticion
 *
 * @return OK/ERROR
 */
int gestiona_response(const char* method, Response* response);

/**
 * Gestiona las peticiones GET, ya aclararemos que hace
 *
 * @param Response *response: estructura response de la peticion
 *
 * @return OK/ERROR
 */
int gestiona_get( Response *response);

/**
 * Gestiona las peticiones POST, ya aclararemos que hace
 *
 * @param Response *response: estructura response de la peticion
 *
 * @return OK/ERROR
 */
int gestiona_post(Response *response);

/**
 * Gestiona las peticiones OPTIONS, ya aclararemos que hace
 *
 * @param Response *response: estructura response de la peticion
 *
 * @return OK/ERROR
 */
 
int gestiona_options(Response *response);

/**
 * Se encarga de la ejecucion del script. Crea un hijo en el cual
 * ejecuta el interprete que corresponda seguna las macros definidas, 
 * al interprete le pasa el script solicitado. Finalmente se le manda
 * por stdin los argumentos del programa al hijo y se leen por
 * stdout. El resultado se devuelve en result y su tamano en size
 *
 * NOTA: result TIENE que ser liberado fuera de esta funcion
 * NOTA2: Esta funcion se encarga de mandar un paquete de error en caso de error.
 *
 * @param response: Response del que se obtenddra la extension
 * @param args: argumentos que se le suministran al script por stdin
 * @param result: Cadena en la que se almacena el resultado
 * @param size: Aqui se devuelve el tamano del resultado en bytes
 *
 * @return OK o ERROR
 */
int ejecuta_script(Response *response, char *args, char **result, int *size);

/*********************** FUNCIONES PUBLICAS *************************/

int procesar_peticion(int cl_sock, Config *conf){    
    /*Variables par parse_request*/
    const char *method_aux, *path_aux;
    char *method, *path, req[MAX_LEN];
    int req_len=0, minor_version, prevbuflen=0,ret,pret=0;
    struct phr_header hdrs[MAX_HEADERS];  	
    size_t method_len, path_len, num_headers; 
    /*Varibles para otras cosas*/
    Response response;
    
 
    /*Rellenamos la parte de la estructura Response comun a todos los casos */
    date(&response);
    strcpy(response.signature, "Server: ");
    strcat(response.signature, get_server_signature(conf));
    response.socket_id = cl_sock; 
  
    /*Lectura de paquete*/
    while (pret <= 0) {
        /*Leemos total o parcialmente la request*/
        while ((ret = recv(cl_sock, req + req_len, sizeof(req) - req_len,0)) == -1 && errno == EINTR);
        /*Caso de cierre, timeout o error de lectura*/
        if(ret == 0){
            return CLOSED_CONNECTION;
        }else if(ret <= 0 && errno == TIMEOUT_ERR){
            gestiona_error(&response, 408);
            syslog(LOG_ERR, "Tiempo de espera para la recepcion del request acabado, 408 sent\n");
            return TIMEOUT_ERR;
        }else if (ret <= 0){
            gestiona_error(&response,500);
            syslog(LOG_ERR, "Error en la comunicacion con cliente.\n");
            return ERROR;
        }
        prevbuflen = req_len;
        req_len += ret;
       /* Parseo de request*/
       num_headers = sizeof(hdrs)/sizeof(hdrs[0]);
       pret = phr_parse_request(req, req_len, &method_aux, &method_len, &path_aux, &path_len,
                                &minor_version, hdrs, &num_headers, prevbuflen);
    
       /*Si hay error en el parseo o el tamano de request es muy grande damos 500/400*/
       if (pret == -1 ){
            gestiona_error(&response,500);
            syslog(LOG_ERR, "Error en la funcion phr parse request, 500 sent\n");
            return ERROR;
       }
       if (req_len == sizeof(req)){
            gestiona_error(&response , 413);
            syslog(LOG_ERR, "Request too long, 413 sent"); /*400 xq no sabemos si 414 o 431*/
            return ERROR;
       }
    }
    /*Fin de lectura de paquete*/
    /*Como pret devuelve lectura correcta a partir de aqui asumimos que */
    /*method_aux, method_len, req_len, path_aux y path_len son correctos*/

    /*Rellenamos los valores del metodo y el path*/
    method = (char *) malloc(sizeof(char)*(method_len + 1));
    path = (char *) malloc(sizeof(char)*(path_len + 1));
    if( method == NULL || path == NULL){
        if(method == NULL) free(method);
        if(path == NULL) free(path);
        gestiona_error(&response, 500);
        syslog(LOG_ERR,"Error en la alocacion de memoria\n");
        return ERROR;
    }
    sprintf(method, "%.*s", (int)method_len, method_aux);
    sprintf(path, "%.*s", (int)path_len, path_aux);
    

      
    /* 1. URI bien formada?	2. Verb soportado?      3. Recurso disponible? (*/
    if((uri_bienformada(path, &response, method) == ERROR) ||
        (verbo_soportado(method, &response) == ERROR) ||
        (file_exists(path, path_len, &response, conf) == ERROR)){
        free(method);
        free(path);
        return ERROR;
    } 
    
    if(strcmp(path, "*") != 0) {/*Estas funciones llevarian a error en caso de OPTIONS '*' */
        /* Ahora que tenemos el fname, podemos rellenar ciertas cabeceras: */
        if( (last_modified(&response) == ERROR) ||
            (get_contentlength(&response) == ERROR) ||
            (get_contenttype(&response) == ERROR) ){
            free(method);
            free(path);
            free(response.fname);
            return ERROR;
        }
    }
    /*Falta por rellenar el puntero al body de la request, que nos hara falta para los argumentos del post*/
    /*Si hay contenido:*/
    /*Apuntamos al ultimo header, sumamos el tamanio de ese header y sumamos el tamanio del \r\n\r\n */
    /*Si no rellenamos con NULL*/
        response.body = (char *) hdrs[num_headers-1].value + hdrs[num_headers-1].value_len + 4*sizeof(char);  
    if(req +req_len<=response.body){
        response.body = NULL;
    }

    if(gestiona_response(method,&response) == ERROR){
        free(method);
        free(path);
        free(response.fname);
        return ERROR;
    }
    
    free(method);
    free(path);
    free(response.fname);
    return OK;              
 }
 
 /****************** IMPLEMENTACION FUNCIONES PRIVADAS ***********/

            /*********** PARA LA FECHA ***********/
int last_modified(Response *response){
    struct tm *mytime;
    struct stat attrib;
    stat(response->fname, &attrib);
    mytime = gmtime(&(attrib.st_mtime));
    strcpy(response->last_modif, "Last-Modified: "); 
    std_http_date(mytime, response->last_modif);
    return OK;
}

int date(Response *response){
    time_t now;
    struct tm* mytime;
    time (&now);
    mytime = gmtime(&now);
    strcpy(response->date,"Date: ");
    std_http_date(mytime, response->date);
    return OK;
}

int std_http_date(struct tm* mytime, char *dest ){
    /*TIENE QUE HABER UNA FORMA BONITA DE HACER ESTO SIN PELEAR CON FICHEROS :( */
    char dias[7][4], meses[12][4];
    char aux_string[100];
    strcpy(dias[0], "Mon"); strcpy(dias[1], "Tue");	strcpy(dias[2], "Wed");
    strcpy(dias[3], "Thu");	strcpy(dias[4], "Fri");	strcpy(dias[5], "Sat");
    strcpy(dias[6], "Sun");
    strcpy(meses[0], "Jan"); strcpy(meses[1], "Feb"); strcpy(meses[2], "Mar");
    strcpy(meses[3], "Apr"); strcpy(meses[4], "May"); strcpy(meses[5], "Jun");
    strcpy(meses[6], "Jul"); strcpy(meses[7], "Aug"); strcpy(meses[8], "Sep");
    strcpy(meses[9], "Oct"); strcpy(meses[10], "Nov"); strcpy(meses[11], "Dec");

    sprintf(aux_string, "%s, %d %s %d %d:%d:%d GMT", dias[mytime->tm_wday], mytime->tm_mday,
            meses[mytime->tm_mon], 1900 + mytime->tm_year, mytime->tm_hour, mytime->tm_min, mytime->tm_sec);
    strcat(dest, aux_string);
    return OK;
}

            /**************************************/
            /******** PARA COMPROBACIONES *********/
            /**************************************/

int uri_bienformada(const char *path, Response *response, char* method){
   /* Una uri será una direccion relativa o un '*'
     * Basta con comprobar que el primer caracter es '/' y contiene ".", o es un *
     */ 
    if( ((path[0] == '/') && (strrchr(path, (int)'.') != NULL )) || 
        ((strcmp(path, "*") == 0) && (strcmp(method, "OPTIONS") == 0 ))){        
        syslog(LOG_INFO, "Uri %s bien formada\n", path);
        return OK;
    }
    syslog(LOG_ERR, "Uri %s mal formada: (1er char != '/' o no hay '.'), o no es un '*' Codigo 400 enviado\n", path);
    gestiona_error(response, 400);
    return ERROR;
}

int verbo_soportado(const char* method, Response *response){
    
    if((strcmp(method, "GET") == 0) ||
       (strcmp(method, "POST") == 0) ||
       (strcmp(method, "OPTIONS") == 0)){
        syslog(LOG_INFO, "Metodo %s soportado\n", method);
        return OK;
    }
    syslog(LOG_ERR, "Metodo %s no soportado, 501 sent \n", method);
    gestiona_error(response, 501);
    return ERROR;
}

int file_exists(const char *path, int path_len, Response *response, Config *conf){
    int fname_len;
    char*server_root; /*directorio raiz del servidor*/
    int options;

    options = strcmp(path, "*");

    if(options == 0){
	    fname_len = 2;
    }else{
        /* Formamos el path del recurso */	
        server_root = get_server_root(conf);
        if(server_root == NULL){
            syslog(LOG_ERR, "Error obteniendo dir raiz del servidor en file_exists, 500 sent\n");	
            gestiona_error(response, 500);
            return ERROR;
        }
         fname_len = strlen(server_root) + path_len + 1; /* strlen + pathlen + 1: '/path/servidor/' + '/path/recurso' + '\0'*/	
    }
    response->fname=NULL;
    if ((response->fname = (char *)malloc(fname_len * sizeof(char))) == NULL){
        syslog(LOG_ERR, "Error en erserva de memoria en file_exists, 500 sent\n");
        gestiona_error(response, 500);
        return ERROR;
    }

    /*Usamos copy y concatenar para formar el path del fichero: 'server_root' + 'path' + '\0'*/
    if(options == 0){ /*Si la peticion es un OPTIONS * */
        strcpy(response->fname, path);
    }else{
        strcpy(response->fname, server_root);
        strcat(response->fname, path);	

        /* Una vez tenemos fname con path+'?'+argumentos de entrada, separamos la cadena
         * con punteros para poder comprobar si el fichero existe, su fecha de modif, etc
         */
        if(separa_path(response) == ERROR) return ERROR;
        /* Miramos si existe el fichero?*/
        if(access(response->fname, F_OK) == -1){
                syslog(LOG_ERR, "Fichero %s no encontrado, 404 sent\n", response->fname);
                free(response->fname);
                gestiona_error(response, 404);
                return ERROR;
            }
    }
    return OK;
}

            /*************************************************/
            /****** RELLENAN CAMPOS ESTRUCTURA RESPONSE ******/
            /*************************************************/

int separa_path(Response *response){
    char *interrogacion;
    
    interrogacion = strrchr(response->fname,'?');

    if(interrogacion == NULL){
        response->args = NULL;
    }else if(interrogacion == response->fname + strlen(response->fname) - 1 ){
        /*En caso de que la interrogacion sea el ultimo caracter de fname*/
        syslog(LOG_ERR, "Uri mal formada:'?' sin argumentos. Codigo 400 enviado\n");
        gestiona_error(response, 400);
        return ERROR;
    }else{
        response->args = interrogacion + sizeof(char);/*args apunta al char siguiente a '?'*/
        *interrogacion = '\0';
    }
   
    response->ext = strrchr((const char *)response->fname, (int)'.');
    /*Sabemos que != NULL xq uri_bienformada comprueba q hay un '.'*/
    return OK;
}

int get_contenttype(Response *response){
    /*A estas alturas response->ext no es null por la implementacion de uri_bienformada y separa_path*/
    
    /*Content-type de acuerdo con la extension*/
    if(strcmp(".txt", response->ext) == 0){
        strcpy(response->content_type, "Content-Type: text/plain");
    }else if( strcmp(".htm", response->ext) == 0 || strcmp(".html", response->ext) == 0 || strcmp(".php", response->ext) == 0 || strcmp(".py",response->ext) == 0 ) {
        strcpy(response->content_type, "Content-Type: text/html");
    }else if(strcmp(".gif", response->ext) == 0){
        strcpy(response->content_type, "Content-Type: image/gif");
    }else if( (strcmp(".jpg", response->ext)) == 0 || (strcmp(".jpeg", response->ext)) == 0){
        strcpy(response->content_type, "Content-Type: image_jpeg");
    }else if( (strcmp(".mpg", response->ext)) == 0 || (strcmp(".mpeg", response->ext)) == 0){
        strcpy(response->content_type, "Content-Type: image/mpeg");
    }else if( (strcmp(".doc", response->ext)) == 0 || (strcmp(".docx", response->ext)) == 0){
        strcpy(response->content_type, "Content-Type: application/msword");
    }else if(strcmp(".pdf", response->ext) == 0){
        strcpy(response->content_type, "Content-Type: application/pdf"); 
    }else{
        syslog(LOG_ERR, "Extension %s no soportada, 418 sent\n", response->ext);
        gestiona_error(response, 418);
        return ERROR;
    }
    return OK;
}

/**
 * Funcion auxiliar que ejecuta contentlegth con cualquier path.
 * Esto nos servira para inciar fname o para los casos de error
 */
int get_contentlength_aux(Response *response, char *path){
    struct stat attrib;
    char aux[MAX_STRING];
    if(stat(path, &attrib)!=0) return ERROR;
    sprintf(aux, "Content-Length: %d", (int)attrib.st_size);
    strcpy(response->content_length, aux);
    return OK;

}

int get_contentlength(Response *response){
  return get_contentlength_aux(response, response->fname); 
}

            /****************************************/
            /****** PARA DIFERENTES RESPUESTAS ******/
            /****************************************/


void format(Response *response, char *cadena, int last_mod_bool, int allow_boolean){
    strcpy(cadena, response->start_line);
    strcat(cadena,"\n");
    if(allow_boolean == 1){
        strcat(cadena, "Allow: OPTIONS, GET");
        if((strcmp("*", response->fname) == 0) || (strcmp(".py", response->ext) == 0)
            || (strcmp(".php", response->ext) == 0) ){
        
            strcat(cadena,", POST"); 
        }
        strcat(cadena,"\n");
    }    
    strcat(cadena, response->date);
    strcat(cadena,"\n");
    strcat(cadena, response->signature);
    strcat(cadena,"\n");
    if(last_mod_bool == 1){
        strcat(cadena, response->last_modif);
        strcat(cadena,"\n");
    }
    if(allow_boolean == 0){
        strcat(cadena,response->content_type);
        strcat(cadena,"\n");
    }
    strcat(cadena, response->content_length);
    strcat(cadena,"\n\r\n");
    return;
}


int gestiona_error(Response *response, int code){
    char error_msg[MAX_LEN], err_path[MAX_LEN];
    
    /*Rellenamos la start_line y el content_type*/
    if(code == 400){
        strcpy(err_path, PATH_400);
        strcpy(response->start_line, "HTTP/1.1 400 Bad Request");
    }else if(code == 404){ 
        strcpy(err_path, PATH_404);
        strcpy(response->start_line, "HTTP/1.1 404 Not Found");
    }else if(code == 500){
        strcpy(err_path, PATH_500);
        strcpy(response->start_line, "HTTP/1.1 500 Internal Error");
    }else if(code == 501){
        strcpy(err_path, PATH_501);
        strcpy(response->start_line, "HTTP/1.1 501 Not Implemented");
    }else if(code == 418){
        strcpy(err_path, PATH_418);
        strcpy(response->start_line, "HTTP/1.1 418 I'm a teapot");
    }else if(code == 405){
        strcpy(err_path, PATH_405);
        strcpy(response->start_line, "HTTP/1.1 405 Method Not Allowed");
    }else if(code == 413){
        strcpy(err_path, PATH_413);
        strcpy(response->start_line, "HTTP/1.1 413 Request Entity Too Large");
    }else if(code == 408){
        strcpy(err_path, PATH_408);
        strcpy(response->start_line, "HTTP/1.1 408 Request Timeout");
    }else if(code == 508){
        strcpy(err_path, PATH_508);
        strcpy(response->start_line, "HTTP/1.1 508 Loop Detected");
    }else{	
        return ERROR;
    }

    /*Rellenamos campos*/
    strcpy(response->content_type, "Content-Type: text/html");
    /*Formateamos respuesta*/
    get_contentlength_aux(response,err_path);
    format(response,error_msg, 0, 0);
    
    /*La enviamos*/
    enviar_paquete(response->socket_id, error_msg, strlen(error_msg));
    /*Enviamos error html*/
    enviar_fichero(response->socket_id, err_path);  
    return OK;
}

int gestiona_response(const char* method, Response *response){
    
    strcpy(response->start_line, "HTTP/1.1 200 OK");
	
	if(strcmp(method, "GET") == 0) return gestiona_get(response);
	else if(strcmp(method, "POST") == 0) return gestiona_post(response);
	else return gestiona_options(response);	
    /*Ya hemos probado que es un verbo soportado*/
}

int gestiona_get(Response *response){
    /**
     * Veamos que hay que hacer aqui: 
     * 
     * Si es un fichero normal, ya se ha hecho contentlength
     * Si es un script, se ejecuta con los argumentos y se calcula
     * Luego se hace format y se envia :D
     */
    char msg[MAX_LEN], *result=NULL;
    int size=0;

    if(strcmp(response->ext, ".py" )!= 0 && strcmp(response->ext,".php")!=0){ 
        /*Caso en que no hay que ejecutar script*/
        format(response, msg, 1, 0);
        enviar_paquete(response->socket_id, msg, strlen(msg)*sizeof(char));
        enviar_fichero(response->socket_id, response->fname);        
    }else{
        /*Ejecuta script y guarda el content length*/
        if(ejecuta_script(response,response->args, &result, &size) == ERROR) return ERROR;
        sprintf(response->content_length, "Content-Length: %d", size);
        /*Formateamos cabecera y enviamos todo*/
        format(response,msg,1,0);
        enviar_paquete(response->socket_id,msg,strlen(msg)*sizeof(char));
        enviar_paquete(response->socket_id,result,size);
        /*Liberamos*/
        free(result);
    }    
    return OK;
}
	
int gestiona_post(Response *response){
    char *result=NULL;
    char msg[MAX_LEN];
    int size=0;

    /* En esta practica, post solo se ejecuta con scripts, (no formularios, etc) */
    if((strcmp(response->ext, ".php")!= 0) && (strcmp(response->ext, ".py") != 0)){ 
         gestiona_error(response, 405);
         syslog(LOG_ERR, "No es posible hacer POST de %s, 405 sent\n", response->ext);
         return ERROR;
    }
    if(ejecuta_script(response, response->body, &result, &size) == ERROR){
        return ERROR;
    }
    /*Actualizamos content length con el tamanio de result*/
    sprintf(response->content_length, "Content-Length: %d", size);
    format(response, msg, 1, 0);
    enviar_paquete(response->socket_id, msg, strlen(msg));
    enviar_paquete(response->socket_id, result, size);
    free(result);
    return OK;
}
int gestiona_options(Response *response){
	char msg[MAX_LEN];
	strcpy(response->content_length, "Content-Length: 0");
	if(strcmp(response->fname,"*") == 0) format(response,msg,0,1);
    else format(response, msg, 1, 1); 
    enviar_paquete(response->socket_id, msg, strlen(msg));
    return OK;
}


int ejecuta_script(Response *response, char *args, char **result, int *size){
    /*Conecta stdin del hijo con pipe en el padre*/
    int pipe_stdin[2];
    /*Conecta stdout del hijo con pipe del padre*/
    int pipe_stdout[2];
    int aux, len, aux_f, timeout_flag;
    fd_set file_set;
    struct timeval timeout;
    char interprete[MAX_STRING], *result_aux;
    
    /*Decidimos interprete a utilizar*/
    if(strcmp(response->ext,".py")==0){
        strcpy(interprete,PYTHON_INTERPRETER);
    }else{
        /*Solo soportamos python o php*/
        strcpy(interprete,PHP_INTERPRETER);
    }
    
    /*Generamos pipes y controlamos fallos*/
    if( pipe(pipe_stdin) == -1){
        gestiona_error(response, 500);
        syslog(LOG_ERR,"Error en la creacion de pipe para stdin.\n");
        return ERROR;
    }else if(pipe(pipe_stdout) == -1){
        close(pipe_stdin[0]);
        close(pipe_stdin[1]);
        gestiona_error(response, 500);
        syslog(LOG_ERR,"Error en la creacion de pipe para stdout.\n");
        return ERROR;
    }

    /*Fork y controlamos errores*/
    aux = fork();
    if(aux == -1){
        gestiona_error(response,500);
        syslog(LOG_ERR,"Error en el fork al ejecutar el script.\n");
        return ERROR;
    }else if(aux == 0){
        /*Ejecucion del hijo*/
       
        /*Cambiamos stdin y stdout del hijo*/
        dup2(pipe_stdin[0],STDIN_FILENO);
        dup2(pipe_stdout[1],STDOUT_FILENO);
        /*Cerramos todas las pipes, ya fueron copiadas*/
        close(pipe_stdin[0]);
        close(pipe_stdin[1]);
        close(pipe_stdout[0]);
        close(pipe_stdout[1]);
        /*Ejecutamos interprete con programa por argumento*/
        /*Primer argumento nombre del inteprete, segundo el programa*/
        execl(interprete, interprete,response->fname, NULL);
    }
    /*Ejecucion del padre*/
    /*Cerramos pipes que no usamos*/
    close(pipe_stdin[0]);
    close(pipe_stdout[1]);

    /*Escribimos en la entrada estandar los argumentos si los hay*/
    if(args != NULL)
        write(pipe_stdin[1],args,strlen(args)*sizeof(char));
    /*Indicamos finalizacion de la escritura*/
    close(pipe_stdin[1]);
    
    /*Configuramos el timeout en el read*/
    timeout.tv_sec = SCRIPT_TIMEOUT;
    timeout.tv_usec = 0;
    FD_ZERO(&file_set);             /*Configuracion de descriptores para select*/
    FD_SET(pipe_stdout[0],&file_set);

    /*Leemos en un buffer*/
    *result = (char *)malloc(MAX_STRING*sizeof(char));
    if( *result == NULL ){
        gestiona_error(response,500);
        syslog(LOG_ERR,"Error alocando memoria en script\n");
        close(pipe_stdin[1]);
        close(pipe_stdout[0]);
        return ERROR;
    }
    aux = 0;      /*bytes leidos*/
    len = MAX_STRING;/*Tamano de la cadena*/
    do{
        aux_f = 0;/*bytes leidos en esta iteracion*/

        /*Si se han leido tantos bytes como longitud, se hace realloc*/
        if(aux >= len){
            len = len + sizeof(char)*MAX_STRING;
            result_aux = (char *)realloc(*result, len);
            if(result_aux == NULL){
                free(*result);
                gestiona_error(response,500);
                syslog(LOG_ERR,"Error realocando memoria en script\n");
                close(pipe_stdin[1]);
                close(pipe_stdout[0]);
                return ERROR;
            }
            *result = result_aux;
        }

        /*Establecemos timeout en el read*/
        timeout_flag = select(pipe_stdout[0]+1 ,&file_set,NULL,NULL,&timeout);
        if(timeout_flag == 0){ /*Caso de timeout*/
            gestiona_error(response,508);
            syslog(LOG_ERR,"Timeout en ejecucion del script\n");
            close(pipe_stdout[0]);
            /*Devolvemos error porque no queremos cerrar la conexion*/
            /*Como en el caso en que fuera un timeout de peticion   */
            return ERROR;    
        }else if(timeout_flag < 0){ /*Caso de error*/
            gestiona_error(response,500);
            syslog(LOG_ERR,"Error en ejecucion del script\n");
            close(pipe_stdout[0]);  
            return ERROR;    
        }
        
        /*Leemos en result + bytes leidos*/
        aux_f = read(pipe_stdout[0],*result + aux , len-aux);
        /*Guardamos total de bytes leidos*/
        aux += aux_f;
        /*Leemos hasta que los bytes leidos en esta iteracion sean 0*/
    }while(aux_f > 0);
    /*Devolvemos los bytes leidos*/
    *size = aux;
    /*Cerramos pipes ya utilizados*/
    close(pipe_stdout[0]);
    return OK;
}





