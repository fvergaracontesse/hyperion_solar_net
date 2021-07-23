# Re-run after Kernel restart
from __future__ import absolute_import, division, print_function, unicode_literals
import os
import time
import sys

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

# classification_model = keras.models.load_model(f'models/enb7_solar_classifier_model.h5')

INPUT_MODEL = sys.argv[1]
OUTPUT_DIR = sys.argv[2]

model = keras.models.load_model(f'{INPUT_MODEL}',
                    custom_objects={'iou_score': IOUScore(threshold=0.5),
                                    'f1-score': sm.metrics.FScore(threshold=0.5),
                                    'binary_crossentropy_plus_jaccard_loss': sm.losses.bce_jaccard_loss,
                                    'precision': sm.metrics.Precision(threshold=0.5),
                                    'recall':sm.metrics.Recall(threshold=0.5)})

tf.saved_model.save(model, f'{OUTPUT_DIR}')

#segmentation_model = load_tf_saved_model('models/unet_solar_segmentation_model.h5')


