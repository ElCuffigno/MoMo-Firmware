#include <stdio.h>
#include <stdlib.h>
#include <p24F16KA101.h>


//Write to memory
void mem_write(int val);
long mem_read();
void configure_SPI();
static unsigned char TX_BUF[140];
static unsigned long last_wrote;
static unsigned long last_read;
