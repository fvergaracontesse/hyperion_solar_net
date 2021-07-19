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
from helpers.sn_helpers import check_tile_center_against_bounds
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
from helpers.sn_helpers import (
    load_pickle_file,
)

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

# model_classification = Classification()


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

@app.route('/getplace', methods=['POST'])
def get_place():
    zoom = 21
    place = request.form.get("place")
    file_name = f'data/coordinates/coord_{place}_segmentation'
    tiles = load_pickle_file(file_name)
    zoom_factor = 2**21 / 2**zoom
    picHeight = 600/zoom_factor #Resulting image height in pixels (x2 if scale parameter is set to 2)
    picWidth = 600/zoom_factor

    xScale = math.pow(2, zoom) / (picWidth/256)
    yScale = math.pow(2, zoom) / (picHeight/256)
    total_tiles = 0
    total_tiles_sp = 0
    total_count_sp = 0
    total_sp_area = 0
    for i, tile in enumerate(tiles):
        tile['filename'] = f"s3://solarnet-data/{tile['file_name']}"
        if "mask_url" not in tile:
            tile['mask_url'] = ""
        else:
            tmp_url = tile['mask_url'].replace("img/", "")
            tile['mask_url'] = f"https://solarnet-data.s3.us-west-2.amazonaws.com/{tmp_url}"
        tile['bounds'] = ts_imgutil.getImageBounds(tile['w'], tile['h'], xScale, yScale, tile['lat'], tile['lng'])
        if "panels_area" in tile:
            total_sp_area += tile["panels_area"]
        if "panels_count" in tile:
            total_count_sp += tile["panels_count"]
        if "prediction" in tile and int(tile["prediction"])==1:
            total_tiles_sp += 1
    return json.dumps([tiles, total_tiles_sp, total_count_sp, round(total_sp_area,2), len(tiles), place])


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
    tiles_overlap, nx_overlap, ny_overlap, meters_overlap, h_overlap, w_overlap = map_object.make_tiles(bounds, overlap_percent=2, crop_tiles=crop_tiles)
    print(f" {len(tiles)} tiles, {nx} x {ny}, {meters} x {meters} m")
    # print(" Tile centers:")
    # for c in tiles:
    #   print("  ",c)

    tiles = [t for t in tiles if ts_maps.check_tile_against_bounds(t, bounds)]
    for i, tile in enumerate(tiles):
        tile['id'] = i


    tiles_overlap = [t for t in tiles_overlap if ts_maps.check_tile_against_bounds(t, bounds)]
    for i, tile_overlap in enumerate(tiles_overlap):
        tile_overlap['id'] = i

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

    meta_overlap = map_object.get_sat_maps(tiles_overlap, loop, tmpdirname, tmpfilename+"_overlap_")
    session['metadata_overlay'] = meta_overlap
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

    for i, tile_overlap in enumerate(tiles_overlap):
        tile_overlap['filename'] = tmpdirname+"/"+tmpfilename+"_overlap_"+str(i)+".jpg"
        tile_overlap['bounds'] = ts_imgutil.getImageBounds(tile_overlap['w'], tile_overlap['h'], xScale, yScale, tile_overlap['lat'], tile_overlap['lng'])

    if type == 'tiles':
        print(" returning number of tiles")
        return json.dumps(tiles)
    elif type == 'classification':
        print(" returning classification prediction")
        # tiles = model.predict(tiles)
        tiles_overlap = model_classification.predict(tiles_overlap)
        for tile in tiles:
            for tile_overlap in tiles_overlap:
                check = check_tile_center_against_bounds(tile, tile_overlap["bounds"])
                if check:
                    tile["prediction"] = tile_overlap["prediction"] if "prediction" not in tile else max(tile["prediction"], tile_overlap["prediction"])
        return json.dumps(tiles)
    elif type == 'segmentation':
        print(" returning segmentation prediction")
        # tiles = model.predict(tiles)
        tiles_overlap = model_classification.predict(tiles_overlap)
        for tile in tiles:
            for tile_overlap in tiles_overlap:
                check = check_tile_center_against_bounds(tile, tile_overlap["bounds"])
                if check:
                    tile["prediction"] = tile_overlap["prediction"] if "prediction" not in tile else max(tile["prediction"], tile_overlap["prediction"])
        tiles_pred = list(filter(lambda x: x["prediction"]==1, tiles))
        if len(tiles_pred) > 0:
            # our tiles for prediction are at zoom 21
            result_tiles = model_segmentation.predict(tiles_pred, 21)
            for i, tile in enumerate(tiles):
                if tile["id"] in result_tiles:
                    tiles[i] = result_tiles[tile["id"]]
                    if "mask_url" in tiles[i]:
                        tiles[i]["mask_url"] = f"/{tiles[i]['mask_url']}"
        else:
            print("NO TILES FOR PREDICTION")
        return json.dumps(tiles)

if __name__ == '__main__':
    app.run()
    print("HELLO MAIN")
    model_classification = Classification()
    #model_segmentation = Segmentation()

