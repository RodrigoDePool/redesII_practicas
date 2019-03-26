/**
 * @file semaforos.c
 * @author Lucia Asencio y Rodrigo de Pool
 * @date 31-3-2017
 * @brief fichero que contiene la implementacion de la libreria de semaforos
 */
#include <sys/sem.h>
#include <sys/shm.h>
#include <stdio.h>
#include <stdlib.h>
#include "../includes/semaforos.h"

/**
 * Crea un nuevo semaforo con el key dado y del tamanio indicado.
 * Se inicializan los valores a 0 de todos los semaforos.
 * @param  key   clave para inicializar el semaforo
 * @param  size  cantidad de semaforos que se quieren
 * @param  semid puntero a entero donde se guarda el identificador del array
 * de semaforos
 * @return      devuelve un 0 si el semaforo ya estaba creado 1 si se ha creado.
 * Si se creo el semaforo en semid se guarda su Identificador
 * Si ya estaba creado y no hubo error se devuelve el identificador, en este caso
 * los valores del semaforo no son cambiados
 * Si no se logra crear el semafoto devuelve ERROR en semid
 */
int Crear_Semaforo(key_t key, int size, int *semid){
    int i;
    union semun {
        int             val;
        struct semid_ds *semstat;
        unsigned short  *array;
    } arg;

    *semid = semget(key, size, IPC_CREAT | IPC_EXCL | SHM_R | SHM_W);
    if (*semid == ERROR) {
        *semid = semget(key, size, SHM_R | SHM_W);
        if (*semid == ERROR) {
            return ERROR;
        }
        return 0;
    }
    /*En caso de que se este creando el semaforo se incializa la estructura*/
    arg.array = (unsigned short *) malloc(sizeof(unsigned short) * size);

    for (i = 0; i < size; i++)
        arg.array[i] = 0;

    /*Se fijan valores a 0*/
    semctl(*semid, size, SETALL, arg);
    free(arg.array);
    return 1;
}

/**
 * Iniciliaza el semaforo a los valores indicados
 * @param  semid id del semaforo
 * @param  array array de valores a asignar al semaforo
 * @return       OK si no hubo errores, ERROR si los hubo
 */
int Inicializar_Semaforo(int semid, unsigned short *array){
    union semun {
        int             val;
        struct semid_ds *semstat;
        unsigned short  *array;
    } arg;
    if (semid < 0 || array == NULL) return ERROR;
    arg.array = array;
    if (semctl(semid, 0, SETALL, arg) == -1)
        return ERROR;
    return OK;
}

/**
 * Borra un array de semaforos
 * @param  semid identificador del array
 * @return       devuelve OK si todo correcto, y ERROR en caso de error
 */
int Borrar_Semaforo(int semid){
    if (semctl(semid, 0, IPC_RMID, 0) == -1) {
        return ERROR;
    }
    return OK;
}

/**
 * Funcion privada que nos sirve para generalizar el codigo de down y up
 * de un semaforo
 * El unico cambio es que op es -1 y si es down y 1 si es up.
 * Devuelve ERROR si hubo error o OK en caso de no haberlo
 */
int operacionSemaforo(int id, int num_sem, int undo, int op){
    struct sembuf sem_oper;

    if (id < 0 || num_sem < 0 || (op != -1 && op != 1))
        return ERROR;

    sem_oper.sem_num = num_sem;
    sem_oper.sem_op  = op;
    sem_oper.sem_flg = undo;

    if (semop(id, &sem_oper, 1) == -1)
        return ERROR;
    return OK;
}

/**
 * Hace down a un semaforo
 * @param  id      identificador de array de semaforos
 * @param  num_sem numero de semaforo dentro del array
 * @param  undo    flag que se quiere agregar (UNDO flag recomendable)
 * @return         ERROR en caso de error, OK si todo correcto
 */
int Down_Semaforo(int id, int num_sem, int undo){
    return operacionSemaforo(id, num_sem, undo, -1);
}

/**
 * Hace up a un semaforo
 * @param  id      identificador de array de semaforos
 * @param  num_sem numero de semaforo dentro del array
 * @param  undo    flag que se quiere agregar (UNDO flag recomendable)
 * @return         ERROR en caso de error, OK si todo correcto
 */
int Up_Semaforo(int id, int num_sem, int undo){
    return operacionSemaforo(id, num_sem, undo, 1);
}

/**
 * Funcion privada que generaliza el comportamiento de DownMultiple_Semaforo y
 * UpMultiple_Semaforo. Se le pasa -1 si se quiere actuar como DownMultiple_Semaforo
 * y 1 si se quiere actuar como UpMultiple_Semaforo
 */
int operacionMultipleSemaforo(int id, int size, int undo, int *active, int op){
    int i;
    if (size < 1) return ERROR;
    for (i = 0; i < size; i++) {
        if (operacionSemaforo(id, active[i], undo, op) == ERROR) return ERROR;
    }
    return OK;
}

/**
 * Hace down sobre un conjunto de semaforos.
 * @param  id     identificador del array de semaforos
 * @param  size   tamanio del array active
 * @param  undo   flag a agregarle a la operacion
 * @param  active array con el conjunto de semaforos sobre el que se hace down
 * @return        ERROR si hubo un error al hacer down en algun semaforo, OK
 * en caso de que todo fue correctamente
 */
int DownMultiple_Semaforo(int id, int size, int undo, int *active){
    return operacionMultipleSemaforo(id, size, undo, active, -1);
}


/**
 * Hace up sobre un conjunto de semaforos.
 * @param  id     identificador del array de semaforos
 * @param  size   tamanio del array active
 * @param  undo   flag a agregarle a la operacion
 * @param  active array con el conjunto de semaforos sobre el que se hace down
 * @return        ERROR si hubo un error al hacer up en algun semaforo, OK
 * en caso de que todo fue correctamente
 */
int UpMultiple_Semaforo(int id, int size, int undo, int *active){
    return operacionMultipleSemaforo(id, size, undo, active, 1);
}
