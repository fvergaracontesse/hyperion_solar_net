import os
import time
import sys

import numpy as np
# import matplotlib.pyplot as plt

import tensorflow as tf
from tensorflow import keras

INPUT_MODEL = sys.argv[1]
OUTPUT_DIR = sys.argv[2]

print("Input model:", OUTPUT_DIR)

classification_model = keras.models.load_model(f'{INPUT_MODEL}')
tf.saved_model.save(classification_model, f'{OUTPUT_DIR}')

#segmentation_model = load_tf_saved_model('models/unet_solar_segmentation_model.h5')


