# Import necessary modules
import network
import time
import onewire
import ds18x20
from machine import Pin, I2C, ADC
from math import sqrt, atan, pow, pi, fabs
from imu import MPU6050
import ssd1306
from ws_connection import ClientClosedError
from ws_server import AppServer, ValueGenerator
from ota import OTAUpdater

# Define the Wi-Fi network SSID and password
ssid = 'Jacob'
password = 'Direstraits'
firmware_url = "https://raw.githubusercontent.com/Jacnil98/caravan/main/"
# Defines pixels on OLED display
oled_width = 128
oled_height = 64
# Defines global values for pitch angle, roll angle, the caravan width and the tilt amount
pitch = 0
roll = 0
caravan_lenght = 250
tilt = 0
# Global values for the inner and outside temp
out_temp = 0
in_temp = 0
screen_btn_toggle = 0
screen_btn_debounce_time = 0
ota_btn_debounce_time = 0

# Set up the I2C interface
i2c = machine.SoftI2C(scl=machine.Pin(1), sda=machine.Pin(0))
# Setup the oled display
oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)
#Fills all the pixels in the OLED displays with black
oled.fill(0)
oled.text(f"Starting", 0, 20)
oled.show()
# Create an instance of the MPU6050 sensor
imu = MPU6050(i2c)
pin = machine.Pin(16, machine.Pin.OUT)
pin.value(0) #set GPIO16 low to reset OLED
pin.value(1) #while OLED is running, must set GPIO16 in high
# Defines ON/OFF button to the OLED screen
screen_btn = Pin(18, Pin.IN, Pin.PULL_DOWN)
ota_btn = Pin(22, Pin.IN, Pin.PULL_DOWN)
# Setup the server
server = AppServer(ssid, password)
ota_updater = OTAUpdater(ssid, password, firmware_url, "main.py")
# Setup the Temp sensors
#ds = ds18x20.DS18X20(onewire.OneWire(Pin(21)))
#temp_sensors = ds.scan()

def read_sensor():
    global pitch
    global roll
    global tilt
    try:
        # Read accelerometer data from the sensor
        accel_x = imu.accel.x
        accel_y = imu.accel.y
        accel_z = imu.accel.z

        # Calculate pitch and roll angles from the accelerometer data
        roll = (atan(-accel_x / accel_z) * 180.0 / pi) - 1
        pitch = atan(accel_y / sqrt(pow(accel_x, 2) + pow(accel_z, 2))) * 180.0 / pi
        tilt = atan(pitch * pi / 180.0) * caravan_lenght
    except ZeroDivisionError:
            pass

def read_temp():
    global out_temp
    global in_temp
    out_temp = round(ds.read_temp(temp_sensors[0]), 1)
    in_temp = round(ds.read_temp(temp_sensors[1]), 1)
    ds.convert_temp()

def oled_process():
    oled.fill(0)
    oled.text(f" {server.ip}", 0,0)
    oled.text(f"VH:{round(pitch,1)}", 0, 10)
    oled.text(f"FB:{round(roll,1)}", 0, 20)
    oled.text(f"Kloss: {kloss_calc(int(tilt))} {int(fabs(tilt))}CM", 0, 30)
    oled.text(f"Temp Out: {out_temp}", 0, 40)
    oled.text(f"Temp In: {in_temp}", 0, 50)
    oled.show()
    
def kloss_calc(tilt):
    if tilt == 0:
        return "="
    elif tilt > 0:
        return "<-"
    else:
        return "->"

def oled_button(screen_btn):
    global screen_btn_toggle
    global screen_btn_debounce_time
    screen_btn_toggle = not screen_btn_toggle
    if((time.ticks_ms()-screen_btn_debounce_time) > 200):
        screen_btn_debounce_time=time.ticks_ms()
        if screen_btn_toggle:
            oled.poweroff()
        else:
            oled.poweron()
            
def ota_function(ota_btn):
    global ota_btn_debounce_time
    if((time.ticks_ms()-ota_btn_debounce_time) > 200):
        ota_btn_debounce_time=time.ticks_ms()
        oled.fill(0)
        oled.show()
        oled.text(f"Updating", 0, 20)
        oled.show()
        ota_updater.download_and_install_update_if_available()
        
        
screen_btn.irq(trigger=screen_btn.IRQ_RISING, handler=oled_button)
ota_btn.irq(trigger=ota_btn.IRQ_RISING, handler=ota_function)

while True:
    if(server.ip) == "0.0.0.0":
        server.stop()
        server.try_connect()
    read_sensor()
    ##read_temp() 
    server.process_all(pitch, roll, tilt)
    oled_process()
    time.sleep(0.5)


#V1
