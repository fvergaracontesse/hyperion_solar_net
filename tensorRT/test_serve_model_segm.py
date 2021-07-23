import requests
# from tensorflow.keras.preprocessing.image import load_img, img_to_array
import numpy as np
import json
import cv2
# import tensorflow as tf
from PIL import Image
from scipy.ndimage import zoom as zm
import uuid

images = ["data/ckp4h2d2l00042a6dmutlcbd9.png","data/ckp4h5vro000b2a6dc3zhowo1.png", "data/ckp4h8s0r000h2a6d9rt5qo32.png", "data/ckp4hc20h000s2a6d17ejqip5.png"]

# batched_input = np.zeros((len(images), 600, 600, 3), dtype=np.float32)

batched_input = np.empty((len(images), 512, 512, 3), dtype=np.float32)

for i, img in enumerate(images):
    tmp_image = cv2.imread(img, cv2.IMREAD_COLOR)/255
    resized = cv2.resize(tmp_image, (512, 512))
    image = resized.reshape(512, 512, 3)
    batched_input[i, ...] = image
    i = i+1


data = json.dumps({"signature_name": "serving_default", "instances": batched_input.tolist()})

headers = {"content-type": "application/json"}
json_response = requests.post('http://localhost:8501/v1/models/segmentation_mobilenet_model:predict', data=data, headers=headers)
predictions = json.loads(json_response.text)["predictions"]

predicted = np.where(np.array(predictions) < 0.5, 0, 1).astype(np.float32)
#predicted_2 = tf.where(predictions < tf.cast(0.5, tf.float64), 0, 1).numpy()

#print("PREDICTED", predicted[0])
#print("PREDICTED 2", predicted_2[0])

for i, prediction in enumerate(predicted):
    predicted_matrix = np.array(Image.fromarray(prediction.reshape(512, 512)).resize((600, 600)))
    # convert mask to a 4D image
    array=(prediction * 255).astype(np.uint8).reshape(512, 512,1)
    array = zm(array, (1, 1, 4))
    # get row column value of pixels having value 1
    row_col = np.where(array>0)
    if len(row_col) > 0:
        im_coords = list(zip(row_col[0],row_col[1]))
        for cord in im_coords:
            # pixels of value 1 are set to red color
            array[cord] = [255, 0, 0, 255]
    im = Image.fromarray(array)

    image_name = uuid.uuid4().hex
    im.save(f'{image_name}.png')

