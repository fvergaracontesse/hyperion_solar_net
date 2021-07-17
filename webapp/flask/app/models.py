"""Use this class for predictions with efficient net."""
import tensorflow as tf
from tensorflow import keras
import numpy as np
from tensorflow.keras.preprocessing.image import load_img, img_to_array
import segmentation_models as sm
from segmentation_models import Unet
#from segmentation_models.metrics import iou_score
from segmentation_models.metrics import IOUScore
from tensorflow.keras import backend, layers
from PIL import Image
import cv2
from json import JSONEncoder
import json
import math
import uuid
from scipy.ndimage import zoom as zm
from helpers.sn_helpers import (
    chunks,
    get_image_from_s3,
    get_image_stream_from_s3
)
import os
from tensorflow.python.compiler.tensorrt import trt_convert as trt
from tensorflow.python.saved_model import tag_constants
from tensorflow.keras.preprocessing import image
import time

config = tf.compat.v1.ConfigProto(gpu_options =
                         tf.compat.v1.GPUOptions(per_process_gpu_memory_fraction=0.8)
# device_count = {'GPU': 1}
)
config.gpu_options.allow_growth = True
session = tf.compat.v1.Session(config=config)
tf.compat.v1.keras.backend.set_session(session)


sm.set_framework('tf.keras')

class FixedDropout(layers.Dropout):
        def _get_noise_shape(self, inputs):
            if self.noise_shape is None:
                return self.noise_shape

            symbolic_shape = backend.shape(inputs)
            noise_shape = [symbolic_shape[axis] if shape is None else shape
                           for axis, shape in enumerate(self.noise_shape)]
            return tuple(noise_shape)

class NumpyArrayEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return JSONEncoder.default(self, obj)

class Classification:

    def __init__(self, models_folder='models', model_en='b7'):
        # load pre-trained EfficientNet model
        # self.model = keras.models.load_model(f'{models_folder}/enb7_solar_classifier_model.h5')
        start = time.time()
        self.model = tf.saved_model.load(f'{models_folder}/enb7_solar_classifier_model_TFTRT_FP32', tags=[tag_constants.SERVING])
        end = time.time()
        print("LOAD MODEL")
        print(end - start)

        start = time.time()
        self.infer = self.model.signatures['serving_default']
        end = time.time()
        print("SETUP INFER")
        print(end - start)

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
        start = time.time()
        batched_input = np.zeros((len(tiles), 600, 600, 3), dtype=np.float32)
        end = time.time()
        print("CREATE BATCH INPUT")
        print(end - start)
        # predicting images
        #if not fromS3:
        #    images = list(map(lambda x: np.expand_dims(img_to_array(load_img(x['filename'], grayscale=False)), axis=0), tiles))
        #else:
        #    images = list(map(lambda x: np.expand_dims(img_to_array(get_image_from_s3(x['file_name'])), axis=0), tiles))
        start = time.time()
        for i, tile in enumerate(tiles):
            x = np.expand_dims(img_to_array(load_img(tile['filename'], grayscale=False)), axis=0)
            batched_input[i, :] = x
        end = time.time()
        print("ENUMERATE")
        print(end - start)

        start = time.time()
        batched_input = tf.constant(batched_input)
        end = time.time()
        print("CREATE TF CONSTANT")
        print(end - start)

        # images = np.vstack(images)
        #print(type(images))
        # print(batched_inpu.shape)
        #images = tf.constant(np.vstack(images))
        #print(images)
        # predictions = self.model.predict_on_batch(images).flatten()
        # predictions = tf.nn.sigmoid(predictions)
        # predictions = tf.where(predictions < 0.5, 0, 1).numpy().tolist()
        start = time.time()
        labeling = self.infer(batched_input)
        end = time.time()
        print("INFER")
        print(end - start)
        preds = labeling['dense']
        preds = tf.nn.sigmoid(preds)
        predictions = tf.where(preds < 0.5, 0, 1).numpy().tolist()
        for i, tile in enumerate(tiles):
            tile["prediction"] = predictions[i]
        return tiles

class Segmentation:

    def __init__(self, models_folder='models', model_en='b7'):
        # load pre-trained EfficientNet model
        # model = Unet(backbone_name = 'efficientnetb7', encoder_weights='imagenet', encoder_freeze = False)
        self.model = keras.models.load_model(f'{models_folder}/unet_solar_segmentation_model.h5',
                                                custom_objects={'iou_score': IOUScore(threshold=0.5),
                                                'f1-score': sm.metrics.FScore(threshold=0.5),
                                                'binary_crossentropy_plus_jaccard_loss': sm.losses.bce_jaccard_loss
                                                })

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
        panel_count = round((panel_area / area_per_panel),0)
        panel_area = round(panel_area, 2)
        return(panel_area, panel_count)

    def predict(self, tiles, zoom, fromS3=False, place=None):
        images = np.empty((len(tiles), self.image_width, self.image_height, 3), dtype=np.float32)
        i = 0
        if place:
            if not os.path.exists(f'{self.segmentation_image_folder}/{place}'):
                os.makedirs(f'{self.segmentation_image_folder}/{place}')
            folder = f'{self.segmentation_image_folder}/{place}'
        else:
            folder = f'{self.segmentation_image_folder}'
        for tile in tiles:
            if not fromS3:
                tmp_image = cv2.imread(tile['filename'], cv2.IMREAD_COLOR)/255
            else:
                tmp_image = cv2.imdecode(np.asarray(bytearray(get_image_stream_from_s3(tile["file_name"]))), cv2.IMREAD_COLOR)/255
            resized = cv2.resize(tmp_image, (self.image_width, self.image_height))
            image = resized.reshape(self.image_width, self.image_height, 3)
            images[i, ...] = image
            i = i+1
        predicted = (self.model.predict_on_batch(images))
        predicted = tf.where(predicted < tf.cast(0.5, tf.float64), 0, 1).numpy()
        for i, prediction in enumerate(predicted):
            predicted_matrix = np.array(Image.fromarray(prediction.reshape(self.image_width, self.image_height)).resize((600, 600)))

            # convert mask to a 4D image
            array=(prediction * 255).astype(np.uint8).reshape(self.image_width, self.image_height,1)
            array = zm(array, (1, 1, 4))
            # get row column value of pixels having value 1
            row_col = np.where(array>0)
            if len(row_col) > 0:
                im_coords = list(zip(row_col[0],row_col[1]))
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
