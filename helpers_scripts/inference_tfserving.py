"""This helper scripts tests tensorflow serving models."""
from datetime import datetime
import requests
import json


def inference_tfserving(eval_data, batch=10, repeat=10, signature='predict', model_url=None):
    """Tensoflow serving testing function."""
    request_data = {'signature_name': signature, 'instances': eval_data.tolist()}
    time_start = datetime.utcnow()
    for i in range(repeat):
        response = requests.post(model_url, data=json.dumps(request_data))
        print("RESPONSE", json.dumps(response))
    time_end = datetime.utcnow()
    time_elapsed_sec = (time_end - time_start).total_seconds()

    print('Total elapsed time: {} seconds'.format(time_elapsed_sec))
    print('Time for batch size {} repeated {} times'.format(4, repeat))
    print('Average latency per batch: {} seconds'.format(time_elapsed_sec/repeat))
