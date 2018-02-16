import time
import pigpio
import math
import binascii
from struct import unpack

from threading import Thread
from .base_sensor import Sensor

class SGP30(Sensor):
    def __init__(self):
        super(Sensor).__init__()
        self.setup()

    def run_sensor(self):
        while True:
            self.pi.i2c_write_device(self.handle, self.measureair)
            time.sleep(.2)
            count, data = self.pi.i2c_read_device(self.handle,6)
            #print(count, data)
            self.co2 = int.from_bytes(data[0:2], byteorder='big')
            self.voc = int.from_bytes(data[3:4], byteorder='big')
            #print("Co2: %i" % self.co2)
            #print("TVOC: %i" % self.voc)
            time.sleep(.6)


    def setup(self):
        print("Initializing SGP30 Sensor...")
        self.pi = pigpio.pi()
        self.addr = 0x58
        self.co2 = 0
        self.voc = 0

        # i2c bus, if you have a Raspberry Pi Rev A, change this to 0
        self.bus = 1

        # HTU21D-F Commands
        self.init = b"\x20\x03"
        self.measureair = b"\x20\x08"
        self.getbaseline = 0x2015
        self.setbaseline = 0x201e
        self.measuretest = 0x2032
        self.getfeatureset = 0x202f
        self.measuresignals = 0x2050
        self.handle = self.pi.i2c_open(self.bus, self.addr)
        self.pi.i2c_write_device(self.handle, self.init)
        time.sleep(1)
        self.pi.i2c_write_device(self.handle, self.measureair)

        thread1 = Thread(target=self.run_sensor)
        thread1.start()
        self.sensor_running = True
        time.sleep(15)
        print("Sensor Started")
        #while True:
        #    print(self.co2)
        #    time.sleep(5)

    #def get_data(self)

class tvoc(SGP30):
    def __init__(self):
        super(SGP30).__init__()
        #self.setup()
        self.name = "TVOC"

    def get_data(self):
        return self.voc

class co2(SGP30):
    def __init__(self):
        super(SGP30).__init__()
        self.setup()
        self.name = "Co2"

    def get_data(self):
        return self.co2

def main():

    sensor = co2()
    print(sensor.name)
    time.sleep(15)
    for i in range(1,5):
        print(sensor.get_data())
        time.sleep(2)

    #sensor2 = co2()
    #print(sensor2.get_data())



if __name__ == "__main__":
    main()
