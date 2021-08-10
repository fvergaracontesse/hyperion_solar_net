# Run tensorflow serving.

## Instructions

Our models are served by tensorflow serving. This models have to be saved a .pb and must be saved on a version folder.

### Folders path

```
Example:

/models/1/unet_classifier/
/models/1/enb7_classifier/

```

### Run docker without GPU

```
docker run -p 8501:8501 \
--mount type=bind,source={enb7_classifier_model_path},target=/models/enb7_classifier \
--mount type=bind,source={unet_classifier_model_path},target=/models/unet_segmentation \
--mount type=bind,source=model_config.conf,target=/models/model_config.conf \
-t tensorflow/serving:latest \

```

### Run docker with GPU

```

docker run -p 8501:8501 --gpus all \
--mount type=bind,source={enb7_classifier_model_path},target=/models/enb7_classifier \
--mount type=bind,source={unet_classifier_model_path},target=/models/unet_segmentation \
--mount type=bind,source=model_config.conf,target=/models/model_config.conf \
-t tensorflow/serving:latest-gpu \
--enable_batching \
--model_config_file=/models/model_config.conf \
--per_process_gpu_memory_fraction=0.5 &
