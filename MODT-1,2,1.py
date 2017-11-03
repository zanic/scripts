#!/usr/bin/env python3

import os, sys, time, subprocess, shlex, logging
from datetime import datetime
from collection import OrderedDict


logging.basicConfig(filename=log_file, level=logging.DEBUG)
log = logging.getLogger('Tester')

mbmb_power_pin = 11
mbmb_reset_pin  =13
mbmb_hard_power_pin = 15

coord_dict = OrderedDict()

timestamp_begin = datetime.now()
timestamp_end = datetime.now()

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
		if len(coord_dict) > 100:
			end_test()

def start_test():
	log.info("Starting test")
	test_run_state = True
	timestamp_begin = datetime.now()
	dict_run_times[test_run_state] = timestamp_begin
	log.info("Test started with time: " + timestamp_begin.strftime('%d.%m.%Y %H:%M:%S'))
	while test_run_state != False:
		time.sleep(10)
	return 

def end_test():
	log.info("Stoping test")
	test_run_state = False
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

if __name__ == "__main__":

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
	start_test()