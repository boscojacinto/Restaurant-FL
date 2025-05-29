package main

/*
#include <stdlib.h>
#include <cgo_utils.h>
extern void _consensus_execCB(ConsensusCallBack cb, int retCode, char* msg, void* user_data);
*/
import "C"
import (
	"errors"
	"unsafe"

	//"github.com/waku-org/go-waku/library"
)

const ret_ok = 0
const ret_err = 1
const ret_cb = 2

var errMissingCallback = errors.New("missing callback")

/*func onSuccesfulResponse(value string, cb C.WakuCallBack, userData unsafe.Pointer) C.int {
	retCode := ret_ok
	if cb == nil {
		retCode = ret_cb
		value = errMissingCallback.Error()
	}

	cstrVal := C.CString(value)
	C._waku_execCB(cb, C.int(retCode), cstrVal, userData)

	C.free(unsafe.Pointer(cstrVal))

	return ret_ok
}*/

func onError(err error, cb C.ConsensusCallBack, userData unsafe.Pointer) C.int {
	retCode := ret_err
	if cb == nil {
		retCode = ret_cb
		err = errMissingCallback
	}

	if err != nil {
		errMsg := err.Error()
		cstrVal := C.CString(errMsg)
		C._consensus_execCB(cb, C.int(retCode), cstrVal, userData)
		C.free(unsafe.Pointer(cstrVal))
		return ret_err
	}

	retCode = ret_ok
	C._consensus_execCB(cb, C.int(retCode), nil, userData)
	return ret_ok
}

/*func getInstance(consensusCtx unsafe.Pointer) (*ConsensusInstance, error) {
	pid := (*uint)(consensusCtx)
	if pid == nil {
		return nil, errors.New("invalid consensus context")
	}

	return GetInstance(*pid)
}
*/