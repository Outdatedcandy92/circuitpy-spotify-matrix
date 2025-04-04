# MIT License

# Copyright (c) 2025 uped

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import adafruit_display_text.label
import board
import displayio
import framebufferio
import rgbmatrix
import terminalio
from jpegio import JpegDecoder
from adafruit_bitmap_font import bitmap_font
import gc
import os
import adafruit_connection_manager
import wifi
import adafruit_requests
import time
import binascii

def base64_encode(input_string):
    encoded_bytes = binascii.b2a_base64(input_string.encode("utf-8")).strip()
    return encoded_bytes.decode("utf-8")

class CurrentlyPlayingInfo:
    def __init__(self, name, artists, cover_url, id, progress, duration):
        self.name = name
        self.artists = artists
        self.cover_url = cover_url
        self.id = id
        self.progress = progress
        self.duration = duration

class SpotifyClient:
    def __init__(self, client_id, client_secret, refresh_token, err_handler):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.err_handler = err_handler

    def fetch_access_token(self):
        url = "https://accounts.spotify.com/api/token"
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': spotify_refresh_token
        }
        client = spotify_client_id + ':' + spotify_client_secret
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': 'Basic ' + base64_encode(client)
        }

        response = requests.post(url, data=payload, headers=headers)
        if response.status_code != 200:
            self.err_handler(f'Failed to fetch access token from spotify. Code returned: {response.status_code}')
            return False

        response_data = response.json()

        self.access_token = response_data.get('access_token')
        if 'refresh_token' in response_data:
            self.refresh_token = response_data['refresh_token']
        return True

    def get_currently_playing(self, is_retry=False):
        if not hasattr(self, 'access_token'):
            if not self.fetch_access_token():
                return None

        url = "https://api.spotify.com/v1/me/player/currently-playing"
        headers = {
            'Authorization': 'Bearer ' + self.access_token
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 204:
            return None
        elif response.status_code == 401 and not is_retry:
            print("Spotify returned 401! Trying to reauth....")
            if not self.fetch_access_token():
                return None
            return self.get_currently_playing(True)
        elif response.status_code != 200:
            self.err_handler(f'Failed to get currently playing song data from spotify. Code returned: {response.status_code}')
            return None

        response_data = response.json()
        response_item = response_data['item']
        if not response_item:
            return None
        cover_url = ""
        for item in response_item['album']['images']:
            if item['width'] == 64 and item['height'] == 64:
                cover_url = item['url']

        return CurrentlyPlayingInfo(
            response_item['name'],
            ', '.join(artist['name'] for artist in response_item['artists']),
            cover_url,
            response_item['id'],
            response_data['progress_ms'],
            response_item['duration_ms']
        )

class Display:
    line1_y = 8
    line2_y = 20
    progress_x = 34
    progress_y = 28
    progress_primary_color = 0x1DB954
    progress_secondary_color = 0x18181b
    progress_width = 28


    def __init__(self):
        self.enabled = False
        self.has_error = False
        displayio.release_displays()
        
        base_color = 0xFFFFFF
        # Adjust the color using the brightness factor
        adjusted_color = self.adjust_brightness(base_color, 0.1)
        
        # Customize here!
        matrix = rgbmatrix.RGBMatrix(
            width=64, height=32, bit_depth=5,
            rgb_pins=[board.IO1, board.IO2, board.IO3, board.IO5, board.IO4, board.IO6],
            addr_pins=[board.IO8, board.IO7, board.IO10, board.IO9],
            clock_pin=board.IO12, latch_pin=board.IO11, output_enable_pin=board.IO13)

        self.display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)

        roboto_7pt = bitmap_font.load_font("fonts/Roboto-Regular-7pt.bdf")
        roboto_5pt = bitmap_font.load_font("fonts/Roboto-Regular-5pt.bdf")

        self.line1 = adafruit_display_text.label.Label(
            roboto_7pt,
            color=adjusted_color)
        self.line1.x = self.display.width
        self.line1.y = self.line1_y

        self.line2 = adafruit_display_text.label.Label(
            roboto_5pt,
            color=adjusted_color
        )
        self.line2.x = self.display.width
        self.line2.y = self.line2_y

        self.image_bitmap = displayio.Bitmap(32, 32, 65536)
        image_tile_grid = displayio.TileGrid(self.image_bitmap, pixel_shader=displayio.ColorConverter(input_colorspace=displayio.Colorspace.RGB565_SWAPPED))

        self.progress_bitmap = displayio.Bitmap(self.progress_width, 1, 2)
        progress_palette = displayio.Palette(2)
        progress_palette[0] = self.progress_primary_color
        progress_palette[1] = self.progress_secondary_color
        progress_tile_grid = displayio.TileGrid(self.progress_bitmap, pixel_shader = progress_palette)
        progress_tile_grid.x = self.progress_x
        progress_tile_grid.y = self.progress_y
        self.progress_bar_value = 0.0

        self.display_group = displayio.Group()
        self.display_group.append(self.line1)
        self.display_group.append(self.line2)
        self.display_group.append(image_tile_grid)
        self.display_group.append(progress_tile_grid)

        self.jpeg_decoder = JpegDecoder()
        
    def adjust_brightness(self, hex_color, factor):
        # Extract RGB components from the hex color
        r = (hex_color >> 16) & 0xFF
        g = (hex_color >> 8) & 0xFF
        b = hex_color & 0xFF

        # Adjust the brightness by multiplying each component by the factor
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)

        # Ensure the values stay within the valid RGB range (0-255)
        r = min(max(r, 0), 255)
        g = min(max(g, 0), 255)
        b = min(max(b, 0), 255)

        # Return the new color as a hex value
        return (r << 16) | (g << 8) | b    

    def show_error(self, msg):
        self.enable()
        self.has_error = True
        self.line1.text = "Error"
        self.line1.color = 0xFF0000
        self.line2.text = msg
        self.line2.color = 0xFF0000

    
    def load_image_from_url(self, url):
        gc.collect()
        response = requests.get(url)
        self.jpeg_decoder.open(response.content)
        self.jpeg_decoder.decode(self.image_bitmap, 1) # Assumes the image we fetched is 64x64 and downscales it by 2^1 to 32x32
        
        brightness_factor = 0.3
        width = self.image_bitmap.width
        height = self.image_bitmap.height

        for y in range(height):
            for x in range(width):
                # Get the pixel value in RGB565 format
                pixel_value = self.image_bitmap[x, y]

                # Convert RGB565 to RGB888 (inline implementation of rgb565_swapped_to_rgb888)
                # Swap bytes (for little-endian data from CircuitPython)
                swapped = ((pixel_value & 0xFF) << 8) | ((pixel_value >> 8) & 0xFF)
                # Extract RGB components
                r = ((swapped >> 11) & 0x1F) * 255 // 31
                g = ((swapped >> 5) & 0x3F) * 255 // 63
                b = (swapped & 0x1F) * 255 // 31

                # Apply brightness reduction
                r = int(r * brightness_factor)
                g = int(g * brightness_factor)
                b = int(b * brightness_factor)

                # Convert back to RGB565
                dimmed_pixel_value = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

                # Swap bytes back to RGB565 swapped format
                dimmed_pixel_value_swapped = ((dimmed_pixel_value & 0xFF) << 8) | ((dimmed_pixel_value >> 8) & 0xFF)

                # Update the pixel in the bitmap
                self.image_bitmap[x, y] = dimmed_pixel_value_swapped

    def scroll(self, line):
        line.x = line.x - 1
        line_width = line.bounding_box[2]
        if line.x < -line_width + 32:
            line.x = self.display.width

    def disable(self):
        if not self.has_error:
            self.enabled = False
            self.display.root_group = None
    
    def enable(self):
        self.enabled = True
        self.display.root_group = self.display_group

    def update(self):
        self.scroll(self.line1)
        self.scroll(self.line2)

        for x in range(0, int(self.progress_bar_value * self.progress_width)):
            self.progress_bitmap[x, 0] = 0
        for x in range(int(self.progress_bar_value * self.progress_width), self.progress_width):
            self.progress_bitmap[x, 0] = 1

        self.display.refresh(target_frames_per_second=5,minimum_frames_per_second=0)

        
display = Display()

ssid = os.getenv("CIRCUITPY_WIFI_SSID")
password = os.getenv("CIRCUITPY_WIFI_PASSWORD")

spotify_refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN")
spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
spotify_request_timeout = int(os.getenv("SPOTIFY_REQUEST_TIMEOUT") or "5")

if spotify_refresh_token == None or spotify_client_id == None or spotify_client_secret == None:
    display.show_error("Missing spotify credentials")

pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
requests = adafruit_requests.Session(pool, ssl_context)



print(f"\nConnecting to {ssid}...")
try:
    wifi.radio.connect(ssid, password)
except OSError as e:
    display.show_error("No wifi connection")
print("Connected to Wifi!")


spotify_client = SpotifyClient(spotify_client_id, spotify_client_secret, spotify_refresh_token, display.show_error)

last_update_time = 0
last_id = 0

while True:
    if time.monotonic() > last_update_time + spotify_request_timeout and not display.has_error:
        gc.collect()
        currently_playing = None
        try: 
            currently_playing = spotify_client.get_currently_playing()
        except MemoryError as e:
            print("Failed to allocate memory!")
        gc.collect()
        if currently_playing == None:
            display.disable()
        else:
            if not display.enabled:
                display.enable()
            display.progress_bar_value = currently_playing.progress / currently_playing.duration
            if currently_playing.id != last_id:
                display.load_image_from_url(currently_playing.cover_url)
                last_id = currently_playing.id
                display.line1.text = currently_playing.name
                display.line2.text = currently_playing.artists
        last_update_time = time.monotonic()
    display.update()
