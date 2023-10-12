# Import necessary modules
import time
import onewire
import ds18x20
from machine import Pin, I2C
from imu import MPU6050
import ssd1306
from ws_server import AppServer
from ota import OTAUpdater
from secrets import SSID, PASSWORD

version = 2.1
firmware_url = "https://raw.githubusercontent.com/Jacnil98/caravan/main/"
# Defines pixels on OLED display
oled_width = 128
oled_height = 64
# Defines global values for pitch angle, roll angle, the caravan width and the tilt amount
caravan_width = 250
# Global values for the inner and outside temp
out_temp = 0
in_temp = 0
ota_btn_debounce_time = 0

# Set up the I2C interface
i2c = machine.SoftI2C(scl=machine.Pin(1), sda=machine.Pin(0))

# Setup the oled display
oled_connected = True
try:
    oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)
except:
    oled_connected = False
    
#Fills all the pixels in the OLED displays with black
if oled_connected == True:
    oled.fill(0)
    oled.text(f"Starting", 0, 20)
    oled.show()
    
# Create an instance of the MPU6050 sensor
angle_sensor = True
imu = MPU6050(i2c)

pin = machine.Pin(16, machine.Pin.OUT)
pin.value(0) #set GPIO16 low to reset OLED
pin.value(1) #while OLED is running, must set GPIO16 in high

# Defines ON/OFF button to the OLED screen
extra_btn = Pin(18, Pin.IN, Pin.PULL_DOWN)
screen_btn = Pin(19, Pin.IN, Pin.PULL_DOWN)
ota_btn = Pin(22, Pin.IN, Pin.PULL_DOWN)

# Setup the server
server = AppServer(SSID, PASSWORD)

# Setup Ota classes
if oled_connected == True:
    main_file = OTAUpdater(firmware_url, "main.py", oled)
    html_file = OTAUpdater(firmware_url, "percentage.html", oled)

# Setup the Temp sensors
temp_connected = True

ds = ds18x20.DS18X20(onewire.OneWire(Pin(21)))
temp_sensors = ds.scan()

def read_temp():
    global out_temp
    global in_temp
    try:
        out_temp = round(ds.read_temp(temp_sensors[0]), 1)
        in_temp = round(ds.read_temp(temp_sensors[1]), 1)
        ds.convert_temp()
    except:
        out_temp = 0
        in_temp = 0

def ota_updater(ota_btn):
    main_file.update(ota_btn)
    html_file.update(ota_btn)

screen_btn.irq(trigger=screen_btn.IRQ_RISING, handler=oled.btn_func)
if oled_connected == True:
    ota_btn.irq(trigger=ota_btn.IRQ_RISING, handler=ota_updater)

while True:
    if(server.ip) == "0.0.0.0":
        server.stop()
        server.try_connect()
    if(angle_sensor == True):
        imu.read_sensor(caravan_width)
    if(temp_connected == True):
        read_temp()
    server.process_all(imu.pitch, imu.roll, imu.tilt, in_temp, out_temp, version)
    if(oled_connected == True):
        oled.process(server, imu, out_temp, in_temp)
    time.sleep(0.3)

print(version)