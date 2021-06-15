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
        #self.model = keras.models.load_model(f'{models_folder}/unet_solar_segmentation_model.h5', custom_objects={'iou_score': IOUScore(threshold=0.5), 'f1-score': sm.metrics.FScore(threshold=0.5)})
        self.model = keras.models.load_model(f'{models_folder}/unet_solar_segmentation_model_size512_jaccardloss_iou87.h5', custom_objects={'iou_score': IOUScore(threshold=0.5),
                                   'f1-score': sm.metrics.FScore(threshold=0.5),
                                   'binary_crossentropy_plus_jaccard_loss': sm.losses.bce_jaccard_loss})

        self.model_en = model_en
        self.image_width = 416
        self.image_height = 416
        self.batch_size = 20
        self.segmentation_image_folder = 'img/segmentation'


    def predict(self, tiles):
        images = np.empty((len(tiles), self.image_width, self.image_height, 3), dtype=np.float32)
        i = 0
        for tile in tiles:
            test_image = cv2.imread(tile['filename'], cv2.IMREAD_COLOR)/255
            resized = cv2.resize(test_image, (self.image_width, self.image_height))
            image = resized.reshape(self.image_width, self.image_height, 3)
            images[i, ...] = image
            i = i+1
        predicted = (self.model.predict(images))
        for i in range(0, len(predicted)):
            predicted[i] = tf.where(predicted[i] < 0.5, 0, 1)
            # tiles[i]["predicted"] = predicted[i]
            im = Image.fromarray((predicted[i] * 255).astype(np.uint8).reshape(self.image_width, self.image_height)).resize((600, 600))
            im.save(f'{self.segmentation_image_folder}/image_{i}.png')
            tiles[i]["url"] = f'/{self.segmentation_image_folder}/image_{i}.png'
        return tiles
