#!/usr/bin/env python
# coding=utf-8
__author__ = "Luis Bañuelos"
__license__ = "MIT"
__version__ = "2015-05-28"
__email__ = "luiscarlos.banuelos@gmail.com"

import bglib, serial, time, datetime

# handler to notify of an API parser timeout condition
def ble_parser_timeout(sender, args):
	print "BGAPI parser timed out."

# handler to catch scan responses
def ble_evt_gap_scan_response(sender, args):
	if (args["packet_type"] == 4):
		disp = []
		disp.append("%s" % ''.join(['%02X' % b for b in args["sender"][::-1]]))
		disp.append("%d" % args["rssi"])
		disp.append("%s" % ''.join(['%02X' % b for b in args["data"][::-1]]))
		print ' '.join(disp)

def main():
	# port configuration
	port_name = "/dev/ttyACM0"
	baud_rate = 115200
	packet_mode = False

	# create BGLib object
	ble = bglib.BGLib()
	ble.packet_mode = packet_mode

	# add handler for BGAPI timeout condition
	ble.on_timeout += ble_parser_timeout

	# add handler for gap_scan_response event
	ble.ble_evt_gap_scan_response += ble_evt_gap_scan_response

	# create serial port object and flush buffers
	ser = serial.Serial(port=port_name, baudrate=baud_rate, timeout = 1)
	ser.flushInput()
	ser.flushOutput()

	# disconnect if connected already
	ble.send_command(ser, ble.ble_cmd_connection_disconnect(0))
	ble.check_activity(ser, 1)

	# stop advertising if advertising already
	ble.send_command(ser, ble.ble_cmd_gap_set_mode(0, 0))
	ble.check_activity(ser, 1)

	# set scan parameters (scan_interval, scan_window, active)
	ble.send_command(ser, ble.ble_cmd_gap_set_scan_parameters(0xC8, 0xC8, 1))
	ble.check_activity(ser, 1)

	# start scanning now (mode)
	ble.send_command(ser, ble.ble_cmd_gap_discover(1))
	ble.check_activity(ser, 1)

	while (1):
		# check for all incoming data (no timeout, non-blocking)
		ble.check_activity(ser)

		time.sleep(0.01)

if __name__ == '__main__':
	main()
