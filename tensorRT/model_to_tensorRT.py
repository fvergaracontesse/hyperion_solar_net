# Re-run after Kernel restart
from __future__ import absolute_import, division, print_function, unicode_literals
import os
import time

import numpy as np
# import matplotlib.pyplot as plt

import tensorflow as tf
from tensorflow import keras
from tensorflow.python.compiler.tensorrt import trt_convert as trt
from tensorflow.python.saved_model import tag_constants
from tensorflow.keras.preprocessing import image
# import segmentation_models as sm
# from segmentation_models import Unet
# from segmentation_models.metrics import IOUScore
from tensorflow.keras import backend, layers

# from tensorflow.keras.applications.inception_v3 import InceptionV3
# from tensorflow.keras.applications.inception_v3 import preprocess_input, decode_predictions

# Re-run after Kernel restart
def convert_to_trt_graph_and_save(precision_mode='float32',
                                  input_saved_model_dir='enb7_solar_classifier_model'):
    if precision_mode == 'float32':
        precision_mode = trt.TrtPrecisionMode.FP32
        converted_save_suffix = '_TFTRT_FP32'

    output_saved_model_dir = input_saved_model_dir + converted_save_suffix

    conversion_params = trt.DEFAULT_TRT_CONVERSION_PARAMS._replace(
        precision_mode=precision_mode,
        max_workspace_size_bytes=3000000000
    )

    converter = trt.TrtGraphConverterV2(
        input_saved_model_dir=input_saved_model_dir,
        conversion_params=conversion_params
    )

    print(f'Converting {input_saved_model_dir} to TF-TRT graph precision mode {precision_mode}')

    converter.convert()

    print(f'Saving converted to {output_saved_model_dir}')

    converter.save(output_saved_model_dir=output_saved_model_dir)

    print('Complete')

convert_to_trt_graph_and_save(precision_mode='float32', input_saved_model_dir='enb7_solar_classifier_model')

#segmentation_model = load_tf_saved_model('models/unet_solar_segmentation_model.h5')


