#!/usr/bin/env python3
import os
import sys
import requests
import time
import logging
from datetime import datetime
from pathlib import Path
import zipfile
from moviepy import ImageSequenceClip
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

app = Flask(__name__)
CORS(app)

# Create output directory
OUTPUT_DIR = Path("weather_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Weather event mapping to input_id
WEATHER_EVENT_MAP = {
    "amphan": 0,
    "hagibis": 1,
    "atmospheric-river": 2,
    "hurricane-harvey": 3,
    "kyrill": 4
}

# Weather variable mapping
VARIABLE_MAP = {
    "surface-temp": "t2m",
    "wind-speed": "w10m",
    "water-vapor": "tcwv"
}

invoke_url = "https://climate.api.nvidia.com/v1/nvidia/fourcastnet"

def extract_and_stitch_videos(zip_path, output_dir, variables):
    """Extract PNG files from zip and create videos for each variable"""
    video_paths = {}
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(output_dir)
    
    # Time steps we want (in hours)
    time_steps = [0, 6, 12, 18, 24, 30, 36]
    
    for var in variables:
        var_code = VARIABLE_MAP[var]
        image_files = []
        
        # Collect image file paths for the specific time steps
        for step in time_steps:
            # Format: t2m_000_000.png, t2m_006_000.png, etc.
            filename = f"{var_code}_{step:03d}_000.png"
            filepath = output_dir / filename
            
            if filepath.exists():
                image_files.append(str(filepath))
                logging.info(f"Found image: {filename}")
            else:
                logging.warning(f"Missing image: {filename}")
        
        if image_files:
            # Create video using MoviePy
            video_filename = f"{var_code}_animation.mp4"
            video_path = output_dir / video_filename
            
            # Create video clip from images
            # fps=1 means 1 frame per second (each image shows for 1 second)
            # You can adjust this: fps=2 would make it faster, fps=0.5 slower
            clip = ImageSequenceClip(image_files, fps=1)
            
            # Write video file with good quality
            # MoviePy 2.x simplified parameters
            clip.write_videofile(
                str(video_path),
                codec='libx264',
                fps=1
            )
            
            clip.close()
            video_paths[var] = str(video_path)
            logging.info(f"Created video: {video_filename}")
    
    return video_paths

def run_forecast(weather_event, weather_variables):
    """Run the weather forecast simulation"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"forecast_{timestamp}.zip"
    
    # Convert variables to API format
    api_variables = [VARIABLE_MAP[var] for var in weather_variables]
    variables_str = ",".join(api_variables)
    
    # Get input_id from event
    input_id = WEATHER_EVENT_MAP.get(weather_event, 3)
    
    headers = {
        "Authorization": f"Bearer {os.getenv('NGC_API_KEY', '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')}",
        "NVCF-POLL-SECONDS": "5"
    }
    
    payload = {
        "input_id": input_id,
        "variables": variables_str,
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
    
    # Extract and create videos
    extract_dir = OUTPUT_DIR / f"extracted_{timestamp}"
    extract_dir.mkdir(exist_ok=True)
    
    video_paths = extract_and_stitch_videos(output_file, extract_dir, weather_variables)
    
    return {
        "timestamp": timestamp,
        "video_paths": video_paths,
        "output_file": str(output_file)
    }

@app.route('/forecast', methods=['POST'])
def forecast():
    """Endpoint to trigger weather forecast"""
    try:
        data = request.json
        weather_event = data.get('weatherEvent', 'hurricane-harvey')
        weather_variables = data.get('weatherVariables', ['surface-temp', 'wind-speed', 'water-vapor'])
        
        logging.info(f"Received forecast request: event={weather_event}, variables={weather_variables}")
        
        result = run_forecast(weather_event, weather_variables)
        
        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        logging.error(f"Error in forecast: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/video/<timestamp>/<variable>', methods=['GET'])
def get_video(timestamp, variable):
    """Serve video files"""
    try:
        var_code = VARIABLE_MAP.get(variable, variable)
        video_filename = f"{var_code}_animation.mp4"
        video_path = OUTPUT_DIR / f"extracted_{timestamp}" / video_filename
        
        if video_path.exists():
            return send_file(str(video_path), mimetype='video/mp4')
        else:
            return jsonify({"error": "Video not found"}), 404
    except Exception as e:
        logging.error(f"Error serving video: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)