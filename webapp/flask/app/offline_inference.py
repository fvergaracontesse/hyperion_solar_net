from helpers.sn_helpers import (
    save_pickle_file,
    load_pickle_file,
    chunks
)
import os
import uuid
import numpy as np
from models import Classification, Segmentation
from datetime import datetime

place = "berkeley"
coordinate_file = f"coordinates/coord_{place}"
local_image_directory = f"/home/ubuntu/images/"


tiles_poly = load_pickle_file("data/"+coordinate_file + "_img")

if not os.path.isfile("data/"+coordinate_file + "_classification"):
    print("START CLASSIFICATION:")
    time_start_classification = datetime.utcnow()
    model = Classification()
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

