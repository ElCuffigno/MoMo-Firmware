
#include "platform.h"

//Global State Types
typedef union 
{
	struct
	{
		volatile uint8 module_on;
		volatile uint8 shutdown_pending;
		volatile uint8 unused:6;
	};

	volatile uint8 gsm_state;
} ModuleState;

#ifndef DEFINE_STATE
#define prefix extern
#else
#define prefix
#endif

//GSM Serial Communication Buffer
#define TX_BUFFER_LENGTH 20
prefix uint8 gsm_buffer[TX_BUFFER_LENGTH];
prefix uint8 buffer_len;

#define RX_BUFFER_LENGTH 20
prefix uint8 gsm_rx_buffer[RX_BUFFER_LENGTH];
prefix uint8 rx_buffer_start;
prefix uint8 rx_buffer_end;
prefix uint8 rx_buffer_len;

//GSM Module Status
prefix ModuleState state;
