#!/usr/bin/env python3

import os, sys, time, subprocess, shlex, select, logging, fileinput
import RPi.GPIO as GPIO
from datetime import datetime
import paho.mqtt.client as mqtt


#ORIGINALS
log_file = "/home/pi/test.log"
appdef = "/home/pi/SmartSense/appdef"
net_faces = "/etc/network/interfaces"
#BACKUPS
appdef_backup = "/home/pi/SmartSense/appdef_backup"
net_faces_backup = "/etc/network/interfaces_backup"

logging.basicConfig(filename=log_file, level=logging.DEBUG)

mbmb_power_pin = 11
mbmb_reset_pin  =13
mbmb_hard_power_pin = 15

global gps_coords


GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(mbmb_reset_pin, GPIO.OUT)
GPIO.setup(mbmb_power_pin, GPIO.OUT)
GPIO.setup(mbmb_hard_power_pin, GPIO.OUT)

def modem_power_off():
	GPIO.output(mbmb_power_pin, False)
	time.sleep(1)
	GPIO.output(mbmb_power_pin, True)
	time.sleep(2)
	GPIO.output(mbmb_power_pin, False)
	time.sleep(1)
	GPIO.output(mbmb_hard_power_pin, False)
	return

def modem_power_on():
	GPIO.output(mbmb_hard_power_pin, True)
	time.sleep(1)
	GPIO.output(mbmb_power_pin, True)
	time.sleep(1)
	GPIO.output(mbmb_power_pin, False)
	time.sleep(0.18)
	GPIO.output(mbmb_power_pin, True)
	return
def modem_reset():
	GPIO.output(mbmb_reset_pin, True)
	time.sleep(1)
	GPIO.output(mbmb_reset_pin, False)
	time.sleep(0.1)
	GPIO.output(mbmb_reset_pin, True)
	return

'''
just run process and return stdout.
This is blocking
'''
def run_shell_process(cmd):
	try:
		output = subprocess.check_output(
			cmd, shell=True,stderr=subprocess.STDOUT
			)
	except Exception as err:
		print("cmd %s FAILED %r" %(cmd, err))
		return str(err)
	return output.decode(encoding="utf-8", errors="ignore").rstrip()


def on_connect(client, userdata, rc):
    mqtt_subscribe(client)

def on_message(client, userdata, msg):
    process_mqtt_message(msg)

def on_publish(client, userdata, mid):
    return

def mqtt_subscribe(client):
    client.subscribe("smartcity/data/0/GPS/+")    
    return

def process_mqtt_message(msg):
	global gps_coords
	msg = msg.payload.decode('utf8').split(',')
	logging.debug(msg[0] + " " + msg[2])
	print(str(msg[0] + " " + msg[2]))
	if float(msg[0]) > 1 and float(msg[2]) > 1:
		gps_coords = gps_coords + 1
		if gps_coords > 3:
			logging.debug("Test is over")
			do_cleanup()


def disable_nmag():
	logging.debug("Disabling nmag in appdef")
	for line in fileinput.input(appdef, inplace=True):
		print(line.rstrip().replace('nmag:', '#nmag:'))
	
	logging.debug("nmag is disabled")


def check_reset_counter():
	result = run_shell_process("sudo uboot_env -n reset_counter | grep  -oE  '[[:digit:]]'")
	return result

def check_is_nmag_enabled():
	logging.debug("Parsing appdef to see if nmag is enabled")
	
	with open(appdef) as f:
		for line in f.readlines():
			if "#nmag" in line:
				return False
	return True

def enable_wifi_auto():
	logging.debug("Setting wifi auto mode")
	
	with open(net_faces, 'r+') as f:
		for line in f.readlines():
			if "iface eth0 inet dhcp" in line:
				f.write("\n auto wlan0")

def check_file_exists(file):
	return os.path.exists(file)


def do_cleanup():
	logging.debug('GPS working at %s' % (datetime.now()))
	quit()

if __name__ == "__main__":
	run_shell_process("sudo mount -o remount rw /")
	logging.debug("Starting gps location test")

	gps_coords = 0

	#if it is first time starting, make backups
	if check_file_exists(appdef_backup):
		pass
	else:
		logging.debug("Making backup of %s" % appdef)
		run_shell_process("sudo cp %s %s" % (appdef, appdef_backup))

	if check_file_exists(net_faces_backup):
		pass
	else:
		logging.debug("Making backup of %s" % net_faces)
		run_shell_process("sudo cp %s %s" % (net_faces, net_faces_backup))

	#Mount partition as rw
	logging.debug("Mounting partition as read/write")
	run_shell_process("sudo mount -o remount rw /")
	logging.debug("Done")
	#check if nmag is disabled
	result = check_is_nmag_enabled()
	logging.debug("Done")
	if  result:
		disable_nmag()
		enable_wifi_auto()
		#run_shell_process("sudo reboot")
	else:
		# if nmag is disabled then this must be second iteration
		#  return it to zero for simplicity
		if check_reset_counter() == 4:
			run_shell_process("sudo uboot_env -n reset_counter -v 0")

	temp = 0
	while temp <2:
		modem_power_off()
		logging.debug("Modem powered off")
		modem_power_on()
		logging.debug("Modem powered on")
		modem_reset()
		logging.debug("Modem reset")
		temp = temp + 1
		if temp == 0:
			time.sleep(2*60)

	# MQTT Parameters
	broker_address = "127.0.0.1"
	broker_port = 1883 
       
	mqttc = mqtt.Client()
	mqttc.on_connect = on_connect
	mqttc.on_message = on_message
	mqttc.on_publish = on_publish
	mqttc.connect(broker_address, port=broker_port, keepalive=60)

	mqttc.loop_start()
	
	start_time = datetime.now()
	logging.debug('Modem reset at %s' %  str(start_time))

	while True:
		time.sleep(50000)
