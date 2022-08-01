import json

def send_bill(event, context):
    print("Received event: " + json.dumps(event, indent=2))
