from pymomo.commander import transport, cmdstream
from pymomo.commander.proxy import *
from pymomo.commander.exceptions import *

import serial
from serial.tools import list_ports
import re

def get_controller(serial_port=None):
	"""
	Given serial port descriptor, create all of the necessary
	object to get a controller proxy module 
	"""

	if serial_port == None:
		serial_port = find_momo_serial()
		if serial_port == None:
			raise InitializationException( "No port specified and no valid USB device detected." )

	s = transport.SerialTransport(serial_port)
	c = cmdstream.CMDStream(s)

	con = MIBController(c)
	return con

def find_momo_serial():
	"""
	Iterate over all connected COM devices and return the first
	one that matches FTDI's Vendor ID (403)
	"""
	for port, desc, hwid in sorted( list_ports.comports() ):
		if re.match( r"USB VID:PID=403:(\d+).*", hwid) != None:
			return port