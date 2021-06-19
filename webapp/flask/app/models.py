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
        self.model = keras.models.load_model(f'{models_folder}/enb7_solar_classifier_model.h5')
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

    def predict(self, tiles):
        # predicting images
        images = list(map(lambda x: np.expand_dims(img_to_array(load_img(x['filename'], grayscale=False)), axis=0), tiles))
        images = np.vstack(images)
        predictions = self.model.predict(images).flatten()
        predictions = tf.nn.sigmoid(predictions)
        predictions = tf.where(predictions < 0.5, 0, 1).numpy().tolist()
        for tile in tiles:
            #image_arr = np.expand_dims(img_to_array(load_img(tile['filename'], grayscale=False)), axis=0)
            #prediction = self.model.predict(image_arr).flatten()
            # Apply a sigmoid since our model returns logits
            #prediction = tf.nn.sigmoid(prediction)
            #tile["prediction"] = tf.where(prediction < 0.5, 0, 1).numpy().tolist()
            tile["prediction"] = predictions[tile["id"]]
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

        return(panel_area, panel_count)

    def predict(self, tiles, zoom):
        images = np.empty((len(tiles), self.image_width, self.image_height, 3), dtype=np.float32)
        i = 0
        for tile in tiles:
            test_image = cv2.imread(tile['filename'], cv2.IMREAD_COLOR)/255
            resized = cv2.resize(test_image, (self.image_width, self.image_height))
            image = resized.reshape(self.image_width, self.image_height, 3)
            images[i, ...] = image
            i = i+1
        predicted = (self.model.predict(images))
        predicted = tf.where(predicted < tf.cast(0.5, tf.float64), 0, 1).numpy()

        for i in range(0, len(predicted)):
            predicted_matrix = predicted[i]
            im = Image.fromarray((predicted[i] * 255).astype(np.uint8).reshape(self.image_width, self.image_height))
            image_name = uuid.uuid4().hex
            im.save(f'{self.segmentation_image_folder}/image_{image_name}.png')
            tiles[i]["url"] = f'/{self.segmentation_image_folder}/image_{image_name}.png'
            tiles[i]['panels_area'], tiles[i]['panels_count'] = self.get_panels_area_and_count(tiles[i]['lat'], zoom, predicted_matrix)

        return tiles
