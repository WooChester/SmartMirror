from tkinter import *
import time
import requests
import json
from PIL import Image, ImageTk
import traceback
import spotipy
from flask import Flask, render_template, request, redirect, url_for
import _thread

xx_large_text_size = 96
x_large_text_size = 64
large_text_size = 48
medium_text_size = 28
small_text_size = 18
x_small_text_size = 12

# Spotify Key
client_id = "f41573f4ed3d4b4bb028675092222610"
secret_id = "0c31ffc1385148658e173032bc9bb354"
redirect_uri = "http://localhost:8888/"
scope = "user-modify-playback-state playlist-read-collaborative user-read-playback-state streaming app-remote-control"

alexa_id = 'd30c83c1-a672-4d2f-bd30-2261f68c8afe'

app = Flask(__name__)
app.debug = False
app.use_reloader = False
g_COMMAND = ''

g_playing = False


@app.route("/", methods=['POST', 'GET'])
def index():
    global g_playing
    if request.method == 'POST':
        global g_COMMAND
        g_COMMAND = request.form['command']
        time.sleep(1)
        if not g_playing:
            if g_COMMAND == "p":
                return render_template("pause.html")
            return render_template("play.html")
        else:
            if g_COMMAND == 'p':
                return render_template("play.html")
            else:
                try:
                    return redirect("")
                except Exception as e:
                    return "There was an issue"
    else:
        if g_playing:
            return render_template("pause.html")
        return render_template("play.html")


@app.route("/postmethod", methods=['POST'])
def vol_index():
    pass


def flask_thread():
    app.run(debug=False, host="0.0.0.0", port=9000)


def song_pixel_sz(song):
    alpha = {
        "A": 2, "B": 2, "C": 2, "D": 2, "E": 2, "F": 2,
        "G": 2, "H": 2, "I": 1, "J": 1, "K": 2, "L": 1,
        "M": 3, "N": 2, "O": 2, "P": 2, "Q": 2, "R": 2,
        "S": 2, "T": 2, "U": 2, "V": 2, "W": 2, "X": 2,
        "Y": 2, "Z": 2,
        "a": 1, "b": 2, "c": 2, "d": 2, "e": 1, "f": 1,
        "g": 2, "h": 2, "i": 1, "j": 1, "k": 2, "l": 1,
        "m": 2, "n": 2, "o": 1, "p": 2, "q": 2, "r": 1,
        "s": 2, "t": 1, "u": 2, "v": 2, "w": 2, "x": 2,
        "y": 1, "z": 2,
        " ": 1, "!": 1, "@": 2, "#": 2, "$": 1, "&": 2,
        "-": 1, "+": 2, "[": 1, "]": 1, "?": 2, ".": 1,

    }

    size = 0
    for letter in song:
        if letter in alpha:
            size += alpha[letter]
        else:
            size += 1
    return size * 4


class Clock(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')

        self.time_format = 12

        self.time = ''
        self.timeLbl = Label(self, bg='black', fg='white', font=('Helvetica', large_text_size), text=self.time)
        self.timeLbl.pack(side=TOP, anchor=E)

        self.day = ''
        self.dayLbl = Label(self, bg='black', fg='white', font=('Helvetica', medium_text_size), text=self.day)
        self.dayLbl.pack(side=TOP, anchor=E)

        self.date = ''
        self.dateLbl = Label(self, bg='black', fg='white', font=('Helvetica', medium_text_size), text=self.date)
        self.dateLbl.pack(side=TOP, anchor=E)

        self.tick()

    def tick(self):
        if self.time_format == 12:
            time2 = time.strftime("%I:%M %p")
        else:
            time2 = time.strftime("%H:%M")

        day2 = time.strftime("%A")
        date2 = time.strftime("%b %d, %Y")

        if time2 != self.time:
            self.time = time2
            self.timeLbl.config(text=self.time)
        if day2 != self.day:
            self.day = day2
            self.dayLbl.config(text=self.day)
        if date2 != self.date:
            self.date = date2
            self.dateLbl.config(text=self.date)

        self.after(200, self.tick)


class Spotify(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, bg='black')

        self.song_canvas = Canvas(self, bg='black', width=self.winfo_screenwidth() // 2.25,
                                  height=self.winfo_screenheight() // 8, highlightbackground='black')

        self.currently_playing = ''
        self.cnv_currently_playing = self.song_canvas.create_text(int(self.song_canvas['width']) // 1.9, 50,
                                                                  text=self.currently_playing,
                                                                  font=('Times New Roman', medium_text_size, 'bold'),
                                                                  fill='white', tags="marquee_song", anchor=CENTER)

        self.current_artist = ''
        self.cnv_current_artist = self.song_canvas.create_text(int(self.song_canvas['width']) // 1.9, 100,
                                                               text=self.current_artist,
                                                               font=('Times New Roman', small_text_size, 'bold'),
                                                               fill='white', tags="marquee_artist", anchor=CENTER)

        self.song_canvas.pack(side=TOP, anchor=CENTER, fill=X)
        self.song_canvas.grid(row=1, column=0, padx=(100, 10))

        self.song_length = 0
        self.idle = 0
        self.is_playing = False
        self.is_pause = True
        self.hidden = True

        self.update_song()
        self.display_song()

    def display_song(self):  # Handles what is being displayed
        if self.idle >= 600000:
            self.fade_music()
            self.update_song()
            self.after(5000, self.display_song)
        else:
            self.idle += 1000 // 40
            self.song_canvas.itemconfig(self.cnv_currently_playing, text=self.currently_playing)
            self.song_canvas.itemconfig(self.cnv_current_artist, text=self.current_artist)
            if len(self.currently_playing) > 56:
                x1, y1, x2, y2 = self.song_canvas.bbox("marquee_song")
                if x2 < 0 or y1 < 0:  # reset the coordinates
                    x1 = self.song_canvas.winfo_width() + song_pixel_sz(self.currently_playing)
                    y1 = self.song_canvas.winfo_height() // 2
                    self.song_canvas.coords("marquee_song", x1, y1)
                else:
                    self.song_canvas.move("marquee_song", -2, 0)
                self.after(1000 // 40, self.display_song)

            else:
                self.after(1000 // 40, self.display_song)
            self.song_length -= 1000 // 40
            if self.song_length % 5000 <= 24 or self.song_length <= 0:
                self.update_song()

    def update_song(self):  # Handles updating songs if changed

        token = spotipy.prompt_for_user_token("chesterwoo409", scope=scope, client_id=client_id,
                                              client_secret=secret_id,
                                              redirect_uri=redirect_uri)

        if token:
            sp = spotipy.Spotify(auth=token)
            cp = sp.currently_playing()
            global g_playing

            if cp is not None:

                currently_playing2 = cp['item']['name']
                current_artist = cp['item']['album']['artists'][0]['name']

                if cp['is_playing']:
                    g_playing = True
                    self.is_pause = False
                    self.idle = 0
                    self.hidden = False
                    for i in range(len(currently_playing2)):
                        currently_playing2 = currently_playing2[:i * 2 + 1] + ' ' + currently_playing2[i * 2 + 1:]
                    for i in range(len(current_artist)):
                        current_artist = current_artist[:i * 2 + 1] + ' ' + current_artist[i * 2 + 1:]
                    self.current_artist = current_artist

                    if self.currently_playing != currently_playing2:
                        self.currently_playing = currently_playing2
                        self.song_canvas.itemconfig(self.cnv_currently_playing, text=self.currently_playing)
                        self.song_canvas.itemconfig(self.cnv_current_artist, text=self.current_artist)
                        self.song_length = (cp['item']['duration_ms'] - cp['progress_ms']) + (
                                4 - (cp['item']['duration_ms'] - cp['progress_ms']) % 4)

                        if len(self.currently_playing) > 56:
                            self.song_canvas.coords("marquee_song", int(self.song_canvas['width']) // 2, 50)
                        else:
                            self.song_canvas.coords("marquee_song", int(self.song_canvas['width']) // 1.9, 50)
                            self.song_canvas.coords("marquee_artist", int(self.song_canvas['width']) // 1.9, 100)
                else:
                    self.is_pause = True
                    g_playing = False
                    self.song_length = (cp['item']['duration_ms'] - cp['progress_ms']) + (
                            4 - (cp['item']['duration_ms'] - cp['progress_ms']) % 4)
            else:
                self.song_length = 10000

    def fade_music(self):
        if not self.hidden:
            self.song_canvas.itemconfig(self.cnv_currently_playing, text='')
            self.song_canvas.itemconfig(self.cnv_current_artist, text='')
            self.hidden = True

    def play_pause(self):
        token = spotipy.prompt_for_user_token("chesterwoo409", scope=scope, client_id=client_id,
                                              client_secret=secret_id,
                                              redirect_uri=redirect_uri)
        if token:
            sp = spotipy.Spotify(auth=token)
            cp = sp.currently_playing()
            global g_playing

            if cp is not None and cp['is_playing'] is True:
                sp.pause_playback()
                self.is_pause = True
                g_playing = False

            else:
                active = False
                device_list = sp.devices()['devices']
                for d in device_list:
                    if d['is_active'] is True:
                        active = True
                device = None
                if not active:
                    for d in device_list:
                        if d["name"] == "Chester's Echo Dot":
                            d['is_active'] = True
                    device = alexa_id
                    # self.curr_volume = d['volume_percent']

                self.is_pause = False
                try:
                    sp.transfer_playback(device_id=device, force_play=True)
                    sp.shuffle(True)
                    g_playing = True
                    self.update_song()
                except Exception as e:
                    self.play_pause()

    def next_song(self):
        token = spotipy.prompt_for_user_token("chesterwoo409", scope=scope, client_id=client_id,
                                              client_secret=secret_id,
                                              redirect_uri=redirect_uri)
        if token:
            sp = spotipy.Spotify(auth=token)
            sp.next_track()
            self.update_song()

    def prev_song(self):
        token = spotipy.prompt_for_user_token("chesterwoo409", scope=scope, client_id=client_id,
                                              client_secret=secret_id,
                                              redirect_uri=redirect_uri)
        if token:
            sp = spotipy.Spotify(auth=token)
            sp.previous_track()
            self.update_song()

    @staticmethod
    def volume(command):
        token = spotipy.prompt_for_user_token("chesterwoo409", scope=scope, client_id=client_id,
                                              client_secret=secret_id,
                                              redirect_uri=redirect_uri)
        if token:
            sp = spotipy.Spotify(auth=token)

            for d in sp.devices()['devices']:
                if d['is_active']:
                    current_volume = d['volume_percent']
            if command == 'up':
                if current_volume >= 95:
                    sp.volume(100)
                else:
                    sp.volume(current_volume + 5)
            elif command == 'down':
                if current_volume <= 5:
                    sp.volume(0)
                else:
                    sp.volume(current_volume - 5)


class Weather(Frame):
    def __init__(self, parent):

        Frame.__init__(self, parent, bg='black')

        ################
        # Main Weather #
        ################

        self.forecastFrm = Frame(self, bg='black')
        self.forecastFrm.pack(side=TOP, anchor=CENTER)

        self.forecast_Canvas = Canvas(self.forecastFrm, bg='black', width=self.winfo_screenwidth() // 5,
                                      height=self.winfo_screenheight() // 10, highlightbackground='black')
        self.temperature = ''
        self.cnv_temperature = self.forecast_Canvas.create_text(int(self.forecast_Canvas['width']), 50,
                                                                text=self.temperature,
                                                                font=('Times New Roman', x_large_text_size, 'bold'),
                                                                fill='white', tags="marquee_temp", anchor='w')
        self.icon = ''
        self.photo = ''
        self.cnv_icon = self.forecast_Canvas.create_image(int(self.forecast_Canvas['width']) + int(self.forecast_Canvas['width'])//3, 50,
                                                          image=self.icon,
                                                          tags='marquee_icon', anchor='w')

        self.forecast_Canvas.pack(side=TOP, anchor=CENTER)

        ###################
        # Toggled Details #
        ###################

        self.detailFrm = Frame(self, bg='black')
        self.detailFrm.pack(side=TOP, anchor=CENTER)

        self.detail_canvas = Canvas(self.detailFrm, bg='black', width=self.winfo_screenwidth() // 5,
                                    height=self.winfo_screenheight() // 5, highlightbackground='black')

        self.location = ''
        self.cnv_location = self.detail_canvas.create_text(int(self.detail_canvas['width']) // 2.5, - 130,
                                                           text=self.location,
                                                           font=('Helvetica', small_text_size, 'bold'),
                                                           fill='white', tags="marquee_loc", anchor='w')

        self.line_bar = self.detail_canvas.create_line(
            int(self.forecast_Canvas['width'])//4, -1*int(self.forecast_Canvas['width'])//3,
            int(self.forecast_Canvas['width']), -1*int(self.forecast_Canvas['width'])//3, fill='black', tags="marquee_line")

        self.wind_speed = ''
        self.cnv_wind_speed = self.detail_canvas.create_text(int(self.detail_canvas['width']) // 3, - 70,
                                                             text=self.wind_speed,
                                                             font=('Helvetica', x_small_text_size, 'bold'),
                                                             fill='white', tags="marquee_ws", anchor='w')
        self.uv_index = ''
        self.cnv_uv_index = self.detail_canvas.create_text(int(self.detail_canvas['width']) // 3, - 40,
                                                           text=self.uv_index,
                                                           font=('Helvetica', x_small_text_size, 'bold'),
                                                           fill='white', tags="marquee_uv", anchor='w')

        self.rain_chance = ''
        self.cnv_rain_chance = self.detail_canvas.create_text(int(self.detail_canvas['width']) // 3, - 10,
                                                              text=self.rain_chance,
                                                              font=('Helvetica', x_small_text_size, 'bold'),
                                                              fill='white', tags="marquee_rain", anchor='w')
        # IMPLEMENT FEELS LIKE:

        self.detail_canvas.pack(side=TOP, anchor=CENTER)

        # Icon for forecast matching
        self.icon_lookup = {
            'Sunny': "assets/Sun.png",  # clear sky day
            'Clear night': "assets/Moon.png",  # clear sky night

            'wind': "assets/Wind.png",  # wind

            'Overcast': "assets/Cloud.png",  # cloudy day
            'Overcast night': "assets/Cloud.png",

            'Partly cloudy': "assets/PartlySunny.png",  # partly cloudy day
            'Partly cloudy night': "assets/PartlyMoon.png",  # scattered clouds night

            'Light Rain': "assets/Rain.png",  # rain day
            'Rain': "assets/Rain.png",
            'Light Rain night': "assets/Rain.png",
            'Rain night': "assets/Rain.png",

            'Snow': "assets/Snow.png",  # snow day
            'Patchy light snow': "assets/Snow.png",  # sleet day
            'Moderate snow': "assets/Snow.png",
            'Snow night': "assets/Snow.png",
            'Patchy light snow night': "assets/Snow.png",  # sleet day
            'Moderate snow night': "assets/Snow.png",

            'Mist': "assets/Haze.png",  # fog day
            'Mist night': "assets/Haze.png",

            'thunderstorm': "assets/Storm.png",  # thunderstorm
            'tornado': "assests/Tornado.png",  # tornado
            'hail': "assests/Hail.png"  # hail
        }

        self.details_out = False
        self.hidden = True

        self.idle = 0

        self.get_weather()

    def get_weather(self):
        # Get Weather for Location through IP
        self.idle += 1
        weather_req_url = "http://api.weatherstack.com/current?access_key=e25e4a061557ee8da674b5b01d202ba9&query=%s" \
                          % self.get_ip()
        r = requests.get(weather_req_url)
        weather_obj = json.loads(r.text)
        degree_sign = u'\N{DEGREE SIGN}'

        temperature2 = "%s%s" % (str(int(weather_obj['current']['temperature'] * 9 / 5 + 32)), degree_sign)
        weather_desc = "%s" % (str(weather_obj['current']['weather_descriptions'][0]))
        wind_speed2 = "Wind: %smph %s" % (weather_obj['current']['wind_speed'], weather_obj['current']['wind_dir'])
        uv2 = "UV Index: %s" % weather_obj['current']['uv_index']
        rain_chance2 = "Chance of Rain: %s %%" % (weather_obj['current']['precip'])
        location2 = "%s" % weather_obj['location']['name']
        for i in range(len(location2)):
            location2 = location2[:i * 2 + 1] + ' ' + location2[i * 2 + 1:]

        try:
            weather_desc = weather_desc[:weather_desc.index(',')]
        except ValueError:
            pass
        if weather_obj['current']['is_day'] == 'no':
            weather_desc += " night"

        icon2 = self.icon_lookup[weather_desc]

        if icon2 is not None:
            if self.icon != icon2:
                self.icon = icon2
        else:
            # remove image
            print("No icon?!")

        if self.temperature != temperature2:
            self.temperature = temperature2

        if self.location != location2:
            self.location = location2

        if self.wind_speed != wind_speed2:
            self.wind_speed = wind_speed2

        if self.uv_index != uv2:
            self.uv_index = uv2

        if self.rain_chance != rain_chance2:
            self.rain_chance = rain_chance2

        self.after(1800000, self.get_weather)
        if self.idle > 2 and not self.hidden:
            self.toggle_weather()

    @staticmethod
    def get_ip():
        try:
            ip_url = "http://jsonip.com/"
            req = requests.get(ip_url)
            ip_json = json.loads(req.text)
            return ip_json['ip']
        except Exception as e:
            traceback.print_exc()
            return "Error: %s. Cannot get ip." % e

    def toggle_weather(self):
        if self.hidden:
            self.idle = 0
            self.forecast_Canvas.itemconfig(self.cnv_temperature, text=self.temperature)
            im = Image.open(self.icon)
            im = im.resize((100, 100), Image.ANTIALIAS)
            im = im.convert('RGB')
            self.photo = ImageTk.PhotoImage(im)
            self.forecast_Canvas.itemconfig(self.cnv_icon, image=self.photo)

            self.forecast_slide()

        else:
            self.forecast_Canvas.itemconfig(self.cnv_temperature, text="")
            self.forecast_Canvas.itemconfig(self.cnv_icon, image='')
            self.forecast_Canvas.move("marquee_temp", 200, 0)
            self.forecast_Canvas.move("marquee_icon", 200, 0)
            if self.details_out:
                self.toggle_weather_details()
        self.hidden = not self.hidden

    def toggle_weather_details(self):
        if not self.hidden:
            # Toggle details
            if not self.details_out:
                self.detail_canvas.itemconfig(self.cnv_location, text=self.location)
                self.detail_canvas.itemconfig(self.cnv_wind_speed, text=self.wind_speed)
                self.detail_canvas.itemconfig(self.cnv_uv_index, text=self.uv_index)
                self.detail_canvas.itemconfig(self.cnv_rain_chance, text=self.rain_chance)
                self.detail_canvas.itemconfig(self.line_bar, fill='white')

                self.detail_slide()

            else:
                self.detail_canvas.itemconfig(self.cnv_location, text='')
                self.detail_canvas.itemconfig(self.line_bar, fill='black')
                self.detail_canvas.itemconfig(self.cnv_wind_speed, text='')
                self.detail_canvas.itemconfig(self.cnv_uv_index, text='')
                self.detail_canvas.itemconfig(self.cnv_rain_chance, text='')
                self.detail_canvas.move("marquee_loc", 0, -110)
                self.detail_canvas.move("marquee_line", 0, -110)
                self.detail_canvas.move("marquee_ws", 0, -110)
                self.detail_canvas.move("marquee_uv", 0, -110)
                self.detail_canvas.move("marquee_rain", 0, -110)
            self.details_out = not self.details_out

    def forecast_slide(self):
        x, y = self.forecast_Canvas.coords(self.cnv_temperature)
        if x >= self.forecast_Canvas.winfo_screenwidth() // 18:
            self.forecast_Canvas.move("marquee_temp", -3, 0)
            self.forecast_Canvas.move("marquee_icon", -3, 0)
            self.after(10, self.forecast_slide)

    def detail_slide(self):
        x, y = self.detail_canvas.coords(self.cnv_location)
        if y <= self.detail_canvas.winfo_screenheight() // 24:
            self.detail_canvas.move("marquee_loc", 0, 1.7)
            self.detail_canvas.move("marquee_line", 0, 1.7)
            self.detail_canvas.move("marquee_ws", 0, 1.7)
            self.detail_canvas.move("marquee_uv", 0, 1.7)
            self.detail_canvas.move("marquee_rain", 0, 1.7)
            self.after(10, self.detail_slide)

    def toggle_full_weather(self):
        self.toggle_weather()
        self.toggle_weather_details()


class FullscreenWindow:
    def __init__(self):
        self.tk = Tk()
        self.tk.configure(bg='black')
        self.fs = True
        #self.tk.attributes("-fullscreen", self.fs)

        self.topFrame = Frame(self.tk, bg='black')
        self.topFrame.pack(side=TOP, fill=X)

        self.clock = Clock(self.topFrame)
        self.clock.pack(side=LEFT, anchor=N, padx=40, pady=40)

        self.spotify = Spotify(self.topFrame)
        self.spotify.pack(side=LEFT, anchor=N, pady=40)

        self.weather = Weather(self.topFrame)
        self.weather.pack(side=LEFT, anchor=N, padx=40, pady=40)

        # Bindings #
        self.tk.bind("<Return>", self.toggle_fullscreen)
        self.tk.bind("<Escape>", self.toggle_fullscreen)
        self.tk.bind("a", lambda event: self.weather.toggle_weather())
        self.tk.bind("s", lambda event: self.weather.toggle_weather_details())
        self.tk.bind("d", lambda event: self.weather.toggle_full_weather())
        self.tk.bind("]", lambda event: self.spotify.play_pause())
        self.tk.bind("[", lambda event: self.spotify.prev_song())
        self.tk.bind("\\", lambda event: self.spotify.next_song())
        self.tk.bind("=", lambda event: self.spotify.volume("up"))
        self.tk.bind("-", lambda event: self.spotify.volume("down"))

        self.check_web()

    def toggle_fullscreen(self, event=None):
        self.fs = not self.fs  # Just toggling the boolean
        self.tk.attributes("-fullscreen", self.fs)

    def check_web(self):
        global g_COMMAND
        if g_COMMAND != '':
            print(g_COMMAND)
            if g_COMMAND == '<<':
                self.spotify.prev_song()
            elif g_COMMAND == '>>':
                self.spotify.next_song()
            elif g_COMMAND == 'p':
                self.spotify.play_pause()
            elif g_COMMAND == "+":
                self.spotify.volume('up')
            elif g_COMMAND == "-":
                self.spotify.volume("down")
            elif g_COMMAND == "Toggle Weather":
                self.weather.toggle_full_weather()
            f = open("command_times.txt", "a")
            f.write("\nCommand: {}\nTime: {}\n".format(g_COMMAND, self.clock.date + " at " + self.clock.time))
            f.close()

            g_COMMAND = ''
        self.tk.after(500, self.check_web)


if __name__ == '__main__':
    w = FullscreenWindow()
    _thread.start_new_thread(flask_thread, ())
    w.tk.mainloop()
