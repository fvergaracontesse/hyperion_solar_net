"""Use this script to save keras model to .pb model."""
import sys

import tensorflow as tf
from tensorflow import keras

INPUT_MODEL = sys.argv[1]
OUTPUT_DIR = sys.argv[2]

keras_model = keras.models.load_model(f'{INPUT_MODEL}')
tf.saved_model.save(keras_model, f'{OUTPUT_DIR}')
