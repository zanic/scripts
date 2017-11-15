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
global timestamp_begin
global timestamp_end
timestamp_begin = datetime.now()
timestamp_end = datetime.now()
global test_run_state

report_file = test_number + '.txt'
log_file = test_number + '.log'

test_info = {
	'tester_name': tester_name, 
	'test_name': test_name, 
	'test_number': test_number,
	'timestamp_begin': 0,
	'timestamp_end': 0,
	'test_additional_data': test_additional_data,
	'test_result': test_result
}
TEST_SUCCESS = 1
TEST_FAIL = 0

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
	global test_run_state
	if float(msg[0]) > 0.15 and float(msg[2]) > 0.15:
		coord_dict[datetime.now()] = str(msg[0]) + ":" + str(msg[2])
		if len(coord_dict) > 3:
			test_run_state = False



def main():

	test_array = []

	global test_run_state
	test_run_state = True
	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BOARD)
	GPIO.setup(mbmb_reset_pinm GPIO.OUT)
	GPIO.setup(mbmb_power_pin, GPIO.OUT)
	GPIO.setup(mbmb_hard_power_pin, GPIO.OUT)

	# Mqtt parameters
	broker_address = "127.0.0.1"
	broker_port = 1883

	mqttc = mqtt.Cient()
	mqttc.on_connect = on_connect
	mqttc.on_message = on_message
	mqttc.on_publish = on_publish
	mqttc.connect(broker_address, port=broker_port, keepalive=60)
	test_info['timestamp_begin'] = test.start(log)
	if not restart_modem():
		test_array.append(TEST_FAIL)
	else:

		time_left = 5*60

		while time_left > 0:

			if test_run_state:
				time.sleep(3)
				time_left = time_left - 3

			else:
				test_array.append(TEST_SUCCESS)
				test_info['timestamp_end'] = test.end(log)
				test.make_report(log, report_file, test_info)


if __name__ == "__main__":
	main()
