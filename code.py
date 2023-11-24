"""
Title: MTG Life Counter
Author: Logan D.G. Smith (@logandgsmtih)
Description: Track life and other relavant counters using a Feather and Wing
from Adafruit. Life is modified with a 4-switch rotary encoder in the QT-STEMMA
connector and displayed on a 128x64 OLED Wing. 
"""

import board
import displayio
import terminalio
import time

# Imports for rotary dial
from rainbowio import colorwheel
from digitalio import Pull
from adafruit_seesaw import seesaw, rotaryio, digitalio, neopixel

# Imports for OLED screen
from adafruit_display_text import label
import adafruit_displayio_sh1107

# Imports for feather helper functions
from feathers2neo import FeatherS2NeoHelper, MatrixMessage, MatrixAnimation

class Player:
    def __init__(self, name:str, color:list[int], position:int):
        self._name = name
        self._health = 40
        self._color = color # [0xrr, 0xgg, 0xbb]
        self._text_area = label.Label(terminalio.FONT, text=f'{self._name}: {self._health}', color=0xFFFFFF, x=0, y=position)

    @property
    def name(self) -> str:
        return self._name

    @property
    def health(self) -> int:
        return self._health

    @health.setter
    def health(self, value):
        self._health = value
        self.update_health()

    @property
    def color(self) -> str:
        return self._color

    @property
    def text_area(self) -> label.Label:
        return self._text_area

    @text_area.setter
    def text_area(self, value):
        self._text_area.text = value
    
    def get_health_string(self) -> str:
        return f'{self._name}: {self._health}'

    def increment_health(self) -> int:
        self._health += 1
        self.update_health()
        return self._health
    
    def decrement_health(self) -> int:
        self._health -= 1
        self.update_health()
        return self._health

    def update_health(self):
        if self._health > 0:
            self.text_area = f'{self._name}: {self._health}'
        else:
            self.text_area = f'{self._name}: Out!'

# Rotary encoder setup
i2c_stemma = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
seesaw = seesaw.Seesaw(i2c_stemma, addr=0x49)
encoders = [rotaryio.IncrementalEncoder(seesaw, n) for n in range(4)]
switches = [digitalio.DigitalIO(seesaw, pin) for pin in (12, 14, 17, 9)]
for switch in switches:
    switch.switch_to_input(Pull.UP) # Input and pullup resistor

# Neopixel setup on rotary breakout board
pixels = neopixel.NeoPixel(seesaw, 18, 4)
pixels.brightness = 0.85
last_positions = [0, 0, 0, 0]
colors = [0, 0, 0, 0]

# Display setup
displayio.release_displays()
# oled_reset = board.D9
i2c = board.I2C()  # uses board.SCL and board.SDA
display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
# button_c = digitalio.DigitalInOut(board.D5)
# button_c.direction = digitalio.Direction.INPUT

# SH1107 is vertically oriented 64x128
WIDTH = 128
HEIGHT = 64
BORDER = 2

display = adafruit_displayio_sh1107.SH1107(
    display_bus, width=WIDTH, height=HEIGHT, rotation=0
)

# Make the display context
splash = displayio.Group()
display.root_group = splash

# Player setup
players = [
    Player('Player 1', [0xff, 0x00, 0x00], 8),
    Player('Player 2',[0x00, 0xff, 0x00],  18),
    Player('Player 3',[0xff, 0x00, 0xff],  28),
    Player('Player 4',[0x00, 0xff, 0xff],  38)
]

# Initialize text areas for players
for player in players:
    splash.append(player.text_area)

text_area2 = label.Label(terminalio.FONT, text='HEALTH', scale=2, color=0xFFFFFF, x=32, y=56)
splash.append(text_area2)

# Setup LED Matrix
helper = FeatherS2NeoHelper()
helper.set_pixel_matrix_power(True)

matrix = MatrixMessage(helper.matrix)
matrix.scroll_direction = matrix.LEFT
matrix.display_rotation = 0
matrix.setup_message(' Start! ', delay=0.12, use_padding=True)

# Declare the R G B colors
r,g,b = 0,0,0
color_index = 0
next_color = 0.01 # color time delay step
next_color_step = 0.01

while True:
    # Update the color from the color wheel every 10ms
    if time.monotonic() > next_color + next_color_step:
        color_index += 1
        r,g,b = helper.rgb_color_wheel( color_index )
        next_color = time.monotonic()
        helper.pixel[0] = (r, g, b) # Set the color of the neopixel (not matrix)
        # If the color_index is divisible by 100, flip the state of the blue LED on IO13
        if color_index % 100 == 0:
            helper.blue_led = not helper.blue_led

    if matrix.show_message(color=[r,g,b], brightness=0.3, fade_out=0.2):
        pass

    positions = [encoder.position for encoder in encoders]
    for n, rotary_pos in enumerate(positions):
        if rotary_pos != last_positions[n]:
            if switches[n].value:  # Change the LED color if switch is not pressed
                if (rotary_pos > last_positions[n]): 
                    colors[n] += 8 # Advance forward throught he colorwheel
                    players[n].increment_health()
                else:
                    colors[n] -= 8  # Advance backward through the colorwheel.
                    players[n].decrement_health()
                colors[n] = (colors[n] + 256) % 256  # wrap around to 0-256
            last_positions[n] = rotary_pos


        # if switch is pressed, light up white, otherwise use the stored color
        if not switches[n].value:
            pixels[n] = 0xFFFFFF
            players[n].health = 40
            matrix.setup_message(' Life Reset! ', delay=0.01, use_padding=True)
        else:
            pixels[n] = colorwheel(colors[n])

    display.refresh()