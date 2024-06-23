#!python
import ltr390
import utime
from machine import Pin, I2C, PWM
from PiicoDev_SSD1306 import *
from micropython import const
import math
from borked_keypad import BorkedKeypad

## TODO for buzzer
# Need a 330 ohm resistor to keep current just under 10 mA
buzzer = PWM(Pin(9))
buzzer.duty(0)
buzzer.freq(4000)  # Apparently the optimal frequency for this unit

# Set the pin number for the RGB LED
rgb_led_num = const(21)

# Note for OLED piicodev
# blue = SDA (pin 2)
# yellow = SCL (pin 1)

# The red push-button
push_button = Pin(4, Pin.IN, Pin.PULL_DOWN)

# This screen is 128x64
# And the font is 8x8
display = create_PiicoDev_SSD1306(bus=0, sda=Pin(2), scl=Pin(1))

sensor_i2c = I2C(1, scl=Pin(39), sda=Pin(40), freq=100_000)
ltr = ltr390.LTR390(sensor_i2c)

ltr.set_uvs()
ltr.set_gain(ltr390.eGain6)
ltr.set_measure_rate(ltr390.e18bit, ltr390.e200ms)
utime.sleep_ms(500)  # initial reading can be off unless we do this

keypad = BorkedKeypad()
total = 0.0
start_time = utime.time()
target_string = ""
target = 0
warning_flash = 0
rolling_average = ltr.uvs() / 256.0
remain_mins = 0
remain_secs = 0
cycle_delay = const(300)  # milliseconds

while True:
    v = ltr.uvs() / 256.0
    total = total + v
    elapsed_time = utime.time() - start_time
    elapsed_minutes = math.floor(elapsed_time / 60.0)
    elapsed_seconds = elapsed_time % 60
    rolling_average = (rolling_average * 0.97) + (v * 0.03)
    if target == 0 or total >= target:
        remain_mins = 0
        remain_secs = 0
    elif rolling_average < 1:
        remain_mins = 999
        remain_secs = 99
    else:
        amt_remain = (target - total) / rolling_average / (1000 / cycle_delay)
        remain_mins = math.floor(amt_remain / 60.0)
        remain_secs = int(amt_remain) % 60

    display.fill(0)
    display.text("Instant: {:>7.1f}".format(v), 0, 0, 1)
    display.text("Total: {:>9.0f}".format(total), 0, 10, 1)
    display.text(f"Target: {target}", 0, 20, 1)
    display.text(
        "Elapsed: {:d}:{:02d}".format(elapsed_minutes, elapsed_seconds), 0, 30, 1
    )
    display.text("Remain: {:d}:{:02d}".format(remain_mins, remain_secs), 0, 40, 1)

    if target > 0 and total >= target:
        display.fill_rect(0, 50, 127, 63, warning_flash)
        buzzer.duty(512 * warning_flash)
        if warning_flash == 0:
            warning_flash = 1
        else:
            warning_flash = 0
    else:
        # Need to reset the buzzer here, in case the target was increased
        buzzer.duty(0)

    display.show()

    # Check for the reset button being pushed:
    if push_button.value() == 1:
        total = 0.0
        start_time = utime.time()
        target = 0
        target_string = ""
        buzzer.duty(0)

    # Check for keypad entry:
    key = keypad.keypresses_only()
    if key != None and key >= "0" and key <= "9":
        target_string = target_string + key
        target = int(target_string)

    utime.sleep_ms(cycle_delay)
