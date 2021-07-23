# Re-run after Kernel restart
from __future__ import absolute_import, division, print_function, unicode_literals
import os
import time

import numpy as np
# import matplotlib.pyplot as plt

import tensorflow as tf
from tensorflow import keras
# from tensorflow.python.compiler.tensorrt import trt_convert as trt
# from tensorflow.python.saved_model import tag_constants
# from tensorflow.keras.preprocessing import image
import segmentation_models as sm
from segmentation_models import Unet
from segmentation_models.metrics import IOUScore
# from tensorflow.keras import backend, layers

# from tensorflow.keras.applications.inception_v3 import InceptionV3
# from tensorflow.keras.applications.inception_v3 import preprocess_input, decode_predictions

classification_model = keras.models.load_model(f'models/enb7_solar_classifier_model.h5')
tf.saved_model.save(classification_model, 'enb7_solar_classifier_model/1')

#segmentation_model = load_tf_saved_model('models/unet_solar_segmentation_model.h5')


