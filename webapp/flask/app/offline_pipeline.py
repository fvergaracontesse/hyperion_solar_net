from helpers.sn_helpers import (
    get_state_tiles,
    get_json_file_from_s3,
    save_pickle_file,
    load_pickle_file,
    upload_file,
    sign_url,
    chunks
)
from dotenv import load_dotenv
from helpers.ts_gmaps import GoogleMap
import helpers.ts_maps as ts_maps
import helpers.ts_imgutil as ts_imgutil
import asyncio
import os
import uuid
import requests
from tensorflow.keras.preprocessing.image import img_to_array
from PIL import Image
from io import BytesIO
import numpy as np
from models import Classification, Segmentation
from datetime import datetime

load_dotenv()

place = "berkeley"
coordinate_file = f"coordinates/coord_{place}"
image_directory = f"data/images/{place}"
google_api_key = os.environ["GOOGLE_MAP_API_KEY"]
google_api_secret = os.environ["GOOGLE_MAP_API_SECRET"]
map_object = GoogleMap(google_api_key)
bucket = "solarnet-data"



# Generate tiles
if not os.path.isfile("data/"+coordinate_file):
    place_json = get_json_file_from_s3(f"{coordinate_file}.json")
    tiles_poly, place_poly, place_bounds = get_state_tiles(place_json, map_object, activate=True)
    for tile in tiles_poly:
        tile["hash_id"] = uuid.uuid4().hex
    save_pickle_file("data/"+coordinate_file, tiles_poly)
else:
    tiles_poly = load_pickle_file("data/"+coordinate_file)

if not os.path.isfile("data/"+coordinate_file + "_img"):
    i = 0
    for tile in tiles_poly:
        url = map_object.get_url(tile)
        signed_url = sign_url(url, google_api_secret)
        tile["url"] = signed_url
        response = requests.get(tile["url"])
        if response.status_code == 200:
            tile["file_name"] = place + "/" + tile["hash_id"] + ".jpg"
            content = response.content
            upload_file(tile["file_name"], bucket, content)
            tile["image_status"] = True
        else:
            print(response.status_code)
            print("No", tile["url"])
            tile["image_status"] = False
        i += 1
        print(i)
    save_pickle_file("data/"+coordinate_file + "_img", tiles_poly)

if not os.path.isfile("data/"+coordinate_file + "_classification"):
    model = Classification()
    classification_tiles = []
    tiles_poly = load_pickle_file("data/"+coordinate_file + "_img")
    tiles_poly_chunks = chunks(tiles_poly, 8)
    for chunk in tiles_poly_chunks:
        classification_tiles.extend(model.predict(chunk, True))
        print("Iteration:", datetime.now())
    save_pickle_file("data/"+coordinate_file + "_classification", classification_tiles)


if not os.path.isfile("data/"+coordinate_file + "_segmentation"):
    print("START Segmentation:", datetime.now())
    classification_tiles = load_pickle_file("data/"+coordinate_file + "_classification")
    solar_panel_tiles = list(filter(lambda x: x["prediction"] == 1, classification_tiles))
    solar_panel_tiles_chunks = chunks(solar_panel_tiles, 8)
    segmentation_tiles = {}
    model = Segmentation()
    i = 0
    for chunk in solar_panel_tiles_chunks:
        print("ITERATION: ", i)
        print("ITERATION TIME: ", datetime.now())
        result_tiles = model.predict(chunk, 21, True, place)
        segmentation_tiles.update(result_tiles)
        i += 1
    for i, tile in enumerate(classification_tiles):
        if tile["id"] in segmentation_tiles:
            print(segmentation_tiles[tile["id"]])
            classification_tiles[i] = segmentation_tiles[tile["id"]]
    save_pickle_file("data/"+coordinate_file + "_segmentation", classification_tiles)


# map_object.get_sat_maps(tiles_poly, loop, image_directory, uuid.uuid4().hex)
