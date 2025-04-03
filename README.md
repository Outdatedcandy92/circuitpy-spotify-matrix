# Spotify Currently Playing Display for 64x32 LED Matrix

Display the song you are currently playing on Spotify on a 64x32 LED matrix using a CircuitPython-supported microcontroller.
<p float="middle">
    <img src="https://github.com/upedd/circuitpy-spotify-matrix/blob/main/images/photo1.jpg?raw=true" width="400"/>
    <img src="https://github.com/upedd/circuitpy-spotify-matrix/blob/main/images/photo2.jpg?raw=true" width="400"/>
</p>
## Features
- Displays the title and artist(s) of the song.
- Shows scaled-down, colorful cover art.
- Includes a progress bar for the currently playing song.
- Supports on-device cover art fetching and decoding.
- Features 5-bit color depth.
- Operates on as little as 8 MB of RAM!

## Installation
1. Install CircuitPython on your board: [Guide](https://learn.adafruit.com/welcome-to-circuitpython/installing-circuitpython).
2. Clone this repository.
3. Copy `code.py` and the `fonts` folder to your device's root directory.
4. Copy the contents of the `libs` folder to your device's `libs` directory.
5. Create a new application on the Spotify Developer Dashboard: [Spotify Dashboard](https://developer.spotify.com/dashboard). Take note of the **Client ID** and **Client Secret**.
6. Visit [Spotify Refresh Token Generator](https://spotify-refresh-token-generator.netlify.app) to generate a refresh token with the `user-read-currently-playing` scope.
7. Open `settings.toml` in your device directory and paste in the following, filling in your details:
    ```toml
    CIRCUITPY_WIFI_SSID = "your Wi-Fi SSID"
    CIRCUITPY_WIFI_PASSWORD = "your Wi-Fi password"
    SPOTIFY_CLIENT_ID = "your Spotify Client ID"
    SPOTIFY_CLIENT_SECRET = "your Spotify Client Secret"
    SPOTIFY_REFRESH_TOKEN = "your generated refresh token"
    ```
8. Enjoy your Spotify Matrix Display!

## Modifying for Other Boards
This code has been tested with Hack Club's Neon but should work with any CircuitPython-compatible microcontroller connected to a 64x32 LED matrix. You might need to modify the `RGBMatrix` constructor call on line 138.
