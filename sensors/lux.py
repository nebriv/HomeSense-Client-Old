from tsl2561 import TSL2561
from time import sleep
import pigpio

def get_lux():
    tsl = TSL2561(debug=1)
    tsl.set_auto_range(16)
    return tsl.lux()
