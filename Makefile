# Build the x264 ctypes shim against the CARC x264 module.
# Usage:  source env.sh && make
X264_ROOT ?= $(error X264_ROOT not set: run "source env.sh" first)

CC      ?= gcc
CFLAGS  += -O2 -fPIC -Wall -Wextra -std=c11 -I$(X264_ROOT)/include
LDFLAGS += -shared -L$(X264_ROOT)/lib -Wl,-rpath,$(X264_ROOT)/lib
LDLIBS  += -lx264

LIB := build/libx264shim.so

all: $(LIB)

$(LIB): encoder_shim.c | build
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $< $(LDLIBS)

build:
	mkdir -p build

clean:
	rm -rf build

.PHONY: all clean
