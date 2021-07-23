import numpy as np
# from PIL import Image
import cv2
from datetime import datetime
import requests
import json

def inference_tfserving(eval_data, batch=10, 
                        repeat=10, signature='predict'):
  # url = 'http://localhost:8501/v1/models/enb7_solar_classifier_model:predict'
  url = 'http://localhost:8501/v1/models/mobilenet_solar_segmentation_model:predict'
  # instances = [[i for i in list(eval_data[img])] for img in range(batch)]

  request_data = {'signature_name': signature, 
                  'instances': eval_data.tolist()}
  time_start = datetime.utcnow() 
  for i in range(repeat):
    response = requests.post(url, data=json.dumps(request_data))
  time_end = datetime.utcnow() 
  time_elapsed_sec = (time_end - time_start).total_seconds()

  print('Total elapsed time: {} seconds'.format(time_elapsed_sec))
  print('Time for batch size {} repeated {} times'.format(4, repeat))
  print('Average latency per batch: {} seconds'.format(time_elapsed_sec/repeat))


images = ["data/ckp4h2d2l00042a6dmutlcbd9.png","data/ckp4h5vro000b2a6dc3zhowo1.png", "data/ckp4h8s0r000h2a6d9rt5qo32.png", "data/ckp4hc20h000s2a6d17ejqip5.png"]

batched_input = np.zeros((len(images), 600, 600, 3), dtype=np.float32)
for i, img in enumerate(images):
    tmp_image = cv2.imread(img)
    resized = cv2.resize(tmp_image, (600, 600))[...,::-1].astype(np.float32)
    x = np.expand_dims(resized.reshape(600, 600, 3), axis=0)
    batched_input[i, :] = x

inference_tfserving(batched_input, 4)
