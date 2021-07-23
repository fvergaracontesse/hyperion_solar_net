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

config = tf.compat.v1.ConfigProto(gpu_options =
                         tf.compat.v1.GPUOptions(per_process_gpu_memory_fraction=0.8)
# device_count = {'GPU': 1}
)
config.gpu_options.allow_growth = True
session = tf.compat.v1.Session(config=config)
tf.compat.v1.keras.backend.set_session(session)


images = ["data/ckp4h2d2l00042a6dmutlcbd9.png","data/ckp4h5vro000b2a6dc3zhowo1.png", "data/ckp4h8s0r000h2a6d9rt5qo32.png", "data/ckp4hc20h000s2a6d17ejqip5.png"]

def load_tf_saved_model(input_saved_model_dir):
    print(f'Loading saved model {input_saved_model_dir}')
    saved_model_loaded = tf.saved_model.load(input_saved_model_dir, tags=[tag_constants.SERVING])
    return saved_model_loaded


def batch_input(batch_size=8):
    batched_input = np.zeros((batch_size, 600, 600, 3), dtype=np.float32)

    for i in range(batch_size):
        img_path = images[i % 4]
        img = image.load_img(img_path,  target_size=(600, 600))
        x = image.img_to_array(img)
        x = np.expand_dims(x, axis=0)
        # x = preprocess_input(x)
        batched_input[i, :] = x
    batched_input = tf.constant(batched_input)
    return batched_input

def predict_and_benchmark_throughput(batched_input, infer, N_warmup_run=50, N_run=1000):

    elapsed_time = []
    all_preds = []
    batch_size = batched_input.shape[0]

    for i in range(N_warmup_run):
        labeling = infer(batched_input)
        preds = labeling['dense']
        preds = tf.nn.sigmoid(preds)
        preds = tf.where(preds < 0.5, 0, 1).numpy().tolist()
        print(preds)

    for i in range(N_run):
        start_time = time.time()
        labeling = infer(batched_input)
        preds = labeling['dense'].numpy()
        end_time = time.time()
        elapsed_time = np.append(elapsed_time, end_time - start_time)
        all_preds.append(preds)

        if i % 50 == 0:
            print('Steps {}-{} average: {:4.1f}ms'.format(i, i+50, (elapsed_time[-50:].mean()) * 1000))

    print('Throughput: {:.0f} images/s'.format(N_run * batch_size / elapsed_time.sum()))
    return all_preds

batched_input = batch_input(batch_size=4)
print(type(batched_input))
print(batched_input.shape)

# saved_model = load_tf_saved_model('enb7_solar_classifier_model')

# infer = saved_model.signatures['serving_default']

# print(infer.structured_outputs)

# all_preds = predict_and_benchmark_throughput(batched_input,
#                                             infer,
#                                             N_warmup_run=5,
#                                             N_run=100)


# TensorRT

saved_model_tensor_rt = load_tf_saved_model('enb7_solar_classifier_model_TFTRT_FP32')

infer_tensor_rt = saved_model_tensor_rt.signatures['serving_default']

print(infer_tensor_rt.structured_outputs)

all_preds = predict_and_benchmark_throughput(batched_input,
                                             infer_tensor_rt,
                                             N_warmup_run=5,
                                             N_run=100)
