# BLE iBeaconScanner git@loxberry.woerstenfeld.de
# For LoxBerry BLE-Scanner
# 10.11.2017 22:53:00
# v0.24
# based on several other projects like
# https://github.com/adamf/BLE/blob/master/ble-scanner.py
# https://github.com/adamf/BLE/blob/master/ble-scanner.py
# https://code.google.com/p/pybluez/source/browse/trunk/examples/advanced/inquiry-with-rssi.py
# https://github.com/pauloborges/bluez/blob/master/tools/hcitool.c for lescan
# https://kernel.googlesource.com/pub/scm/bluetooth/bluez/+/5.6/lib/hci.h for opcodes
# https://github.com/pauloborges/bluez/blob/master/lib/hci.c#L2782 for functions used by lescan

# performs a simple device inquiry, and returns a list of ble advertizements 
# discovered device + RSSI

DEBUG = False

import os
import sys
import struct
import time
import bluetooth._bluetooth as bluez

LE_META_EVENT = 0x3e
LE_PUBLIC_ADDRESS=0x00
LE_RANDOM_ADDRESS=0x01
LE_SET_SCAN_PARAMETERS_CP_SIZE=7
OGF_LE_CTL=0x08
OCF_LE_SET_SCAN_PARAMETERS=0x000B
OCF_LE_SET_SCAN_ENABLE=0x000C
OCF_LE_CREATE_CONN=0x000D

LE_ROLE_MASTER = 0x00
LE_ROLE_SLAVE = 0x01

# these are actually subevents of LE_META_EVENT
EVT_LE_CONN_COMPLETE=0x01
EVT_LE_ADVERTISING_REPORT=0x02
EVT_LE_CONN_UPDATE_COMPLETE=0x03
EVT_LE_READ_REMOTE_USED_FEATURES_COMPLETE=0x04

# Advertisment event types
ADV_IND=0x00
ADV_DIRECT_IND=0x01
ADV_SCAN_IND=0x02
ADV_NONCONN_IND=0x03
ADV_SCAN_RSP=0x04


def returnnumberpacket(pkt):
    myInteger = 0
    multiple = 256
    for c in pkt:
        myInteger +=  struct.unpack("B",c)[0] * multiple
        multiple = 1
    return myInteger 

def returnstringpacket(pkt):
    myString = "";
    for c in pkt:
        myString +=  "%02x" %struct.unpack("B",c)[0]
    return myString 

def printpacket(pkt):
    for c in pkt:
        sys.stdout.write("%02x " % struct.unpack("B",c)[0])

def get_packed_bdaddr(bdaddr_string):
    packable_addr = []
    addr = bdaddr_string.split(':')
    addr.reverse()
    for b in addr: 
        packable_addr.append(int(b, 16))
    return struct.pack("<BBBBBB", *packable_addr)

def packed_bdaddr_to_string(bdaddr_packed):
    return ':'.join('%02x'%i for i in struct.unpack("<BBBBBB", bdaddr_packed[::-1]))

def hci_enable_le_scan(sock):
    try:
			hci_toggle_le_scan(sock, 0x01)
    except:
			print 'Error: Start le_scan failed -> hci Interface up? Check with "hciconfig"'
			sys.exit(1)

def hci_disable_le_scan(sock):
    hci_toggle_le_scan(sock, 0x00)

def hci_toggle_le_scan(sock, enable):
    cmd_pkt = struct.pack("<BB", enable, 0x00)
    bluez.hci_send_cmd(sock, OGF_LE_CTL, OCF_LE_SET_SCAN_ENABLE, cmd_pkt)

def hci_le_set_scan_parameters(sock, loop_count=3):
    old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

    SCAN_RANDOM = 0x01
    OWN_TYPE = SCAN_RANDOM
    SCAN_TYPE = 0x01

def parse_events(sock, loop_count=10):
    old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

    # perform a device inquiry on bluetooth device #0
    # The inquiry should last 8 * 1.28 = 10.24 seconds
    # before the inquiry is performed, bluez should flush its cache of
    # previously discovered devices
    flt = bluez.hci_filter_new()
    bluez.hci_filter_all_events(flt)
    bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )
    done = False
    results = []
    myFullList = []

    for i in range(0, loop_count):
        try:
                sock.settimeout(5)
                pkt = sock.recv(255)
        except:
                timeout_raised=1
                #print ''#'Error: 4s timeout'
        ptype, event, plen = struct.unpack("BBB", pkt[:3])
        if event == bluez.EVT_INQUIRY_RESULT_WITH_RSSI:
                i =0
        elif event == bluez.EVT_NUM_COMP_PKTS:
                i =0 
        elif event == bluez.EVT_DISCONN_COMPLETE:
                i =0 
        elif event == LE_META_EVENT:
            subevent, = struct.unpack("B", pkt[3])
            pkt = pkt[4:]
            if subevent == EVT_LE_CONN_COMPLETE:
                le_handle_connection_complete(pkt)
            elif subevent == EVT_LE_ADVERTISING_REPORT:
                num_reports = struct.unpack("B", pkt[0])[0]
                report_pkt_offset = 0
                for i in range(0, num_reports):
		
		    if (DEBUG == True):
			print "\t~----------------------------------------------------------"
		    	print "\t~UDID: ", printpacket(pkt[report_pkt_offset -22: report_pkt_offset - 6])
                    	print "\t~MAC address: ", packed_bdaddr_to_string(pkt[report_pkt_offset + 3:report_pkt_offset + 9])
                    	txpower, = struct.unpack("b", pkt[report_pkt_offset -2])
	
                    	rssi, = struct.unpack("b", pkt[report_pkt_offset -1])
                    	print "\t~RSSI:", rssi
		    # build the return string
                    Adstring = packed_bdaddr_to_string(pkt[report_pkt_offset + 3:report_pkt_offset + 9])
		    Adstring += ","
		    Adstring += returnstringpacket(pkt[report_pkt_offset -22: report_pkt_offset - 6]) 
		    Adstring += ","
		    Adstring += "%i" % returnnumberpacket(pkt[report_pkt_offset -6: report_pkt_offset - 4]) 
		    Adstring += ","
		    Adstring += "%i" % returnnumberpacket(pkt[report_pkt_offset -4: report_pkt_offset - 2]) 
		    Adstring += ","
		    Adstring += "%i" % struct.unpack("b", pkt[report_pkt_offset -2])
		    Adstring += ","
		    Adstring += "%i" % struct.unpack("b", pkt[report_pkt_offset -1])

 		    myFullList.append(Adstring)
                done = True
    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )
    return myFullList

import blescan
import sys

import bluetooth._bluetooth as bluez

dev_id = 0
try:
	sock = bluez.hci_open_dev(dev_id)

except:
	print "Error: Cannot access bluetooth device..."
    	sys.exit(1)

blescan.hci_le_set_scan_parameters(sock, 10)
blescan.hci_enable_le_scan(sock)
returnedList = blescan.parse_events(sock, 20)
mac_addr_list = []

for beacon in returnedList:
   signal = beacon.split(',')[len(beacon.split(','))-1]
   if signal != "00":
     if any(beacon.split(',')[0] in s for s in mac_addr_list):
			pass
     else:
			newbeacon = beacon.split(',')[0]+";"+beacon.split(',')[len(beacon.split(','))-1]
			mac_addr_list.append(newbeacon)

if len(mac_addr_list) > 0:
	mac_addr_list.sort()
	for beacon in mac_addr_list:
 		print(beacon)
	sys.exit(0)	

returnedList  = "";
returnedList  = blescan.parse_events(sock, 20)

for beacon in returnedList:
   signal = beacon.split(',')[len(beacon.split(','))-1]
   if signal != "00":
     if any(beacon.split(',')[0] in s for s in mac_addr_list):
			pass
     else:
			newbeacon = beacon.split(',')[0]+";"+beacon.split(',')[len(beacon.split(','))-1]
			mac_addr_list.append(newbeacon)


if len(mac_addr_list) > 0:
	mac_addr_list.sort()
	for beacon in mac_addr_list:
 		print(beacon)
	sys.exit(0)	
else:
  print("Error: Nothing found after 2 scans, giving up...")

sys.exit(0)	