import json
import logging
import re
from dataclasses import dataclass
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
from bill_info_result import BillInfoDecoder, BillInfoResult
from botocore.exceptions import ClientError

CHARSET = "UTF-8"
BUCKET_ARN_REGEX = re.compile(r"""arn:aws:s3:::([^/]*)/(.*)""")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

boto3.set_stream_logger('', logging.DEBUG)


@dataclass(frozen=True)
class BucketArnParseResult:
    bucket_name: str
    object_path: str


def download_from_s3(bucket: str, bucket_location: str, dest_filepath: str):
    # print("--------------------------------------------------------------------------------")
    # res = boto3.resource('s3')
    # b = res.Bucket(bucket)
    # for obj in b.objects.all():
    #     print("---->", obj.key, obj.key == bucket_location)
    # print("--------------------------------------------------------------------------------")
    s3_client = boto3.client('s3')
    try:
        logging.info(f"Downloading from {bucket} - {bucket_location} to {dest_filepath}")
        response = s3_client.download_file(bucket, bucket_location, dest_filepath)
        logging.info(f"Done {response}")
    except ClientError as e:
        logging.error(e)
        raise


def parse_bucket_arn(bucket_arn: str) -> BucketArnParseResult:
    match = BUCKET_ARN_REGEX.match(bucket_arn)
    return BucketArnParseResult(bucket_name=match.group(1), object_path=match.group(2))


def email_text():
    return """Hello {recipient_name},

Please find attached Broadband Expenses claim form for {billing_period} with receipt.
As last time, I made sure it's capped at 20£ in the "Total" column and the "Other" column contains real value.

Best regards,
{my_name}""".format(
        recipient_name="Krzysztof Recipient",
        billing_period="11/07-11/08/2022",
        my_name="Krzysztof Wielgo"
    )


def send_email(bill_info: BillInfoResult, local_pdf_path: str):
    subject = "Broadband expenses {billing_period}".format(billing_period=bill_info.bill_info.invoice_date)
    recipient = "chriswielgo+ses@gmail.com"
    sender = "chriswielgo+ses@gmail.com"

    message = MIMEMultipart()
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = recipient

    part = MIMEText(email_text(), 'plain')
    part.set_charset(CHARSET)
    message.attach(part)

    with open(local_pdf_path, 'rb') as pdf:
        part = MIMEApplication(pdf.read(), 'pdf')
        part.add_header(
            'Content-Disposition',
            'attachment',
            filename=f"{bill_info.bill_info.service_name}-{bill_info.bill_info.invoice_date}.pdf")
        message.attach(part)

    ses = boto3.client("ses")

    response = ses.send_raw_email(
        Destinations=[recipient],
        Source=sender,
        RawMessage={'Data': message.as_string()}
    )

    print("Sent email: ", json.dumps(response))


def send_bill(event: dict, _):
    event_json = json.dumps(
        event)  # this seems silly, but we already have logic for serialization/deserialization from JSON
    print("Received event:", event_json)

    bill_info: BillInfoResult = json.loads(event_json, object_hook=BillInfoDecoder.json_decode)

    print(f"Bill info: {bill_info}")

    pdf_bucket_location = parse_bucket_arn(bill_info.pdf_location)
    print("Parsed PDF location", pdf_bucket_location)
    local_pdf_path = "/tmp/bill.pdf"
    download_from_s3(pdf_bucket_location.bucket_name, pdf_bucket_location.object_path, local_pdf_path)

    send_email(bill_info, local_pdf_path)
