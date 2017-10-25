#!/usr/bin/env python3

import sys, re, logging, time
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

	def __init__(self, name, dut, connection):
		self.name = name
		self.dut = test_dict[self.name]['dut']
		self.connection = test_dict[self.name]['connection']
		self.nmag = test_dict[self.name]['nmag']

	def init_mqtt(self):
		self.mqtt = mqtt.Client()
		self.mqtt.on_connect = on_connect
		self.mqtt.on_message = on_message
		self.mqtt.on_publish = on_publish
		self.mqtt.connect(mqtt_broker, port=mqtt_broker_port, keepalive=60)
		self.mqtt.loop_start()

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
		for line in fileinput.input(appdef, inplace=True)
		if "#nmag" in line:
			return

	def add_testcase_to appdef(self):
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
		logging.debug()
