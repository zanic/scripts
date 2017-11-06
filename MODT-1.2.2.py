#!/usr/bin/env python3

import os, sys, time, logging, re
from datetime import datetime
from collections import OrderedDict
import paho.mqtt.client as mqtt

report_file = 'MODT-1.2.2.txt'
log_file = 'test.log'
#logging.basicConfig(filename=log_file, level=logging.DEBUG)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
log = logging.getLogger('Tester')


coord_dict = OrderedDict()
dict_run_times = {}
global timestamp_begin
global timestamp_end
timestamp_begin = datetime.now()
timestamp_end = datetime.now()
global test_run_state


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
	global test_run_state
	global timestamp_begin
	test_run_state = True
	log.info("Starting test")
	timestamp_begin = datetime.now()
	dict_run_times[test_run_state] = timestamp_begin
	log.info("Test started with time: " + timestamp_begin.strftime('%d.%m.%Y %H:%M:%S'))
	while test_run_state != False:
		time.sleep(0.1)
	return 

def end_test():
	log.info("Stoping test")
	global test_run_state
	global timestamp_end
	test_run_state = False
	coord_dict.clear()
	timestamp_end = datetime.now()
	log.info("Test ended with time: " + timestamp_end.strftime('%d.%m.%Y %H:%M:%S'))
	make_report()

def make_report():
	global timestamp_begin
	global timestamp_end
	log.info("Making report")
	with open(report_file, 'a') as f:
		for key, value in coord_dict.items():
			f.write(str(key) + ": " + str(value) + '\n')
	return


if __name__ == "__main__":

	global test_run_state
	test_run_state = True


	logging.debug("Starting MODT-1.2.2")

	# MQTT Parameters
	broker_address = "127.0.0.1"
	broker_port = 1883 
       
	mqttc = mqtt.Client()
	mqttc.on_connect = on_connect
	mqttc.on_message = on_message
	mqttc.on_publish = on_publish
	mqttc.connect(broker_address, port=broker_port, keepalive=60)

	mqttc.loop_start()

	while True:
		time.sleep(1000)