#!/usr/bin/env python3
import os
import sys
import requests
import time
import logging

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

output_file = "output.zip"

invoke_url = "https://climate.api.nvidia.com/v1/nvidia/fourcastnet"
headers = {
    "Authorization": f"Bearer {os.getenv('NGC_API_KEY', '')}",
    "NVCF-POLL-SECONDS": "5"
}
payload = {
    "input_id": 3,
    "variables": "w10m,t2m,tcwv",
    "simulation_length": 6,
    "ensemble_size": 1,
    "noise_amplitude": 0,
}

# re-use connections
session = requests.Session()

logging.info(f"Payload {payload}")
logging.info("Making inference request")
response = session.post(invoke_url, headers=headers, json=payload)
response.raise_for_status()
if response.status_code == 202:
    request_id = response.headers['nvcf-reqid']
else:
    raise Exception("Failed request")

logging.info(f"Polling job {request_id}")
status_url = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{request_id}"
while(True):
    response = session.get(status_url, headers=headers, allow_redirects=False)
    response.raise_for_status()
    # Invocation is fulfilled.
    if response.status_code == 200:
        logging.info(f"Invocation is fulfilled. Downloading to {output_file}")
        with open(output_file, 'wb') as f:
            f.write(response.content)
        break
    # Large asset response
    elif response.status_code == 302:
        logging.info(f"Downloading large asset output to {output_file}")
        asset_url = response.headers['Location']
        with requests.get(asset_url, stream=True) as r:
            with open(output_file, 'wb') as f:
                f.write(r.content)
        break
    # Response in progress
    elif response.status_code == 202:
        logging.info(f"Job still running")
    else:
        raise Exception(f"Unexpected status code {response.status_code}")
    time.sleep(3)