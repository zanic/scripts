#!/usr/bin/env python3

import sys, re, logging, time, subprocess, os, fileinput, serial, threading
from datetime import datetime
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
from test_descr import test_dict
from collections import OrderedDict


class Test_case(object):

	log = logging.getLogger('Test_case')

	net_config = "/etc/network/interfaces"
	appdef = "/home/pi/SmartSense/appdef"
	appdef_test_line = "testcase:/home/pi/scripts/:./test.py::root:no\n"
	backup_dir = "backup_dir/"
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
		self.test_name = name
		self.dut = test_dict[self.test_name]['dut']
		self.connection = test_dict[self.test_name]['connection']
		self.nmag = test_dict[self.test_name]['nmag']
		self.include_reboot = test_dict[self.test_name]['reboot']

		#Report file 
		self.report_file = self.test_name + ".txt"
		self.test_run_state = False
		# Dict containing GPS data 
		self.dict_gps_coords = OrderedDict()
		# Dict containing test starting and ending time
		self.dict_run_times = {}

		self.mount_partition_as_rw()
		if self.first_time_running():
			self.make_backups()
			self.add_testcase_to_appdef()
			if not self.nmag:
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
		if self.dut == 'gps':
			client.subscribe("smartcity/data/0/GPS/+")    
		return

	def process_mqtt_message(self, msg):
		match = re.search("smartcity/data/0/GPS", msg.topic)
		if match:
			msg = (msg.payload.decode('utf-8').split(','))
			self.process_mqtt_gps_data(msg)

	def process_mqtt_gps_data(self, msg):
		if self.test_run_state == True:
			if float(msg[0]) > 0.15 and float(msg[2]) > 0.15:
				self.dict_gps_coords[datetime.now()] = str(msg[0]) + ":" + str(msg[2])
				
				if len(self.dict_gps_coords) > 100:
					self.end_test()


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
		self.run_shell_process("sudo mount -o remount rw /")
		self.log.info("Partition is mount as rw")
		return

	def make_backups(self):
		self.run_shell_process("mkdir %s" % (self.backup_dir))
		self.run_shell_process("sudo cp %s %s."  % (self.net_config, self.backup_dir))
		self.run_shell_process("sudo cp %s %s."  % (self.appdef, self.backup_dir))
		self.log.info("Backups were made")
		return

	def disable_nmag(self):
		self.log.info("Disabling nmag")
		for line in fileinput.input(self.appdef, inplace=True):
			print (line.rstrip().replace('nmag', '#nmag'))
		return

	def add_testcase_to_appdef(self):
		self.log.info("Appending our script to appdef")
		with open(self.appdef, 'a') as f:
			f.write(self.appdef_test_line)
		self.log.info("Testcase added to appdef, will be started on next boot")

	def check_reset_counter(self):
		self.log.info("Checking check_reset_counter")
		cmd = "sudo uboot_env -n reset_counter | grep -oE '[[:digit::]]'"
		return self.run_shell_process(cmd)

	def reboot(self):
		self.log.info("Going down for a reboot")
		self.run_shell_process("sudo reboot")

	def first_time_running(self):
		self.log.info("Checking are we running for first time")
		if os.path.exists(self.backup_dir):
			self.log.info("Not running for first time")
			return False
		else:
			self.log.info("First time running")
			return True

	def enable_wifi_auto(self):
		self.log.info("Setting wifi auto mode")
		with open(self.net_config, 'a') as f:
			f.write("auto wlan0\n")

	def restart_modem(self):
		retry = 0
		while Modem().restart() != True:
			retry = retry + 1
			if retry > 5:
				self.log.info("Modem could not be returned, exit")
				self.do_cleanup()

	def calc_diff(self):
		with open(self.report_file, 'w') as f:
			for line in f.readlines():
				split = line.split()



	def do_cleanup(self):
		self.log.info("Test over, cleaning up")
		with open(self.report_file, 'a') as f:
			
			if self.test_name == "MODT-1.2.1":
				f.write(self.timestamp_begin.strftime('%d.%m.%Y %H:%M:%S')
			 	+ " : " + self.timestamp_end.strftime('%d.%m.%Y %H:%M:%S') + 
			 	" diff=" + str((self.timestamp_end-self.timestamp_begin).total_seconds()) +
			 	" seconds" + "\n")
			
			if self.test_name == "MODT-1.2.2":
				for key, value in self.dict_gps_coords.items():
					f.write(str(key) + ": " + str(value) + '\n')
				#self.calc_diff()

		self.dict_gps_coords.clear()
		self.test_run_state = False
		#exit()

	def start_test(self):
		self.log.info("Starting test")
		self.test_run_state = True

		self.timestamp_begin = datetime.now()
		self.dict_run_times[self.test_run_state] = self.timestamp_begin
		self.log.info("Test started with time: " + self.timestamp_begin.strftime('%d.%m.%Y %H:%M:%S'))

		while self.test_run_state != False:
			time.sleep(10)
		return 

	def end_test(self):
		self.log.info("Stoping test")
		self.test_run_state = False
		self.timestamp_end = datetime.now()
		self.dict_run_times[self.test_run_state] = self.timestamp_end
		self.log.info("Test ended with time: " + self.timestamp_end.strftime('%d.%m.%Y %H:%M:%S'))
		self.do_cleanup()


#class Modem(Test_case):
class Modem(object):
	mbmb_power_pin = 11
	mbmb_reset_pin  =13
	mbmb_hard_power_pin = 15

	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BOARD)
	GPIO.setup(mbmb_reset_pin, GPIO.OUT)
	GPIO.setup(mbmb_power_pin, GPIO.OUT)
	GPIO.setup(mbmb_hard_power_pin, GPIO.OUT)

	def __init__(self, **kwargs):
		if len(kwargs) > 0:
			self.port = port
			self.baudrate = baudrate
			self.timeout = 1
			self.alive = False
			self.response_event = None
			self.reponse = None
			self.notification = []
			self.tx_Lock = threading.RLock()
		else:
			pass

	def connect(self):
		try:
			self.serial = serial.Serial(port=self.port, baudrate=self.baudrate,
			 timeout=self.timeout)
			self.alive = True
			self.rxThread = threading.Thread(target=self.readloop)
			self.rxThread.daemon = True
			self.rxThread.start()
		except Exception as e:
			self.log.err("Error opening serial with: %r" % (e))

	def close(self):
		self.alive = False
		self.rxThread.join()
		self.serial.close()

	def handle_line_read(self, line, checkForResponseTerm=True):
		if self.response_event and not self.response_event.is_set():
			self.response.append(line)
			if not checkForResponseTerm or self.RESPONSE_TERM.match(line):
				self.log.debug('reponse: %s', self.response)
				self.response_event.set()
		else:
			self.notification.append(line)
			if self.serial.inWaiting() == 0:
				self.notifyCallback(self.notification)
				self.notification = []

	def read_loop(self):
		try:
			read_term_seq = list(self.RX_EOL_SEQ)
			read_term_len = len(read_term_seq)
			rxBuffer = []
			while self.alive:
				data = self.serial.read(1)
				if data != '':
					rxBuffer.append(data)
					if rxBuffer[-read_term_len:] == read_term_seq:
						line = ''.join(rxBuffer)
						rxBuffer = []
						self.handle_line_read(line, checkForResponseTerm=False)
		except serial.SerialException as e:
			self.alive = False
			try:
				self.serial.close()
			except Exception as err:
				self.log_err("Fatal Error %r" % (err))

	def write(self, data, waitForResponse=True, timeout=5):
		while self.tx_Lock:
			if waitForResponse:
				self.response = []
				self.response_event = threading.Event()
				self.serial.write(data)
				if self.response_event.wait(timeout):
					self.response_event = None
					return self.response
				else:
					self.response_event = None
					if len(self.response) > 0:
						self.log.err("Timeout error,  reponse is: %s" % (self.response))

			else:
				self.serial.write(data)




	def restart(self):
		self.log.info("Restarting modem")
		if self.check_modem_exists():
			self.log.info("/dev/gsmmodem exists")
		else:
			self.log.info("/dev/gsmmodem does not exist, try getting it back")
		self.power_off()
		time.sleep(5)
		self.power_on()
		time.sleep(5)
		self.reset()
		if self.check_modem_return():
			return True
		else:
			return False

	def check_modem_return(self):
		self.log.info("Checking has modem returned")
		sleep_time = 2
		time_left = 60
		while time_left - sleep_time > 0:
			if self.check_modem_exists():
				self.log.info("Modem is back")
				return True
			else:
				time.sleep(sleep_time)
				time_left = time_left - sleep_time
		self.log.info("Modem has not returned")
		return False


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
		self.log.info("Modem is reset")
		return

	def check_modem_exists(self):
		return os.path.exists("/dev/gsmmodem")