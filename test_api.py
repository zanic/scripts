#!/usr/bin/env python3

import sys, re, logging, time, subprocess
from datetime import datetime
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
from dict_base import test_dict

class Test_case(object):

	net_config = "/etc/network/interfaces"
	appdef = "/home/pi/SmartSense/appdef"
	appdef_test_line = "testcase:/home/pi/:./testcase_script.py :pi:no"
	backup_dir = "/home/pi/backup_dir/"
	mqtt_broker = "localhost"
	mqtt_broker_port = 1883
	mbmb_power_pin = 11
	mbmb_reset_pin  =13
	mbmb_hard_power_pin = 15

	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BOARD)
	GPIO.setup(mbmb_reset_pin, GPIO.OUT)
	GPIO.setup(mbmb_power_pin, GPIO.OUT)
	GPIO.setup(mbmb_hard_power_pin, GPIO.OUT)

	def __init__(self, name):
		self.name = name
		self.dut = test_dict[self.name]['dut']
		self.connection = test_dict[self.name]['connection']
		self.nmag = test_dict[self.name]['nmag']

	def init_mqtt(self):
		self.mqtt = mqtt.Client()
		self.mqtt.on_connect = self.on_connect
		self.mqtt.on_message = self.on_message
		self.mqtt.on_publish = self.on_publish
		self.mqtt.connect(self.mqtt_broker, port=self.mqtt_broker_port, keepalive=60)
		self.mqtt.loop_start()

	def on_connect(self, client, userdata, flags, rc):
	    self.mqtt_subscribe(client)
	
	def on_message(self, client, userdata, msg):
	    self.process_mqtt_message(msg)
	
	def on_publish(self, client, userdata, mid):
	    return
	
	def mqtt_subscribe(self, client):
	    client.subscribe("smartcity/data/0/GPS/+")    
	    return

	def process_mqtt_message(self, msg):
		msg = msg.payload.decode('utf-8').split(',')
		print(str(msg))


	def run_shell_process(self, cmd):
		try:
			output = subprocess.check_output(
				cmd, shell=True,stderr=subprocess.STDOUT
				)
		except Exception as err:
			print("cmd %s FAILED %r" %(cmd, err))
			return str(err)
		return output.decode(encoding="utf-8", errors="ignore").rstrip()

	def mount_partition_as_rw(self, cmd):
		run_shell_process("sudo mount -o remount rw /")
		logging.debug("Partition is mount as rw")
		return

	def make_backups(self):
		run_shell_process("sudo mkdir %s" % (backup_dir))
		run_shell_process("sudo cp %s %s."  % (net_config, backup_dir))
		run_shell_process("sudo cp %s %s."  % (appdef, backup_dir))
		logging.debug("Backups were made")
		return

	def disable_nmag(self):
		logging.debug("Disabling nmag")
		with open(appdef) as f:
			for line in f.readlines():
				if "#nmag" in line:
					return
		for line in fileinput.input(appdef, inplace=True):
			print (line.rstrip().replace('nmag:', '#nmag'))
			return

	def add_testcase_to_appdef(self):
		logging.debug("Appending our script to appdef")
		with open(appdef, 'a') as f:
			f.write(appdef_test_line)
		logging.debug("Testcase added to appdef, will be started on next boot")

	def check_reset_counter(self):
		logging.debug("Checking check_reset_counter")
		cmd = "sudo uboot_env -n reset_counter | grep -oE '[[:digit::]]'"
		return run_shell_process(cmd)

	def reboot(self):
		logging.debug("Going down for a reboot")
		run_shell_process("sudo reboot")

	def first_time_running(self):
		logging.debug("Checking are we running for first time")
		if os.path.exists("/home/pi/conf_backups"):
			return False

	def enable_wifi_auto(self):
		logging.debug("Setting wifi auto mode")
		with open(net_faces, 'a') as f:
			f.write("auto wlan0")

	def do_cleanup(self):
		logging.debug("Test over, cleaning up")

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
	
	