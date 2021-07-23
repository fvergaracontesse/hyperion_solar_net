import tensorflow as tf

converter = tf.lite.TFLiteConverter.from_keras_model("/home/ubuntu/projects/hyperion_solar_net/tensorRT/models/enb7_solar_classifier_model.h5")
tflite_model = converter.convert()

tflite_model.save(output_saved_model_dir="/home/ubuntu/projects/hyperion_solar_net/tensorRT/classification_model_tflite")
