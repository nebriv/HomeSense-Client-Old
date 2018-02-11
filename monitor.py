# from temp_humid import read_humidity
# from temp_humid import read_temperature
# from lux import get_lux
# from pres_alt import get_pres



import time
import datetime
import requests
import subprocess
from daemon import Daemon
api_server = "http://192.168.1.161:8000"
sensor_id = "http://127.0.0.1:8000/api/sensors/1dbe5bb9-6ee6-46a1-86c7-cfdf274033a4/"

def get_i2c_sensors():
    p = subprocess.Popen(['i2cdetect', '-y', '1'], stdout=subprocess.PIPE, )
    # cmdout = str(p.communicate())

    for i in range(0, 9):
        line = str(p.stdout.readline())
        print(line)

class Monitor(Daemon):
    def run(self):
        get_i2c_sensors()

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
