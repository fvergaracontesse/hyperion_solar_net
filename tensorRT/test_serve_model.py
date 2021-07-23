import requests
from tensorflow.keras.preprocessing.image import load_img, img_to_array
import numpy as np
import json
import cv2

def sigmoid(x):
  return 1 / (1 + np.exp(-x))

# images = ["data/ckp4h2d2l00042a6dmutlcbd9.png","data/ckp4h5vro000b2a6dc3zhowo1.png", "data/ckp4h8s0r000h2a6d9rt5qo32.png", "data/ckp4hc20h000s2a6d17ejqip5.png"]
images = ["data/ckp4h2d2l00042a6dmutlcbd9.png","data/ckp4h5vro000b2a6dc3zhowo1.png"]

batched_input = np.zeros((len(images), 600, 600, 3), dtype=np.float32)

for i, img in enumerate(images):
    tmp_image = cv2.imread(img)
    resized = cv2.resize(tmp_image, (600, 600))[...,::-1].astype(np.float32)
    image = np.expand_dims(resized.reshape(600, 600, 3), axis=0)
    x = np.expand_dims(img_to_array(load_img(img, target_size=(600, 600))), axis=0)
    batched_input[i, :] = x


data = json.dumps({"signature_name": "serving_default", "instances": batched_input.tolist()})

headers = {"content-type": "application/json"}
json_response = requests.post('http://localhost:8501/v1/models/classification_tft_model:predict', data=data, headers=headers)
predictions = json.loads(json_response.text)

predictions = np.where(sigmoid(np.array(predictions["predictions"])) < 0.5, 0, 1).tolist()

print(predictions)

