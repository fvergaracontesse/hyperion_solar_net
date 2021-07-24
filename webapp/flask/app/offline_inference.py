from helpers.sn_helpers import (
    save_pickle_file,
    load_pickle_file,
    chunks
)
import os
import uuid
import numpy as np
from models_3 import Classification, Segmentation
from datetime import datetime

place = "berkeley"
coordinate_file = f"coordinates/coord_{place}"
local_image_directory = f"/home/ubuntu/images/"


tiles_poly = load_pickle_file("data/"+coordinate_file + "_img")

if not os.path.isfile("data/"+coordinate_file + "_classification"):
    print("START CLASSIFICATION:")
    time_start_classification = datetime.utcnow()
    model = Classification(models_folder="/home/ubuntu/models")
    classification_tiles = []
    for i, tile in enumerate(tiles_poly):
        tile["filename"] = local_image_directory + tile["file_name"]
    tiles_poly_chunks = chunks(tiles_poly, 20)
    for i, chunk in enumerate(tiles_poly_chunks):
        print("ITERATION N:",i)
        iteration_start = datetime.utcnow()
        classification_tiles.extend(model.predict(chunk, True))
        iteration_end = datetime.utcnow()
        time_elapsed_sec = (iteration_end - iteration_start).total_seconds()
        print("ITERATION TIME:", time_elapsed_sec)
    print("END CLASSIFICATION:")
    time_end_classification = datetime.utcnow()
    time_elapsed_classification_sec = (time_end_classification - time_start_classification).total_seconds()
    print("TOTAL TIME:", time_elapsed_classification_sec)
    save_pickle_file("data/"+coordinate_file + "_classification", classification_tiles)

if not os.path.isfile("data/"+coordinate_file + "_segmentation"):
    print("START Segmentation:", datetime.utcnow())
    time_start_segmentation = datetime.utcnow()
    classification_tiles = load_pickle_file("data/"+coordinate_file + "_classification")
    solar_panel_tiles = list(filter(lambda x: x["prediction"] == 1, classification_tiles))
    solar_panel_tiles_chunks = chunks(solar_panel_tiles, 40)
    segmentation_tiles = {}
    model = Segmentation(models_folder="/home/ubuntu/models")
    for i, chunk in enumerate(solar_panel_tiles_chunks):
        print("ITERATION N:",i)
        iteration_start = datetime.utcnow()
        result_tiles = model.predict(chunk, 21, True, place)
        segmentation_tiles.update(result_tiles)
        iteration_end = datetime.utcnow()
        time_elapsed_sec = (iteration_end - iteration_start).total_seconds()
        print("ITERATION TIME:", time_elapsed_sec)
    for i, tile in enumerate(classification_tiles):
        if tile["id"] in segmentation_tiles:
            classification_tiles[i] = segmentation_tiles[tile["id"]]
    print("END SEGMENTATION:")
    time_end_segmentation = datetime.utcnow()
    time_elapsed_segmentation_sec = (time_end_segmentation - time_start_segmentation).total_seconds()
    print("TOTAL TIME:", time_elapsed_segmentation_sec)
    save_pickle_file("data/"+coordinate_file + "_segmentation", classification_tiles)

tiles = load_pickle_file("data/"+coordinate_file + "_segmentation")

predicted = 0
panels_area = 0
panels_count = 0
for tile in tiles:
    if "prediction" in tile and tile["prediction"] == 1:
        predicted += 1
    if "mask_url" in tile:
        panels_area += tile['panels_area']
        panels_count += tile['panels_count']

print("TOTAL PREDICTED:", predicted)
print("TOTAL AREA:", panels_area)
print("TOTAL COUNT:", panels_count)


