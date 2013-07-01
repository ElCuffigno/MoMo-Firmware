#include "bus_slave.h"
#include "test.h"
#include <string.h>

extern volatile unsigned char 	mib_buffer[kBusMaxMessageSize];

void* test_command(MIBParamList *param)
{
	_RA1 = !_RA1; //Blink light
	
	MIBIntParameter *retval;

	bus_free_all();

	retval = (MIBIntParameter*)bus_allocate_int_param();

	bus_init_int_param(retval, 6);
	bus_slave_setreturn(kNoMIBError, (MIBParameterHeader*)retval);

	return NULL;
}

void* echo_buffer(MIBParamList *list)
{
	MIBBufferParameter *buf = (MIBBufferParameter *)list->params[0];
	bus_free_all();

	memmove((void*)mib_buffer, buf, 2);
	memmove((void*)mib_buffer+2, buf->data, buf->header.len);

	bus_slave_setreturn(kNoMIBError, (MIBParameterHeader*)mib_buffer);

	return NULL;
}