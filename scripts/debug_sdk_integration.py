
import os
import sys
import logging
from google.cloud import aiplatform_v1beta1
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_sdk")

# Ensure env vars
# Docker sets GOOGLE_APPLICATION_CREDENTIALS, PROJECT, LOCATION

project = os.environ.get("GOOGLE_CLOUD_PROJECT")
location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
model_id = "veo-3.0-generate-001"

def test_sdk_generation():
    print(f"Testing SDK generation with Project: {project}, Location: {location}")
    
    # Client options
    api_endpoint = f"{location}-aiplatform.googleapis.com"
    client_options = {"api_endpoint": api_endpoint}
    
    # Initialize client
    client = aiplatform_v1beta1.PredictionServiceClient(client_options=client_options)
    
    # Construct endpoint path for model manually
    endpoint = f"projects/{project}/locations/{location}/publishers/google/models/{model_id}"
    
    print(f"Endpoint: {endpoint}")
    
    # Instances
    instance_dict = {"prompt": "A cinematic drone shot of a waterfall"}
    instance = Value()
    json_format.ParseDict(instance_dict, instance)
    
    # Parameters
    params_dict = {
        "durationSeconds": 6,
        "aspectRatio": "16:9",
        "sampleCount": 1,
    }
    parameters = Value()
    json_format.ParseDict(params_dict, parameters)
    
    print("Calling predict_long_running...")
    print(f"Client methods: {[m for m in dir(client) if 'predict' in m]}")
    try:
        # returns an Operation (LRO)
        operation = client.predict_long_running(
            endpoint=endpoint,
            instances=[instance],
            parameters=parameters,
        )
        
        print(f"Operation started: {operation.operation.name}")
        
        # Poll
        print("Polling via SDK...")
        result = operation.result(timeout=600) # blocks until done
        
        print("Operation completed!")
        print(f"Result type: {type(result)}")
        # Result is a PredictResponse protobuf
        
        # Extract predictions
        if result.predictions:
            print(f"Got {len(result.predictions)} predictions")
            # Convert first prediction to dict
            pred_dict = json_format.MessageToDict(result.predictions[0])
            print("Prediction keys:", pred_dict.keys())
        else:
            print("No predictions in result.")
            
    except Exception as e:
        print(f"SDK Error: {e}")

if __name__ == "__main__":
    test_sdk_generation()
