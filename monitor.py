# from temp_humid import read_humidity
# from temp_humid import read_temperature
# from lux import get_lux
# from pres_alt import get_pres



import time
import datetime
import requests
import subprocess
import sys
import git
import configparser
from daemon import Daemon
from configparser import ConfigParser
import os
#from sensors import lux, pressure_altitude, temperature_humidity, sgp30
import logging
import psutil
import uuid
from display import Display
import signal

from web_interface import webserver

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# create the logging file handler
fh = logging.FileHandler("homesense.log")

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)

# add handler to logger object
logger.addHandler(fh)

#api_server = "http://192.168.1.161:8000"

def int_to_en(num):
    d = { 0 : 'zero', 1 : 'one', 2 : 'two', 3 : 'three', 4 : 'four', 5 : 'five',
          6 : 'six', 7 : 'seven', 8 : 'eight', 9 : 'nine', 10 : 'ten',
          11 : 'eleven', 12 : 'twelve', 13 : 'thirteen', 14 : 'fourteen',
          15 : 'fifteen', 16 : 'sixteen', 17 : 'seventeen', 18 : 'eighteen',
          19 : 'nineteen', 20 : 'twenty',
          30 : 'thirty', 40 : 'forty', 50 : 'fifty', 60 : 'sixty',
          70 : 'seventy', 80 : 'eighty', 90 : 'ninety' }
    k = 1000
    m = k * 1000
    b = m * 1000
    t = b * 1000

    assert(0 <= num)

    if (num < 20):
        return d[num]

    if (num < 100):
        if num % 10 == 0: return d[num]
        else: return d[num // 10 * 10] + '-' + d[num % 10]

    if (num < k):
        if num % 100 == 0: return d[num // 100] + ' hundred'
        else: return d[num // 100] + ' hundred and ' + int_to_en(num % 100)

    if (num < m):
        if num % k == 0: return int_to_en(num // k) + ' thousand'
        else: return int_to_en(num // k) + ' thousand, ' + int_to_en(num % k)

    if (num < b):
        if (num % m) == 0: return int_to_en(num // m) + ' million'
        else: return int_to_en(num // m) + ' million, ' + int_to_en(num % m)

    if (num < t):
        if (num % b) == 0: return int_to_en(num // b) + ' billion'
        else: return int_to_en(num // b) + ' billion, ' + int_to_en(num % b)

    if (num % t == 0): return int_to_en(num // t) + ' trillion'
    else: return int_to_en(num // t) + ' trillion, ' + int_to_en(num % t)

    raise AssertionError('num is too large: %s' % str(num))

def restart_program():
    """Restarts the current program, with file objects and descriptors
       cleanup
    """
    logger.info("Restarting to apply updates")
    #print("Restarting to apply updates")
    try:
        p = psutil.Process(os.getpid())
        for handler in p.get_open_files() + p.connections():
            os.close(handler.fd)
    except Exception as e:
        logger.error(e)

    python = sys.executable
    os.execl(python, python, *sys.argv)

class Monitor(Daemon):
    verbose = 0

    def check_for_updates(self):
        try:
            self.display.update_screen(["Checking for updates"])
            logger.info("Checking for sensor updates")
            #print("Checking for sensor_updates")
            g = git.cmd.Git(os.getcwd())
            update_results = g.pull()
            if "Updating " in update_results:
                restart_program()
        except Exception as err:
            logger.error(err)
            #print("CAUGHT EXCEPTION DURING UPDATES: %s" % err)

    def get_sensors(self):
        logger.info("Detecting sensors")
        self.display.update_screen(["Detecting Sensors..."])
        time.sleep(2)
        self.available_sensors = []
        try:
            p = subprocess.Popen(['i2cdetect', '-y', '1'], stdout=subprocess.PIPE, )
            firstLine = True
            self.sensor_addresses = []

            for i in range(1, 9):
                if firstLine:
                    line = str(p.stdout.readline()).strip()
                    firstLine = False
                else:
                    line = str(p.stdout.readline()).strip()
                    # print line
                    entry = line.split(" ")
                    entry = entry[1:]
                    for each in entry:
                        if (each != "") and (each != "--"):
                            # print(each)
                            self.sensor_addresses.append("0x%s" % each)
            self.sensor_addresses.append("0x58")
        except Exception as err:
            logger.warning("i2cdetect not supported, setting dummy vars")
            #print("Not supported on this OS, setting dummy vars")
            self.sensor_addresses = ['0x40', '0x60', '0x39']

        i = 1

        for sensor_address in self.config.items('SensorAddresses'):
            if sensor_address[1] in self.sensor_addresses:
                #print(sensor_address)
                try:
                    unit = self.config.get('SensorUnits', sensor_address[0])
                    #print(unit)
                except Exception as e:
                    if "No option" in str(e):
                        logger.warning("No unit for %s sensor" % sensor_address[1])
                        #print("No unit set")
                        unit = "Unknown"

                self.available_sensors.append({'sensor_name': "sensor_%s" % int_to_en(i),
                                               'name': sensor_address[0],
                                               'sensor_data_unit_name': "sensor_%s_data_unit" % int_to_en(i),
                                               'sensor_data_unit': unit,
                                               'address': sensor_address[1]})
                i += 1
        line = ""
        for each in self.available_sensors:
            line += "%s " % each['name']
        self.display.update_screen(["Found Sensors:", line])
        time.sleep(4)
        #print(self.available_sensors)
        logger.debug("Found sensors: %s" % self.available_sensors)
        #exit()


    def log(self, *args):
        if self.verbose >= 1:
            with open('homesense.log', 'a') as out_file:
                out_file.write(str(*args) + "\n")

    def generate_device_id(self):
        self.device_id = str(uuid.uuid4())

    def save_config(self):
        #self.print_config()
        with open('homesense.conf', 'w') as configfile:
            self.config.write(configfile)

    def print_config(self):
        for section in self.config.sections():
            for option in self.config.items(section):
                logger.debug("%s - %s" % (section, option))

    def register(self):
        logger.info("Registering with server")
        self.display.update_screen(["Registering with server:", self.api_server])
        data = {'device_id': self.device_id}
        i = 1
        if self.dev_api_server:
            d = requests.get(self.api_server + "/api/sensors/get_token/")
        r = requests.get(self.api_server + "/api/sensors/get_token/")

        if r.status_code == 200:
            logger.info("Received sensor token from server")
            self.token = r.json()['token']
            self.config.set("Server", "token", self.token)
        else:
            #print(r.status_code, r.text)
            logger.error("Unable to get token from server: %s %s" % (r.status_code, r.text))
            exit()
        try:
            for each in self.available_sensors:
                data[each['sensor_name'] + "_name"] = each['name']
                data[each['sensor_data_unit_name']] = each['sensor_data_unit']
                data['token'] = self.token
            if self.dev_api_server:
                d = requests.post(self.dev_api_server + "/api/sensors/register/", data=data)
            r = requests.post(self.api_server + "/api/sensors/register/", data=data)
            if r.status_code == 201:
                logger.info("Successfully Registered Sensor")
            else:
                #print(r.status_code, r.text)
                logger.error("Unable to register with server: %s %s" % (r.status_code, r.text))
                exit()
        except Exception as err:
            logger.error("Unable to register with server: %s" % (err))
            exit()


    def initialize_sensors(self):
        logger.info("Initializing Sensors")
        self.display.update_screen(["Initializing Sensors"])
        self.sensors =  []
        self.sensors.append(lux.Lux())
        self.sensors.append(pressure_altitude.Pressure())
        self.sensors.append(temperature_humidity.Temperature())
        self.sensors.append(temperature_humidity.Humidity())
        self.sensors.append(sgp30.co2())
        self.sensors.append(sgp30.tvoc())
        self.display.update_screen(["All sensors running"])
        time.sleep(2)

    def keyboard_interrupt(self, signal, frame):
        logger.info("Keyboard Interrupt - Shutting Down")
        self.display.update_screen(["Shutting Down!"])
        time.sleep(5)
        self.display.clear()
        sys.exit(0)


    def collect_sensor_data(self):
        logger.info("Collecting sensor data")
        self.display.update_screen(["Collecting Data"])
        sensor_data = {}
        for sensor in self.sensors:
            data = sensor.get_data()
            #print(sensor.get_name())
            #print(data)
            if data == None:
                sensor_data[sensor.get_name()] = None
            else:
                sensor_data[sensor.get_name()] = round(data, 3)
            time.sleep(.5)

        for each in self.available_sensors:
            each['latest_data'] = sensor_data[each['name']]

        time.sleep(1)


    def initialize(self):
        logger.info("Initializing HomeSense Monitor")
        #print("Initializing HomeSense Monitor...")
        self.generate_device_id()
        logger.info("Device ID: %s" % self.device_id)
        #print("Device ID: %s" % self.device_id)
        self.config.set('Server', 'device_id', str(self.device_id))
        self.register()
        self.save_config()


    def check_first_start(self):
        self.config = ConfigParser()

        logger.info("Checking to see if we have a config file")
        import os.path
        first_start = False
        if os.path.isfile("homesense.conf"):
            try:
                self.config.read_file('homesense.conf')
                token = self.config.get('Server', 'Token')
                if token:
                    print("OK")
                else:
                    del self.config
                    first_start = True
            except Exception as err:
                logger.debug("Config exists, but is not valid.")
                first_start = True
        else:
            first_start = True
        return first_start


    def load_config(self):
        self.config = ConfigParser()
        try:
            logger.info("Trying to read homesense.conf")
            with open('homesense.conf') as f:
                self.config.read_file(f)
                self.token = self.config.get('Server', 'Token')
                self.device_id = self.config.get('Server', 'Device_id')
                self.api_server = self.config.get('Server', 'server')
                if self.config.has_option('Server', 'dev_server'):
                    self.dev_api_server = self.config.get('Server', 'dev_server')
                else:
                    self.dev_api_server = None
        except IOError as err:
            logger.warning("Config file not found")
            print("Config File Not Found.")

    def create_initial_config(self):
        self.config = ConfigParser()
        self.config.read('.homesense_init.conf')
        self.api_server = self.config.get('Server', 'server')
        if self.config.has_option('Server', 'dev_server'):
            self.dev_api_server = self.config.get('Server', 'dev_server')
        self.save_config()

    def run(self):
        logger.debug("Starting Run Statement")
        signal.signal(signal.SIGINT, self.keyboard_interrupt)
        self.display = Display()
        #self.display.dim()
        self.display.update_screen(["Booting..."])
        time.sleep(2)
        self.check_for_updates()
        if self.check_first_start():
            self.create_initial_config()
            self.get_sensors()
            self.initialize()
        else:
            self.load_config()
            self.get_sensors()

        self.initialize_sensors()


        while True:
            try:
                self.collect_sensor_data()
                post_data = {'device_id': self.device_id, 'token': self.token}
                for each_sensor in self.available_sensors:
                    post_data[each_sensor['sensor_name'] + "_data"] = each_sensor['latest_data']
                #print(post_data)

                #print(post_data)
                logger.debug("%s" % str(post_data))
                logger.info("Uploading sensor data")
                self.display.update_screen(["Uploading Data"])
                time.sleep(1)
                if self.dev_api_server:
                    try:
                        d = requests.post(self.dev_api_server + '/api/data/add/', data=post_data)
                    except Exception as err:
                        logger.error(err)
                        #print("CAUGHT EXCEPTION: %s" % err)
                r = requests.post(self.api_server + '/api/data/add/', data=post_data)
                if r.status_code == 201:
                    logger.debug("Data uploaded")
                    #print("Data Uploaded")
                else:
                    logger.error("%s %s" % (r.status_code, r.json()))
                    # print(r.status_code)
                    # print(r.json())
                self.display.update_screen(["Data Uploaded...", "", "Sleeping 300 seconds"])
                timer = 300
                while timer > 0:
                    self.display.update_screen(["Sleeping for", "%i seconds" % timer])
                    time.sleep(1)
                    timer -= 1
            except Exception as err:
                #print("CAUGHT EXCEPTION: %s" % err)
                logger.error(err)
                time.sleep(600)

if __name__ == "__main__":
    daemon = Monitor('homesense.pid', verbose=2)
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        elif 'debug' == sys.argv[1]:
            daemon.run()
        else:
            print("Unknown command")
            sys.exit(2)
        sys.exit(0)
    else:
        print("usage: %s start|stop|restart" % sys.argv[0])
        sys.exit(2)