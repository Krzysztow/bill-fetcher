import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

import main_fetcher as fetcher
from bill_info_result import BillInfoEncoder, BillInfoResult

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def upload_to_s3(filepath: str, bucket: str, bucket_location: str):
    s3_client = boto3.client('s3')
    try:
        logging.info(f"Uploading {filepath} to {bucket_location}")
        response = s3_client.upload_file(filepath, bucket, bucket_location)
        logging.info(f"Done {response}")
    except ClientError as e:
        logging.error(e)
        raise


def upload_bill_info(bill_info_json: str, bucket: str, bucket_location: str):
    bill_info_filepath = "/tmp/bill_info.json"
    with open(bill_info_filepath, "w") as f:
        f.write(bill_info_json)

    upload_to_s3(bill_info_filepath, bucket, bucket_location)


def main():
    username = os.getenv("HO_USERNAME")
    password = os.getenv("HO_PASSWORD")
    bucket = os.getenv("RESULT_BUCKET_NAME")

    pdf_location = "/tmp/bill.pdf"
    result = fetcher.fetch_bill(username, password, pdf_location)

    bucket_pdf_location = result.bill_info.invoice_date.isoformat() + "/bill.pdf"
    bucket_json_location = result.bill_info.invoice_date.isoformat() + "/bill_info.json"

    upload_to_s3(pdf_location, bucket, bucket_pdf_location)

    bill_fetch_result = BillInfoResult(bill_info=result.bill_info,
                                       pdf_location=f"arn:aws:s3:::{bucket}/{bucket_pdf_location}")
    bill_info_json = json.dumps(obj=bill_fetch_result, default=BillInfoEncoder.json_encode)
    upload_bill_info(bill_info_json, bucket, bucket_json_location)
    task_token = os.getenv("TASK_TOKEN")
    client = boto3.client('stepfunctions')
    client.send_task_success(
        taskToken=task_token,
        output=bill_info_json
    )


if __name__ == "__main__":
    main()
