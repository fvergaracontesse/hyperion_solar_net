"""Use this class for predictions with efficient net."""
import numpy as np
from PIL import Image
import cv2
from json import JSONEncoder
import json
import math
import uuid
from scipy.ndimage import zoom as zm
import os
import requests

from helpers.sn_helpers import (
    chunks,
    get_image_stream_from_s3,
    sigmoid
)


class NumpyArrayEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return JSONEncoder.default(self, obj)


class Classification:

    def __init__(self, models_folder='models', model_en='b7', from_server=True):
        self.params_dict = {
                # Coefficients:   res
                'b0': (224, 224),
                'b1': (240, 240),
                'b2': (260, 260),
                'b3': (300, 300),
                'b4': (380, 380),
                'b5': (456, 456),
                'b6': (528, 528),
                'b7': (600, 600),
                'b8': (672, 672),
                'l2': (800, 800),
            }
        self.model_en = model_en
        self.image_size = self.params_dict[self.model_en]
        self.batch_size = 20

    def predict(self, tiles, fromS3=False):
        batched_input = np.zeros((len(tiles), 600, 600, 3), dtype=np.float32)
        for i, tile in enumerate(tiles):
            tmp_image = cv2.imread(tile["filename"])
            resized = cv2.resize(tmp_image, (600, 600))[..., ::-1].astype(np.float32)
            x = np.expand_dims(resized.reshape(600, 600, 3), axis=0)
            batched_input[i, :] = x
        batches = chunks(batched_input.tolist(), 10)
        predictions = []
        for batch in batches:
            data = json.dumps({"signature_name": "serving_default", "instances": batch})
            headers = {"content-type": "application/json"}
            json_response = requests.post('http://localhost:8501/v1/models/enb7_classifier:predict', data=data, headers=headers)
            preds = json.loads(json_response.text)["predictions"]
            preds = sigmoid(np.array(preds))
            predictions.extend(np.where(preds < 0.5, 0, 1).tolist())
        for i, tile in enumerate(tiles):
            tile["prediction"] = predictions[i][0]
        return tiles


class Segmentation:

    def __init__(self, models_folder='models', model_en='b7'):
        self.model_en = model_en
        self.image_width = 512
        self.image_height = 512
        self.batch_size = 20
        self.segmentation_image_folder = 'img/segmentation'

    def get_panels_area_and_count(self, latitude, zoom, matrix):
        '''
        :type latitude: int
        :type zoom: int
        :type matrix: List[int]
        :rtype panel_area: int
        :rtype panel_count: int
        function input is the location latitude, zoom and a matrix of 0 and 1
        integers denoting if pixel contains solar panel. function outputs the total
        solar panel area and the solar panel count in the image
        '''
        # initialize as np array and count non-zeros equal to 1
        np_matrix = np.array(matrix)
        one_count = np.count_nonzero(np_matrix == 1)
        # calculate meters per pixel per Google calculations
        meters_per_pixel = 156543.03392 * math.cos(latitude * math.pi / 180) / math.pow(2, zoom)
        # convert to feet per pixel
        feet_per_pixel = 3.28084 * meters_per_pixel
        # calculate area per pixel in feet^2
        area_per_pixel = feet_per_pixel * feet_per_pixel
        # calculate the total area of solar panels in image
        panel_area = one_count * area_per_pixel

        # initialize the standard panel area (residential = 17.6, commercial = 20.85)
        # Solar panels are roughly 5 feet long and 3 feet wide, with some small variation by manufacturer
        # from https://news.energysage.com/average-solar-panel-size-weight/
        area_per_panel = 17.6
        # calculate the number of panels rounding to whole number
        panel_count = round((panel_area / area_per_panel), 0)
        panel_area = round(panel_area, 2)
        return(panel_area, panel_count)

    def predict(self, tiles, zoom, fromS3=False, place=None):
        images = np.empty((len(tiles), self.image_width, self.image_height, 3), dtype=np.float32)
        if place:
            if not os.path.exists(f'{self.segmentation_image_folder}/{place}'):
                os.makedirs(f'{self.segmentation_image_folder}/{place}')
            folder = f'{self.segmentation_image_folder}/{place}'
        else:
            folder = f'{self.segmentation_image_folder}'
        for i, tile in enumerate(tiles):
            if not fromS3:
                tmp_image = cv2.imread(tile['filename'], cv2.IMREAD_COLOR)/255
            else:
                tmp_image = cv2.imdecode(np.asarray(bytearray(get_image_stream_from_s3(tile["file_name"]))), cv2.IMREAD_COLOR)/255
            resized = cv2.resize(tmp_image, (self.image_width, self.image_height))
            image = resized.reshape(self.image_width, self.image_height, 3)
            images[i, ...] = image
        batches = chunks(images.tolist(), 8)
        predictions = []
        for batch in batches:
            data = json.dumps({"signature_name": "serving_default", "instances": batch})
            headers = {"content-type": "application/json"}
            json_response = requests.post('http://localhost:8501/v1/models/unet_segmentation:predict', data=data, headers=headers)
            preds = json.loads(json_response.text)["predictions"]
            predictions.extend(np.where(np.array(preds) < 0.5, 0, 1).astype(np.float32))
        for i, prediction in enumerate(predictions):
            predicted_matrix = np.array(Image.fromarray(prediction.reshape(self.image_width, self.image_height)).resize((600, 600)))

            # convert mask to a 4D image
            array = (prediction * 255).astype(np.uint8).reshape(self.image_width, self.image_height, 1)
            array = zm(array, (1, 1, 4))
            # get row column value of pixels having value 1
            row_col = np.where(array > 0)
            if len(row_col) > 0:
                im_coords = list(zip(row_col[0], row_col[1]))
                for cord in im_coords:
                    # pixels of value 1 are set to red color
                    array[cord] = [255, 0, 0, 255]
            im = Image.fromarray(array)

            image_name = uuid.uuid4().hex
            im.save(f'{folder}/image_{image_name}.png')
            tiles[i]["mask_url"] = f'{folder}/image_{image_name}.png'
            tiles[i]['panels_area'], tiles[i]['panels_count'] = self.get_panels_area_and_count(tiles[i]['lat'], zoom, predicted_matrix)
        result_tiles = {}
        for tile in tiles:
            result_tiles[tile["id"]] = tile
        return result_tiles
