LIBS=-Wall -ggdb -pedantic  

all: main
	rm -f *.o

main: main.o semaforos.o config.o server.o picohttpparser.o http_service.o
	gcc $(LIBS) -o server $^ -lconfuse

picohttpparser.o: src/picohttpparser.c includes/picohttpparser.h
	gcc $(LIBS) -c src/picohttpparser.c 
	
config.o: src/config.c includes/config.h
	gcc $(LIBS) -c src/config.c

http_service.o: src/http_service.c includes/http_service.h
	gcc $(LIBS) -c src/http_service.c

main.o: src/main.c
	gcc $(LIBS) -c src/main.c

server.o: src/server.c includes/server.h
	gcc $(LIBS) -c src/server.c

semaforos.o: src/semaforos.c includes/semaforos.h
	gcc $(LIBS) -c src/semaforos.c


clean:
	rm -f *.o server
