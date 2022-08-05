import json

from bill_info_result import BillInfoDecoder, BillInfoResult

def send_bill(event, context):
    print("Received event: " + json.dumps(event, indent=2))

    bill_info: BillInfoResult = json.loads(context, object_hook=BillInfoDecoder.json_decode)

    print(f"Bill info: {bill_info}")
