import proxy
from pymomo.commander.exceptions import *
from pymomo.commander.types import *
from pymomo.commander.cmdstream import *
from pymomo.utilities.console import ProgressBar
import struct
from intelhex import IntelHex
from time import sleep

class MIBController (proxy.MIBProxyObject):
	MaxModuleFirmwares = 4

	def __init__(self, stream):
		super(MIBController, self).__init__(stream, 8)
		self.name = 'Controller'

	def reset_bus(self, sync=True):
		"""
		Cycle power on all attached momo modules except the controller.
		The count of attached modules is also reset to zero in anticipation
		of the modules reregistering
		"""

		res = self.rpc(42, 5)

		if sync:
			sleep(1.5)

	def count_modules(self):
		"""
		Count the number of attached devices to this controller
		"""

		res = self.rpc(42, 1, result_type=(1, False))
		return res['ints'][0]

	def reflash(self):
		try:
			self.rpc(42, 0xA)
		except RPCException as e:
			if e.type != 7:
				raise e

	def describe_module(self, index):
		"""
		Describe the module given its module index
		"""
		res = self.rpc(42, 2, index, result_type=(0,True))

		return ModuleDescriptor(res['buffer'], 11+index)

	def get_module(self, by_name=None, by_address=None, force=False):
		"""
		Given a module name or a fixed address, return a proxy object
		for that module if it is connected to the bus.  If force is True
		this call will construct an proxy object for the given address even
		if the module is not found in the controller's database of connected
		modules.
		"""

		if by_address is not None and force:
			obj = proxy.MIBProxyObject(self.stream, by_address)
			obj.name = 'Unknown'
			return obj

		mods = self.enumerate_modules()
		if by_name is not None and len(by_name) < 7:
			by_name += (' '*(7 - len(by_name)))

		for mod in mods:
			if by_name == mod.name or by_address == mod.address:
				obj = proxy.MIBProxyObject(self.stream, mod.address)
				obj.name = mod.name
				return obj

		raise ValueError("Could not find module by name or address (name=%s, address=%s)" % (str(by_name), str(by_address)))

	def enumerate_modules(self):
		"""
		Get list of all attached modules and describe them all
		"""
		
		num = self.count_modules()

		mods = []

		for i in xrange(0, num):
			mods.append(self.describe_module(i))

		return mods

	def _encode_firmware_line(self, line):
		if line[0] != ':':
			raise ValueError("Invalid hex line, did not start with a ':': %s" % line)

		line = line[1:]

		cnt = int(line[0:2], 16)
		addr = int(line[2:6], 16)
		rec = int(line[6:8], 16)

		if cnt > 16:
			raise ValueError("Cannot use hex file with more than 16 bytes per line. Line size was %d." % cnt)

		datahex = line[8:8+2*cnt]
		chk = int(line[8+2*cnt:8+2*cnt+2], 16)

		data = bytearray(cnt)
		for i in xrange(0, cnt):
			data[i] = int(datahex[2*i:2*i+2], 16)

		packed = struct.pack('HB%dB' % cnt, addr, rec, *data)
		return bytearray(packed)

	def push_firmware(self, firmware, module_type, verbose=True):
		"""
		Given either a path to a hex file or an open file-like object,
		push the firmware described by the object to the controller.

		returns an integer, which is the firmware bucket that this
		firmware was pushed to.
		"""

		lines = []

		if hasattr(firmware, "readlines"):
			lines = firmware.readlines()
		elif isinstance(firmware, basestring):
			with open(firmware, "r") as f:
				lines = f.readlines()

		if len(lines) == 0:
			raise ValueError("Could not understand firmware object type.  Should be a path or a file object")


		if verbose:
			print "Sending Firmware"
			prog = ProgressBar("Transmission Progress", len(lines))
			prog.start()

		res = self.rpc(7, 0, module_type, result_type=(1, False))
		bucket = res['ints'][0]

		for i in xrange(0, len(lines)):
			buf = self._encode_firmware_line(lines[i])
			res = self.rpc(7, 1, buf)

			if verbose:
				prog.progress(i+1)

		if verbose:
			prog.end()
			print "Firmware stored in bucket %d" % bucket

		return bucket

	def pull_firmware(self, bucket, verbose=True, pic12=True):
		res, reason = self._firmware_bucket_loaded(bucket)

		if res == False:
			raise ValueError(reason)

		info = self.get_firmware_info(bucket)
		length = info['length']

		out = IntelHex()

		if verbose:
			print "Getting Firmware, size=0x%X" % length
			prog = ProgressBar("Transmission Progress", length // 20)
			prog.start()

		for i in xrange(0, length, 20):
			res = self.rpc(7, 4, bucket, i, result_type=(0, True))

			for j in range(0, len(res['buffer'])):
				out[i+j] = ord(res['buffer'][j])
				if pic12 and (j%2 != 0):
					out[i+j] &= 0x3F

			if verbose:
				prog.progress(i//20)

		if verbose:
			prog.end()

		return out

	def _firmware_bucket_loaded(self, index):
		res = self.get_firmware_count()
		mods = res['module_buckets']

		if index < 4 and index >= mods:
			return False, "Invalid firmware bucket specified, only %d buckets are filled" % mods

		if index == 4 and not res['controller_firmware']:
			return False, "Controller firmware requested and none is loaded"

		if index == 5 and not res['backup_firmware']:
			return False, "Backup firmware requested and none is loaded"

		if index > 5:
			return False, "Invalid bucket index, there are only 6 firmware buckets (0-5)."

		return True, "" 

	def get_firmware_count(self):
		"""
		Return a dictionary containing:
		- the number of module firmwares loaded
		- if there is a controller firmware loaded
		- if there is a backup controller firmware loaded
		"""

		res = self.rpc(7, 5, result_type=(2, False))
		con = res['ints'][1]

		dic = {}
		dic['module_buckets'] = res['ints'][0]
		dic['controller_firmware'] = (con&0b1 == 1)
		dic['backup_firmware'] = ((con >> 1) == 1)

		return dic

	def clear_firmware_cache(self):
		self.rpc(7, 0x0A)

	def get_firmware_info(self, bucket):
		"""
		Get the firmware size and module type stored in the indicated bucket
		"""

		res = self.rpc(7, 3, bucket, result_type=(7, False))

		length = res['ints'][1] << 16 | res['ints'][2]
		base = res['ints'][3] << 16 | res['ints'][4]
		sub_start = res['ints'][5]
		subs = res['ints'][6]

		return {'module_type': res['ints'][0], 'length': length, 'base_address': base, 'bucket_start': sub_start, 'bucket_size': subs}

	def read_flash(self, baseaddr, count, verbose=True):
		"""
		Read count bytes of the controller's external flash starting at addr.
		The flash is read 20 bytes at a time since this is the maximum mib 
		frame size.
		"""

		if baseaddr >= 1024*1024:
			raise ValueError("Address too large, flash is only 1MB in size")

		buffer = bytearray()

		if verbose:
			prog = ProgressBar("Reading Flash", count)
			prog.start()

		for i in xrange(0, count, 20):
			if verbose:
				prog.progress(i)

			addr = baseaddr + i
			addr_low = addr & 0xFFFF
			addr_high = addr >> 16

			length = min(20, count-i)

			res = self.rpc(42, 3, addr_low, addr_high, result_type=(0, True))
			buffer.extend(res['buffer'][0:length])

		if len(buffer) != count:
			raise RuntimeError("Unknown error in read_flash, tried to read %d bytes, only read %d" % (count, len(buffer)))

		if verbose:
			prog.end()

		return buffer

	def write_flash(self, baseaddr, buffer, verbose=True):
		"""
		Write all of the bytes in buffer to the controller's external flash starting at baseaddr
		"""

		count = len(buffer)

		if baseaddr >= 1024*1024:
			raise ValueError("Address too large, flash is only 1MB in size")

		if verbose:
			prog = ProgressBar("Writing Flash", count)
			prog.start()

		i = 0
		while i < count:
			if verbose:
				prog.progress(i)

			addr = baseaddr + i
			addr_low = addr & 0xFFFF
			addr_high = addr >> 16

			length = min(14, count-i)		
			res = self.rpc(42, 4, addr_low, addr_high, buffer[i:i+length], result_type=(2, False))

			written_addr = res['ints'][0] | (res['ints'][1] << 16)

			if written_addr != addr:
				raise RuntimeError("Tried to write to address 0x%X but wrote to address 0x%X instead" % (addr, written_addr))

			i += length

		if verbose:
			prog.end()

	def erase_flash(self, addr):
		if addr >= 1024*1024:
			raise ValueError("Address too large, flash is only 1MB in size")

		addr_low = addr & 0xFFFF
		addr_high = addr >> 16

		res = self.rpc(42, 6, addr_low, addr_high)

	def alarm_asserted(self):
		"""
		Query the field service unit if the alarm pin on the bus is asserted.  Returns True if 
		the alarm is asserted (low value since it's active low).  Returns False otherwise
		"""

		resp, result = self.stream.send_cmd("alarm status")
		if result != CMDStream.OkayResult:
			raise RuntimeError("Alarm status command failed")

		resp = resp.lstrip().rstrip()
		val = int(resp)

		if val == 0:
			return True
		elif val == 1:
			return False
		else:
			raise RuntimeError("Invalid result returned from 'alarm status' command: %s" % resp)


	def set_alarm(self, asserted):
		"""
		Instruct the field service unit to assert or deassert the alarm line on the MoMo bus.
		"""

		if asserted:
			arg = "yes"
		else:
			arg = "no"

		cmd = "alarm %s" % arg

		resp, result = self.stream.send_cmd(cmd)
		if result != CMDStream.OkayResult:
			raise RuntimeError("Set alarm command failed")
