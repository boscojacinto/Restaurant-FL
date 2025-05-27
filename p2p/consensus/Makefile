SHELL := bash

GOCMD ?= $(shell which go)

.PHONY: all build dynamic-library

all: build

deps: lint-install

build:
	${GOCMD} build -o build/waku ./cmd/waku

vendor:
	${GOCMD} mod tidy

generate:
	${GOCMD} generate ./...

dynamic-library:
	@echo "Building shared library..."
	rm -f ./build/lib/libgosync.so
	CGO_LDFLAGS="-Wl,-soname,libgosync.so.0" ${GOCMD} build \
		-buildmode=c-shared \
		-o ./build/lib/libgosync.so \
		./
	sed -i "s/#include <cgo_utils.h>//gi" ./build/lib/libgosync.h

	cd ./build/lib && \
	mv ./libgosync.so ./libgosync.so.0 && \
	ln -s ./libgosync.so.0 ./libgosync.so
	@echo "Shared library built:"
	@ls -la ./build/lib/libgosync.*