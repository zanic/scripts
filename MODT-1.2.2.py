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
	global test_run_state
	if test_run_state:
		if float(msg[0]) > 0.15 and float(msg[2]) > 0.15:
			coord_dict[datetime.now()] = str(msg[0]) + ":" + str(msg[2])
			if len(coord_dict) > 10:
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
	edit_report()

def edit_report():
	log.info ("Editing report")
	times = []
	diff = []
	lat = []
	lon = []
	formated_line = []
	with open(report_file, 'r') as f:
		log.info("Report_file read")
		lines = f.readlines()
		for index, line in enumerate(lines):
			log.info("We are here in enumerating")
			log.info(str(index))
			time  = (line.split(' ')[1]).rstrip(':')
			splitted = line.split(' ')
			time_y = splitted[0]
			time_h = splitted[1]
			lat = (((lines[-1].split(','))[0])[0:5])
			#lat.append(((lines[-1].split(':'))[0])[0:5])
			#lon.append(((lines[0].split(':'))[0])[0:5])
			lon = (((lines[-1].split(','))[0])[0:5])
			time = splitted[0] +  ' ' + splitted[1].rstrip(':')
			time = datetime.strptime(time, '%Y-%m-%d  %H:%M:%S.%f')
			times.append(time)
			formated_line.append(str(time) + lat + ',' + lon)
		log.info("Done reading")
	log.info("Enumerating")
	for index, time in enumerate(times):
		try:
			diff.append((times[index+1] - times[index]).total_seconds())
		except IndexError as e:
			log.err("Error with %r" % e) 
	log.info ("Writing new report file")
	with open('report', 'w') as report_f:
		i = 0
		for line in formated_line:
			print (line)
			if i > 0:
				report_f.write((line.rstrip('\n') + ' ' + str(diff[i]) + '\n'))
			i = i +1
	coord_dict.clear()
	exit()

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

	start_test()