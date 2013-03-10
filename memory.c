#include "memory.h"
#include "sensor.h"
//Buffer to read SPI to
static unsigned char TX_BUF[140];
static unsigned long next_free;
static unsigned long next_read;

//configure SPI
void configure_SPI() {
  SPI1CON1bits.MODE16 = 0; //communication is byte-wide
  SPI1CON1bits.MSTEN = 1; //SPI is in master mode
}

//Write a value to EEPROM
void mem_write(int val) {
  //Write to
  //Send WREN
  int timeout_ct = 0;
  int i = 0;
  //SEND val
  SPI1STATbits.SPIEN = 1;

  SPI1BUF = 0x02;
  while((SPI1STATbits.SPITBF) && timeout_ct < 1000)
    timeout_ct++; //wait while busy

  //send address bytes MSB first
  for(i = 2; i > 0; i--) { 
    SPI1BUF = (next_free > i * 8) & 0xFF;
    while((SPI1STATbits.SPITBF) && timeout_ct < 1000)
      timeout_ct++; //wait while busy
    if (timeout_ct == 1000);
      //      sends(U2, "Memory timed out on address");
  }

  //send values LSB first (because have to correspond to addresses)
  timeout_ct = 0;
  for(i = 0; i < 3; i++) { 
    SPI1BUF = val >> i * 8; 
    while((SPI1STATbits.SPITBF) && timeout_ct < 1000)
      timeout_ct++; //wait while busy
    if (timeout_ct == 1000);
      //      sends(U2, "Memory timed out on data");
  }

  //finish
  next_free++;
}

long mem_read() {
  //Write to
  //Send WREN
  int timeout_ct;
  int i = 0;
  unsigned long val = 0;
  //SEND val
  SPI1STATbits.SPIEN = 1;

  SPI1BUF = 0x02;
  while((SPI1STATbits.SPITBF) && timeout_ct < 1000)
    timeout_ct++; //wait while busy

  //send address bytes MSB first
  for(i = 2; i > 0; i--) { 
    SPI1BUF = (next_read > i * 8) & 0xFF;
    while((SPI1STATbits.SPITBF) && timeout_ct < 1000)
      timeout_ct++; //wait while busy
    if (timeout_ct == 1000);
      //      sends(U2, "Memory timed out on address");
  }

  //send values LSB first (because have to correspond to addresses)
  timeout_ct = 0;
  for(i = 0; i < 3; i++) { 
    SPI1BUF = 0; //write 0 to initiate write to SPI1BUF
    while((SPI1STATbits.SPITBF) && timeout_ct < 1000)
      timeout_ct++; //wait while busy
    if (timeout_ct == 1000);
      //      sends(U2, "Memory timed out on data");
    val = val | ((0xFF & SPI1BUF) << i * 8);
  }

  //finish
  next_read++;
  return val;
}
