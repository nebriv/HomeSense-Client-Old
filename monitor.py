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
from sensors import lux, pressure_altitude, temperature_humidity, sgp30
import logging
import psutil
import uuid

api_server = "http://192.168.1.161:8000"
sensor_id = "http://127.0.0.1:8000/api/sensors/1dbe5bb9-6ee6-46a1-86c7-cfdf274033a4/"

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

    print("Restarting to apply updates")
    try:
        p = psutil.Process(os.getpid())
        for handler in p.get_open_files() + p.connections():
            os.close(handler.fd)
    except Exception as e:
        logging.error(e)

    python = sys.executable
    os.execl(python, python, *sys.argv)

class Monitor(Daemon):
    verbose = 0

    def check_for_updates(self):
        print("Checking for sensor_updates")
        g = git.cmd.Git(os.getcwd())
        update_results = g.pull()
        if "Updating " in update_results:
            restart_program()

    def get_sensors(self):
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
        except FileNotFoundError as err:
            print("Not supported on this OS, setting dummy vars")
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
                        print("No unit set")
                        unit = "Unknown"

                self.available_sensors.append({'sensor_name': "sensor_%s" % int_to_en(i),
                                               'name': sensor_address[0],
                                               'sensor_data_unit_name': "sensor_%s_data_unit" % int_to_en(i),
                                               'sensor_data_unit': unit,
                                               'address': sensor_address[1]})
                i += 1
        #print(self.available_sensors)
        #exit()


    def log(self, *args):
        if self.verbose >= 1:
            with open('homesense.log', 'a') as out_file:
                out_file.write(str(*args) + "\n")

    def generate_device_id(self):
        self.device_id = str(uuid.uuid4())

    def save_config(self):
        self.print_config()
        with open('homesense.conf', 'w') as configfile:
            self.config.write(configfile)

    def print_config(self):
        for section in self.config.sections():
            for option in self.config.items(section):
                print(section, option)

    def register(self):
        data = {'device_id': self.device_id}
        i = 1
        r = requests.get(api_server + "/api/sensors/get_token/")

        if r.status_code == 200:
            self.token = r.json()['token']
            self.config.set("Server", "token", self.token)

        else:
            print(r.status_code, r.text)
            exit()

        for each in self.available_sensors:
            data[each['sensor_name']] = each['name'] + "_name"
            data[each['sensor_data_unit_name']] = each['sensor_data_unit']
            data['token'] = self.token
        r = requests.post(api_server + "/api/sensors/register/", data=data)
        if r.status_code == 201:
            print("Successfully Registered Sensor")
        else:
            print(r.status_code, r.text)
            exit()

    def initialize_sensors(self):
        self.sensors =  []
        self.sensors.append(lux.Lux())
        self.sensors.append(pressure_altitude.Pressure())
        self.sensors.append(temperature_humidity.Temperature())
        self.sensors.append(temperature_humidity.Humidity())
        self.sensors.append(sgp30.co2())
        #self.sensors.append(sgp30.tvoc())


    def collect_sensor_data(self):
        try:
            sensor_data = {}
            for sensor in self.sensors:
                data = sensor.get_data()
                if data == None:
                    sensor_data[sensor.get_name()] = None
                else:
                    sensor_data[sensor.get_name()] = round(sensor.get_data(), 3)
                time.sleep(.5)

            for each in self.available_sensors:
                each['latest_data'] = sensor_data[each['name']]
        except Exception as err:
            print(err)

    def initialize(self):
        print("Initializing HomeSense Monitor...")
        self.generate_device_id()
        print("Device ID: %s" % self.device_id)
        self.config.set('Server', 'device_id', str(self.device_id))
        self.register()
        self.save_config()

    def run(self):
        self.check_for_updates()
        self.config = ConfigParser()
        try:
            with open('homesense.conf') as f:
                self.config.read_file(f)
                self.token = self.config.get('Server', 'Token')
                self.device_id = self.config.get('Server', 'Device_id')
                self.get_sensors()
        except IOError as err:
            print("Config File Not Found.")
            self.config.read('.homesense_init.conf')
            self.get_sensors()
            self.initialize()

        self.initialize_sensors()

        while True:
            self.collect_sensor_data()
            try:
                post_data = {'device_id': self.device_id, 'token': self.token}
                for each_sensor in self.available_sensors:
                    post_data[each_sensor['sensor_name'] + "_data"] = each_sensor['latest_data']
                print(post_data)

                r = requests.post(api_server + '/api/data/add/', data=post_data)
                if r.status_code == 201:
                    print("Data Uploaded")
                else:
                    print(r.status_code)
                    print(r.json())
            except Exception as err:
                print(err)

            time.sleep(300)


# while True:
#     pass
#     # with open('output.log', 'a') as out_file:
#     #     try:
#     #         print("Collecting data")
#     #         temp_c = round(read_temperature(), 1)
#     #         temp_f = round(9.0/5.0 * temp_c + 32, 1)
#     #         humidity = round(read_humidity(), 1)
#     #         light = round(get_lux(), 1)
#     #         pressure = round(get_pres(), 1)
#     #         time_val = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     #         line_out = "%s,%s,%s,%s,%s" % (time_val,temp_f,humidity,light,pressure)
#     #         print "Temperature(F): %s" % temp_f
#     #         print "  Humidity(rh): %s" % humidity
#     #         print " Ambiant Light: %s" % light
#     #         print " Pressure(kPa): %s" % pressure
#     #     except Exception as e:
#     #         print(e)
#     #         pass
#     #
#     #
#     #     out_file.write(line_out + "\n")
#     #
#     #     sensor_data = {"temperature": temp_f, "humidity": humidity, "light": light, "pressure": pressure}
#     #
#     #     post_data = {"device_id": sensor_id, "sensor_data": str(sensor_data)}
#     #     #print post_data
#     #     r = requests.post(api_server + "/api/data/", data = post_data)
#     #     #print r.text
#     #     if r.status_code == 201:
#     #         print "Uploaded Data"
#     #     else:
#     #         print "Failed Uploading Data:"
#     #         print r.text
#
#     time.sleep(600)


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