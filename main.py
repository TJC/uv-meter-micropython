#!python
import ltr390
import utime
import uasyncio as asyncio
from machine import Pin, I2C, PWM
from PiicoDev_SSD1306 import *
from micropython import const
import math
from borked_keypad import BorkedKeypad


class UVMeter:
    def __init__(self):
        # Need a 330 ohm resistor to keep current just under 10 mA
        self.buzzer = PWM(Pin(9))
        self.buzzer.duty(0)
        self.buzzer.freq(4000)  # Apparently the optimal frequency for this unit

        # Set the pin number for the RGB LED
        self.rgb_led_num = const(21)

        # Note for OLED piicodev
        # blue = SDA (pin 2)
        # yellow = SCL (pin 1)

        # The red push-button
        self.push_button = Pin(4, Pin.IN, Pin.PULL_DOWN)

        # Give other devices a moment to power up and settle before issuing commands
        utime.sleep_ms(50)

        # This screen is 128x64
        # And the font is 8x8
        self.display = create_PiicoDev_SSD1306(bus=0, sda=Pin(2), scl=Pin(1))
        self.display.fill(1)
        self.display.text("UV Meter", 32, 28, 0)
        self.display.show()

        self.sensor_i2c = I2C(1, scl=Pin(39), sda=Pin(40), freq=100_000)
        self.ltr = ltr390.LTR390(self.sensor_i2c)

        self.ltr.set_uvs()
        self.ltr.set_gain(ltr390.eGain6)
        self.ltr.set_measure_rate(ltr390.e18bit, ltr390.e100ms)

        utime.sleep_ms(1000)

        self.keypad = BorkedKeypad()
        self.total = 0.0
        self.start_time = utime.time()
        self.target_string = ""
        self.target = 0
        self.warning_flash = 0
        self.rolling_average = self.ltr.uvs() / 256.0
        self.remain_mins = 0
        self.remain_secs = 0
        self.cycle_delay = const(500)  # milliseconds
        self.cycle_inverse = 1000 / self.cycle_delay

    async def sensorReadLoop(self):
        while True:
            v = self.ltr.uvs() / 1000.0
            self.total = self.total + v
            elapsed_time = utime.time() - self.start_time
            elapsed_minutes = math.floor(elapsed_time / 60.0)
            elapsed_seconds = elapsed_time % 60
            self.rolling_average = (self.rolling_average * 0.95) + (v * 0.05)
            if self.target == 0 or self.total >= self.target:
                self.remain_mins = 0
                self.remain_secs = 0
            elif self.rolling_average < 0.01:
                self.remain_mins = 999
                self.remain_secs = 99
            else:
                amt_remain = (
                    (self.target - self.total)
                    / self.rolling_average
                    / self.cycle_inverse
                )
                self.remain_mins = min(999, math.floor(amt_remain / 60.0))
                self.remain_secs = int(amt_remain) % 60

            self.display.fill(0)
            self.display.text("Instant: {:>7.3f}".format(v), 0, 0, 1)
            self.display.text("Total: {:>9.0f}".format(self.total), 0, 10, 1)
            self.display.text(f"Target: {self.target}", 0, 20, 1)
            self.display.text(
                "Elapsed: {:d}:{:02d}".format(elapsed_minutes, elapsed_seconds),
                0,
                30,
                1,
            )
            self.display.text(
                "Remain: {:d}:{:02d}".format(self.remain_mins, self.remain_secs),
                0,
                40,
                1,
            )

            if self.target > 0 and self.total >= self.target:
                self.display.fill_rect(0, 50, 127, 63, self.warning_flash)
                if self.warning_flash == 0:
                    self.buzzer.duty(512)
                    self.warning_flash = 1
                else:
                    self.buzzer.duty(0)
                    self.warning_flash = 0

            self.display.show()
            await asyncio.sleep_ms(self.cycle_delay)

    async def buttonReadLoop(self):
        while True:
            # Check for the reset button being pushed:
            if self.push_button.value() == 1:
                self.total = 0.0
                self.start_time = utime.time()
                self.target = 0
                self.target_string = ""
                self.buzzer.duty(0)

            # Check for keypad entry:
            key = self.keypad.keypresses_only()
            if key != None and key >= "0" and key <= "9":
                self.target_string = self.target_string + key
                self.target = int(self.target_string)
                # Need to reset the buzzer here, in case the target was increased
                self.buzzer.duty(0)

            await asyncio.sleep_ms(100)


try:
    uvm = UVMeter()
    asyncio.create_task(uvm.sensorReadLoop())
    asyncio.run(uvm.buttonReadLoop())
finally:
    asyncio.new_event_loop()
