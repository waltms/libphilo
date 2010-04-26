# $Id: Makefile.in,v 2.11 2004/05/28 19:22:06 o Exp $
LDFLAGS= 
CFLAGS= -O3
CPPFLAGS= 
LDFLAGS= 
PH_CFLAGS= -I./unpack -D_REENTRANT -fomit-frame-pointer -funroll-all-loops -finline-functions
CC= gcc
PH_BUILDENV = 
PH_LDSEARCHFLAGS = 

all: 	search4	libphilo.so

search4: search4.c search.o retreive.o gmap.o word.o blockmap.o level.o out.o log.o plugin/libindex.a db/db.o db/bitsvector.o db/unpack.o
	$(PH_BUILDENV) $(CC) $(CFLAGS) $(CPPFLAGS) $(PH_CFLAGS) $(LDFLAGS) $(PH_LDSEARCHFLAGS) search4.c search.o retreive.o gmap.o word.o blockmap.o level.o out.o log.o db/db.o db/bitsvector.o db/unpack.o plugin/libindex.a -lgdbm -o search4

db/db.o:  db/db.c db/db.h db/bitsvector.c db/bitsvector.h
	(cd db; make db.o)

db/bitsvector.o: db/bitsvector.c db/bitsvector.h
	(cd db; make bitsvector.o)

db/unpack.o: db/unpack.c db/unpack.c db/bitsvector.c db/bitsvector.h db/db.c db/db.h
	(cd db; make unpack.o)

plugin/libindex.a:	plugin
	(cd plugin; make libindex.a)

gmap.o:		gmap.h gmap.c c.h

word.o:		word.h word.c c.h

level.o:	level.h blockmap.h gmap.h word.h level.c c.h

blockmap.o:	blockmap.h blockmap.c level.h word.h search.h c.h

search.o:	search.c blockmap.h blockmap.c level.h word.h search.h c.h

out.o:		out.h out.c

log.o:		log.h log.c

install:	all
	/usr/bin/install -c search4 ${exec_prefix}/bin

clean: 
	rm -f *.o *~ search4
	(cd plugin; make clean)
	(cd db; make clean)