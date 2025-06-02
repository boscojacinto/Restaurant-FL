SHELL := bash

GOCMD ?= $(shell which go)

.PHONY: all build dynamic-library

all: build

deps: lint-install

vendor:
	${GOCMD} mod tidy

generate:
	${GOCMD} generate ./...

dynamic-library:
	@echo "Building shared library..."
	rm -f ./build/lib/libconsensus.so
	CGO_LDFLAGS="-Wl,-soname,libconsensus.so.0" ${GOCMD} build \
		-buildmode=c-shared \
		-o ./build/lib/libconsensus.so \
		./consensus
	sed -i "s/#include <cgo_utils.h>//gi" ./build/lib/libconsensus.h

	cd ./build/lib && \
	mv ./libconsensus.so ./libconsensus.so.0 && \
	ln -s ./libconsensus.so.0 ./libconsensus.so
	@echo "Shared library built:"
	@ls -la ./build/lib/libconsensus.*