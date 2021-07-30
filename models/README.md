### HyperionSolarNet Models are available here for download
https://drive.google.com/drive/folders/16vBSShfw1S-hT87cLTvj9lEe1aPSbDDi?usp=sharing

### Example code showing how the models can be used to classify and segment images

```
import numpy as np
from PIL import Image
import tensorflow as tf
from tensorflow import keras
import segmentation_models as sm

IMG_SIZE = 600
SEG_IMG_SIZE = 512
CLASSIFICATION_MODEL_NAME = models_folder+'/hyperionsolarnet_classifier_model.h5'
SEGMENTATION_MODEL_NAME = models_folder+'/hyperionsolarnet_segmentation_model.h5'
class_model = keras.models.load_model(CLASSIFICATION_MODEL_NAME)
sm.set_framework('tf.keras')
seg_model = keras.models.load_model(SEGMENTATION_MODEL_NAME,
                   custom_objects={'iou_score': sm.metrics.IOUScore(threshold=0.5), 
                                   'f1-score': sm.metrics.FScore(threshold=0.5),
                                   'binary_crossentropy_plus_jaccard_loss': sm.losses.bce_jaccard_loss,
                                   'precision':sm.metrics.Precision(threshold=0.5),
                                   'recall':sm.metrics.Recall(threshold=0.5)})
                                   
# set the folder containing satellite images
datafolder = <folder containing images>

for filename in os.listdir(datafolder): 
  pathname = os.path.join(datafolder, filename)
  # first, classify the image
  # CV2 reads images in BGR
  tmp_image = cv2.imread(pathname, cv2.IMREAD_COLOR)
  resized = cv2.resize(tmp_image, (IMG_SIZE, IMG_SIZE))[...,::-1].astype(np.float32) #convert to RGB
  class_image = np.expand_dims(resized.reshape(IMG_SIZE, IMG_SIZE, 3), axis=0)
  class_label = class_model.predict(class_image)
  class_label = tf.nn.sigmoid(class_label)

  # if image is classified as solar, pass it through the segmentation model
  if (class_label > 0.5):
    tmp_image = tmp_image/255  #BGR
    resized = cv2.resize(tmp_image, (SEG_IMG_SIZE, SEG_IMG_SIZE))
    image = resized.reshape(SEG_IMG_SIZE, SEG_IMG_SIZE, 3)   

    predicted = seg_model.predict(np.expand_dims(image, axis=0))
    predicted = tf.where(predicted < 0.5, 0, 1).numpy()

    # resize the prediction back to the original size of the image
    img = Image.fromarray(predicted.reshape(SEG_IMG_SIZE, SEG_IMG_SIZE)).resize((IMG_SIZE, IMG_SIZE))
    predicted_matrix = np.array(img)
    
    # save the prediction mask 

```
