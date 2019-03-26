/**
 * Autores: Rodrigo De Pool y Lucia Asencio
 *
 * Defines utiles
 */

#ifndef UTILS_H
#define UTILS_H

#define OK 1
#define CLOSED_CONNECTION 0
#define ERROR -1
#define LOG_NAME "p1_redes2"  
#define MAX_LEN 8192
#define TIMEOUT 60      /*Timeout en segundos, 60s para esperar un mensaje del cliente*/
#define SCRIPT_TIMEOUT 5 /*Timeout que esperamos a que acabe un script 5s*/
#define TIMEOUT_ERR 11  /*Numero en caso de que el cliente haga timeout*/
#define POOL_SIZE 3      /*Cantidad de procesos libre en el pool en todo momento (menor que max_conections)*/
#define MAX_HEADERS 50  /*Maximo numero de headers de una peticion*/
#define MAX_TYPELEN 20  /*Max tam de la string de content-type de la http response,
                         segun los content types contemplados en el enunciado de la practica*/
#define MAX_STRING 50 /*Max tam para strings varias, por ej, cabeceras de response*/
#define PYTHON_INTERPRETER "/usr/bin/python" /*Path a interprete python*/
#define PHP_INTERPRETER "/usr/bin/php" /*Path a interprete php*/

/*ERROR PATHS*/
#define PATH_400 "errors/400.html"
#define PATH_404 "errors/404.html"
#define PATH_500 "errors/500.html"
#define PATH_501 "errors/501.html"
#define PATH_508 "errors/508.html"
#define PATH_418 "errors/418.html"
#define PATH_405 "errors/405.html"
#define PATH_413 "errors/413.html"
#define PATH_408 "errors/408.html" 

#endif
