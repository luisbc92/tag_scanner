#!/usr/bin/env python
# coding=utf-8
__author__  = "Luis Carlos Bañuelos Chacon"
__license__ = "TBD"
__version__ = "06/01/2015"
__email__   = "luiscarlos.banuelos@gmail.com"

import bglib, serial, re, time

# Configuration
BLE_PORT = "/dev/ttyACM0"
BLE_BAUD = 115200
XBEE_PORT = "/dev/ttySER0"
XBEE_BAUD = 9600

ser_ble  = serial.Serial(BLE_PORT, BLE_PORT, timeout = 1)
xbee_ble = serial.Serial(XBEE_PORT, XBEE_BAUD, timeout = 1)

tag_discovered = []     # MAC addresses of identified tags
tag_data = []           # data collected from tags

# function to enter xbee command mode
def xbee_atmode(ser):
    time.sleep(1)                   # guard time
    ser.write("+++")                # enter AT
    time.sleep(1)                   # guard time
    if (xbee_read(ser) == "OK\r"):  # get confirmation
        return True
    else:
        return False

# function to read xbee command responses
def xbee_read(ser):
    eol = b'\r'
    leneol = len(eol)
    line = bytearray()
    while True:
        c = ser.read(1)
        if c:
            line += c
            if line[-leneol:] == eol:
                break
        else:
            break
    return bytes(line)

# function to get MAC address of a network interface (Linux only)
def get_mac(interface):
    # get mac address as string
    try:
        mac = open("/sys/class/net/%s/address" %interface).readline()
    except:
        mac = "00:00:00:00:00:00"
    # separate tokens and return
    return mac.rstrip().split(':')

# handler to notify of an API parser timeout condition
def ble_parser_timeout(sender, args):
    print "BGAPI parser timed out."

# handler to catch scan responses
def ble_evt_gap_scan_response(sender, args):
    global tag_data
    global tag_discovered

    # get advertisement packet and look for tags
    if (args["packet_type"] == 0):                          # 0 - connecteable advertisement packet
        ble_name = ''.join("%c" %c for c in args["data"])   # convert all data into a string to extract name (lazy)
        ble_name = re.sub(r"\W+", "", ble_name)             # remove everything but characters (even more lazy)
        if (ble_name.find("TAG") == 0):                     # if name begins with "TAG"
            if not (args["sender"] in tag_discovered):      # and it has not already been discovered
                tag_discovered.append(args["sender"])       # add MAC address into list
                print "Discovered TAG: " + ble_name

    # get scan response packet and extract data
    # packet structure (30 bytes)
    # byte 0    = packet length (ignored)
    # byte 1    = packet type   (ignored)
    # byte 2-28 = data payload
    # byte 29   = packet count  (used to identify retransmitted packets)
    rx = {}
    if (args["packet_type"] == 4 and args["sender"] in tag_discovered and len(args["data"]) == 30): # it has to be 30 bytes
        if not any(args["data"][29] == p["count"] and args["sender"] == p["mac"] for p in tag_data): # discard if packet is a retransmission
            rx["mac"]   = args["sender"]                    # MAC address
            rx["count"] = args["data"][29]                  # byte 29 is packet count
            rx["rssi"]  = args["rssi"]                      # RSSI
            rx["data"]  = args["data"][2:29]                # data payload
            tag_data.append(rx)                             # append received packet
            print rx

# function to prepare packet for transmission
def create_packet():
    global tag_data

    mac = get_mac("eth0")                               # obtain mac address
    packet = {"ant_mac": mac, "tag_data": tag_data}     # join antenna mac address and collected data
    return packet


def main():
    global tag_data

    # welcome message
    print "-----Tag Scanner-----"

    # create BGLib object
    ble = bglib.BGLib()
    ble.packet_mode = False

    # add handler for BGAPI timeout condition
    ble.on_timeout += ble_parser_timeout

    # add handler for gap_scan_response event
    ble.ble_evt_gap_scan_response += ble_evt_gap_scan_response

    # flush serial buffers
    ser_ble.flushInput()
    ser_ble.flushOutput()

    # disconnect if connected already
    ble.send_command(ser_ble, ble.ble_cmd_connection_disconnect(0))
    ble.check_activity(ser_ble, 1)

    # stop advertising if advertising already
    ble.send_command(ser_ble, ble.ble_cmd_gap_set_mode(0, 0))
    ble.check_activity(ser_ble, 1)

    # set scan parameters (scan_interval, scan_window, active)
    ble.send_command(ser_ble, ble.ble_cmd_gap_set_scan_parameters(0xC8, 0xC8, 1))
    ble.check_activity(ser_ble, 1)

    # start scanning now (mode)
    ble.send_command(ser_ble, ble.ble_cmd_gap_discover(1))
    ble.check_activity(ser_ble, 1)

    while (1):
        # check for all incoming data (no timeout, non-blocking)
        ble.check_activity(ser_ble)

        if (len(tag_data) > 10):
            print create_packet()
            tag_data = []

        time.sleep(0.01)

if __name__ == '__main__':
    main()
