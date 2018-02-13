from tsl2561 import TSL2561
from time import sleep
import pigpio
from . import base_sensor

class Lux(base_sensor.Sensor):

    def __init__(self):
        self.name = "Light"
        self.tsl = TSL2561(debug=1)
        self.tsl.set_auto_range(16)

    def get_data(self):
        return self.tsl.lux()

    def get_name(self):
        return self.name