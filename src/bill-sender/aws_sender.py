import json
from bill_info_result import BillInfoDecoder, BillInfoResult


def send_bill(event: dict, context):
    event_json = json.dumps(event) # this seems silly, but we already have logic for serialziation/deserialization from JSON
    print("Received event:", event_json)

    bill_info: BillInfoResult = json.loads(event_json, object_hook=BillInfoDecoder.json_decode)

    print(f"Bill info: {bill_info}")
