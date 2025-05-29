#include <stdlib.h>
#include <stdint.h>

typedef void (*ConsensusCallBack) (int ret_code, const char* msg, void * user_data);