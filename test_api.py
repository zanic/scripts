#!/usr/bin/env python3

import sys, re, logging, time, subprocess, os, fileinput
from datetime import datetime
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
from dict_base import test_dict


class Test_case(object):

	log = logging.getLogger('Test_case')

	net_config = "/etc/network/interfaces"
	appdef = "/home/pi/SmartSense/appdef"
	appdef_test_line = "testcase:/home/pi/:./testcase_script.py:: root:no\n"
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
		super().__init__()
		self.name = name
		self.dut = test_dict[self.name]['dut']
		self.connection = test_dict[self.name]['connection']
		self.nmag = test_dict[self.name]['nmag']
		self.include_reboot = test_dict[self.name]['reboot']

		self.mount_partition_as_rw()
		if self.first_time_running():
			self.make_backups()
			self.add_testcase_to_appdef()
			if self.nmag:
				self.disable_nmag()
			self.enable_wifi_auto()
			self.reboot()
		else:
			self.init_mqtt()
			return

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

	def mount_partition_as_rw(self):
		print ("Mounting partition as rw")
		self.run_shell_process("sudo mount -o remount rw /")
		self.log.info("Partition is mount as rw")
		return

	def make_backups(self):
		print ("Making backups")
		self.run_shell_process("mkdir %s" % (self.backup_dir))
		self.run_shell_process("sudo cp %s %s."  % (self.net_config, self.backup_dir))
		self.run_shell_process("sudo cp %s %s."  % (self.appdef, self.backup_dir))
		self.log.info("Backups were made")
		return

	def disable_nmag(self):
		self.log.info("Disabling nmag")
		print ("Disabling nmag")
		with open(self.appdef) as f:
			for line in f.readlines():
				if "#nmag" in line:
					return
		for line in fileinput.input(self.appdef, inplace=True):
			print (line.rstrip().replace('nmag:', '#nmag'))
			return

	def add_testcase_to_appdef(self):
		print ("Appending our script to appdef")
		self.log.info("Appending our script to appdef")
		with open(self.appdef, 'a') as f:
			f.write(self.appdef_test_line)
		self.log.info("Testcase added to appdef, will be started on next boot")

	def check_reset_counter(self):
		self.log.info("Checking check_reset_counter")
		cmd = "sudo uboot_env -n reset_counter | grep -oE '[[:digit::]]'"
		return self.run_shell_process(cmd)

	def reboot(self):
		print ("Going for a reboot")
		self.log.info("Going down for a reboot")
		self.run_shell_process("sudo reboot")

	def first_time_running(self):
		self.log.info("Checking are we running for first time")
		if os.path.exists(self.backup_dir):
			print ("Not running for first time")
			return False
		else:
			print("First time running")
			return True

	def enable_wifi_auto(self):
		self.log.info("Setting wifi auto mode")
		with open(self.net_config, 'a') as f:
			f.write("auto wlan0")

	def restart_modem(self):
		Modem().restart()

	def do_cleanup(self):
		self.log.info("Test over, cleaning up")

class Modem(Test_case):

	mbmb_power_pin = 11
	mbmb_reset_pin  =13
	mbmb_hard_power_pin = 15

	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BOARD)
	GPIO.setup(mbmb_reset_pin, GPIO.OUT)
	GPIO.setup(mbmb_power_pin, GPIO.OUT)
	GPIO.setup(mbmb_hard_power_pin, GPIO.OUT)

	def __init__(self):
		pass

	def restart(self):
		if self.check_modem_exists():
			self.log.info("/dev/gsmmodem exists")
			self.power_off()
			time.sleep(3)
			self.power_on()
			self.reset()
			return
		else:
			self.log.info("/dev/gsmmodem does not exist, try getting it back")
			self.power_on()
			self.reset()
			sleep_time = 2
			time_left = 30
			while time_left-sleep_time > 0:
				if self.check_modem_exists():
					self.log.info("Modem is back")
					return
				else:
					time.sleep(sleep_time)


	def power_off(self):
		self.log.info("Powering off modem")
		GPIO.output(self.mbmb_power_pin, False)
		time.sleep(1)
		GPIO.output(self.mbmb_power_pin, True)
		time.sleep(2)
		GPIO.output(self.mbmb_power_pin, False)
		time.sleep(1)
		GPIO.output(self.mbmb_hard_power_pin, False)
		return
	
	def power_on(self):
		self.log.info("Powering on modem")
		GPIO.output(self.mbmb_hard_power_pin, True)
		time.sleep(1)
		GPIO.output(self.mbmb_power_pin, True)
		time.sleep(1)
		GPIO.output(self.mbmb_power_pin, False)
		time.sleep(0.18)
		GPIO.output(self.mbmb_power_pin, True)
		return

	def reset(self):
		self.log.info("Resetting modem")
		GPIO.output(self.mbmb_reset_pin, True)
		time.sleep(1)
		GPIO.output(self.mbmb_reset_pin, False)
		time.sleep(0.1)
		GPIO.output(self.mbmb_reset_pin, True)
		return

	def check_modem_exists(self):
		return os.path.exists("/dev/gsmmodem")

