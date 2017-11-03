#!/usr/bin/env python3

import os, sys, time, logging, re
from datetime import datetime
from collections import OrderedDict
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt

report_file = 'MODT-1.2.1.txt'
log_file = 'test.log'
#logging.basicConfig(filename=log_file, level=logging.DEBUG)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
log = logging.getLogger('Tester')

mbmb_power_pin = 11
mbmb_reset_pin  =13
mbmb_hard_power_pin = 15

coord_dict = OrderedDict()
dict_run_times = {}

timestamp_begin = datetime.now()
timestamp_end = datetime.now()
global test_run_state

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

def restart_modem():
	log.info("Restarting modem")
	if check_modem_exists():
		log.info("/dev/gsmmodem exists")
	else:
		log.info("/dev/gsmmodem does not exist, try getting it back")
	modem_power_off()
	time.sleep(5)
	modem_power_on()
	time.sleep(5)
	modem_reset()
	if check_modem_return():
		return True
	else:
		return False

def check_modem_return():
	log.info("Checking has modem returned")
	sleep_time = 2
	time_left = 60
	while time_left - sleep_time > 0:
		if check_modem_exists():
			log.info("Modem is back")
			return True
		else:
			time.sleep(sleep_time)
			time_left = time_left - sleep_time
	log.info("Modem has not returned")
	return False

def check_modem_exists():
	return os.path.exists("/dev/gsmmodem")

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
	match = re.search("smartcity/data/0/GPS", msg.topic)
	if match:
		msg = (msg.payload.decode('utf-8').split(','))
		process_mqtt_gps_data(msg)

def process_mqtt_gps_data(msg):
	if float(msg[0]) > 0.15 and float(msg[2]) > 0.15:
		coord_dict[datetime.now()] = str(msg[0]) + ":" + str(msg[2])
		if len(coord_dict) > 3:
			end_test()

def start_test():
	global test_run_state
	test_run_state = True
	log.info("Starting test")
	timestamp_begin = datetime.now()
	dict_run_times[test_run_state] = timestamp_begin
	log.info("Test started with time: " + timestamp_begin.strftime('%d.%m.%Y %H:%M:%S'))
	while test_run_state != False:
		time.sleep(10)
	return 

def end_test():
	log.info("Stoping test")
	global test_run_state
	test_run_state = False
	coord_dict.clear()
	timestamp_end = datetime.now()
	log.info("Test ended with time: " + timestamp_end.strftime('%d.%m.%Y %H:%M:%S'))
	make_report()

def make_report():
	log.info("Making report")
	with open(report_file, 'a') as f:
		f.write(timestamp_begin.strftime('%d.%m.%Y %H:%M:%S')
			+ " : " + timestamp_end.strftime('%d.%m.%Y %H:%M:%S') + 
			" diff=" + str((timestamp_end-timestamp_begin).total_seconds()) +
			" seconds" + "\n")
	return


if __name__ == "__main__":

	global test_run_state
	
	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BOARD)
	GPIO.setup(mbmb_reset_pin, GPIO.OUT)
	GPIO.setup(mbmb_power_pin, GPIO.OUT)
	GPIO.setup(mbmb_hard_power_pin, GPIO.OUT)

	logging.debug("Starting MODT-1.2.1")

	# MQTT Parameters
	broker_address = "127.0.0.1"
	broker_port = 1883 
       
	mqttc = mqtt.Client()
	mqttc.on_connect = on_connect
	mqttc.on_message = on_message
	mqttc.on_publish = on_publish
	mqttc.connect(broker_address, port=broker_port, keepalive=60)

	mqttc.loop_start()

	i = 0
	while i < 10:
		if not restart_modem():
			log.info("Modem has not returned")
			break
		timestamp_begin = datetime.now()
		log.info("Test started with time: " + timestamp_begin.strftime('%d.%m.%Y %H:%M:%S'))
		while test_run_state != False:
			time.sleep(10000)
