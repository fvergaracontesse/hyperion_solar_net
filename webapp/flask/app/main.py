#
# SolarNet
# A tool for solar panels from satelite images
#
# SolarNet Team:
#
#
# Based on code done by TowerScout.

# import basic functionality
import helpers.ts_imgutil as ts_imgutil
from helpers.ts_gmaps import GoogleMap
from models import Classification, Segmentation
import helpers.ts_maps as ts_maps
from flask import Flask, render_template, send_from_directory, request, session, Response
from flask_session import Session
from waitress import serve
import json
import os
import zipfile
import ssl
import asyncio
import time
import tempfile
from shutil import rmtree
from PIL import Image, ImageDraw
import threading
import gc
import datetime
import sys
import math

MAX_TILES = 1000
MAX_TILES_SESSION = 100000

# map providers
providers = {
    'google': {'id': 'google', 'name': 'Google Maps'},
}

# Flask boilerplate stuff
app = Flask(__name__)
if app.config["ENV"] == "production":
    app.config.from_object("config.ProductionConfig")
else:
    app.config.from_object("config.DevelopmentConfig")

google_api_key = app.config["GOOGLE_API_KEY"]

loop = asyncio.new_event_loop()


# route for js code
@app.route('/img/<path:path>')
def send_img(path):
    return send_from_directory('img', path)

# route for js code
@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)


# route for js code
@app.route('/css/<path:path>')
def send_css(path):
    return send_from_directory('css', path)


# main page route
@app.route('/')
def map_func():

    # check for compatible browser
    offset = datetime.timezone(datetime.timedelta(hours=-5))  # Atlanta / CDC
    print("Main page loaded:", datetime.datetime.now(offset), "EST")
    print("Browser:", request.user_agent.string)
    # if not request.user_agent.browser in ['chrome','firefox']:
    #     return render_template('incompatible.html')
    # clean out any temp dirs
    if "tmpdirname" in session:
        rmtree(session['tmpdirname'], ignore_errors=True, onerror=None)
        del session['tmpdirname']

    # now render the map.html template, inserting the key
    return render_template('main.html',
                           google_api_key=google_api_key)


# cache control
# todo: ratchet this up after development


@app.after_request
def add_header(response):
    response.cache_control.max_age = 1
    return response


@app.route('/getobjects', methods=['POST'])
def get_objects():
    print(" session:", id(session))

    # check whether this session is over its limit
    if 'tiles' not in session:
        session['tiles'] = 0

    print("tiles queried in session:", session['tiles'])
    if session['tiles'] > MAX_TILES_SESSION:
        return "-1"

    # start time, get params
    start = time.time()
    type = request.form.get("type")
    bounds = request.form.get("bounds")
    height = float(request.form.get("height"))
    width = float(request.form.get("width"))
    zoom = int(request.form.get("zoom"))
    # zoom = 16
    print(" bounds:", bounds)
    print(" width:", width)
    print(" height:", height)
    print(" zoom:", zoom)

    # cropping
    crop_tiles = False

    # empty results
    results = []
    # create a map provider object
    map_object = GoogleMap(google_api_key)

    # divide map into tiles
    tiles, nx, ny, meters, h, w = map_object.make_tiles(bounds, crop_tiles=crop_tiles)
    print(f" {len(tiles)} tiles, {nx} x {ny}, {meters} x {meters} m")
    # print(" Tile centers:")
    # for c in tiles:
    #   print("  ",c)

    tiles = [t for t in tiles if ts_maps.check_tile_against_bounds(t, bounds)]
    for i, tile in enumerate(tiles):
        tile['id'] = i
    print(" tiles left after viewport and polygon filter:", len(tiles))

    if "tmpdirname" in session:
        rmtree(session['tmpdirname'], ignore_errors=True, onerror=None)
        print("cleaned up tmp dir", session['tmpdirname'])
        del session['tmpdirname']

    # make a new tempdir name and attach to session
    tmpdir = tempfile.TemporaryDirectory()
    tmpdirname = tmpdir.name
    tmpfilename = tmpdirname[tmpdirname.rindex("/")+1:]
    print("creating tmp dir", tmpdirname)
    session['tmpdirname'] = tmpdirname
    tmpdir.cleanup()
    os.mkdir(tmpdirname)
    print("created tmp dir", tmpdirname)

    # retrieve tiles and metadata if available
    meta = map_object.get_sat_maps(tiles, loop, tmpdirname, tmpfilename)
    session['metadata'] = meta
    print(" asynchronously retrieved", len(tiles), "files")

    # we create tiles at zoom=21, so factor the size by the current zoom
    zoom_factor = 2**21 / 2**zoom
    picHeight = 600/zoom_factor #Resulting image height in pixels (x2 if scale parameter is set to 2)
    picWidth = 600/zoom_factor

    xScale = math.pow(2, zoom) / (picWidth/256)
    yScale = math.pow(2, zoom) / (picHeight/256)

    for i, tile in enumerate(tiles):
        tile['filename'] = tmpdirname+"/"+tmpfilename+str(i)+".jpg"
        tile['bounds'] = ts_imgutil.getImageBounds(tile['w'], tile['h'], xScale, yScale, tile['lat'], tile['lng'])
        print("Tile bounds:", tile['bounds'])

    if type == 'tiles':
        print(" returning number of tiles")
        return json.dumps(tiles)
    elif type == 'classification':
        print(" returning classification prediction")
        model = Classification()
        tiles = model.predict(tiles)
        return json.dumps(tiles)
    elif type == 'segmentation':
        print(" returning segmentation prediction")
        model = Classification()
        tiles = model.predict(tiles)
        tiles = list(filter(lambda x: x["prediction"]==1, tiles))
        model = Segmentation()
        tiles = model.predict(tiles)
        print("TILES", tiles)
        return json.dumps(tiles)
