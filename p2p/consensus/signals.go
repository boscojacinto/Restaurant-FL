package main

/*
#include <stddef.h>
#include <stdbool.h>
#include <stdlib.h>
extern bool ConsensusSendSignal(void *cb, const char *jsonEvent);
*/
import "C"

import (
	"encoding/json"
	"fmt"
	"unsafe"
)

func send(instance *ConsensusInstance, eventType string, event interface{}) {
	signal := SignalData{
		Type: eventType,
		Event: event,
	}
	data, err := json.Marshal(signal)
	if err != nil {
		fmt.Println("marshal signal error", err)
		return
	}

	dataStr := string(data)

	str := C.CString(dataStr)
	C.ConsensusSendSignal(instance.cb, str)
	C.free(unsafe.Pointer(str))
}
