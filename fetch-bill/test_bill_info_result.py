import json
from datetime import date
from unittest import TestCase

from bill_info_result import BillInfoResult, BillInfo, BillInfoEncoder, BillInfoDecoder


class TestBillInfoResult(TestCase):
    def setUp(self):
        self.info = BillInfoResult(
            bill_info=BillInfo(service_name='150Mb Fibre Connection - Broadband Only', invoice_value='£29.00',
                               invoice_date=date(2022, 7, 10)), pdf_location='/tmp/requests.pdf')

    def test_json(self):
        info_json = json.dumps(obj=self.info, default=BillInfoEncoder.json_encode)
        print("wrote:", info_json)
        json_read = json.loads(info_json, object_hook=BillInfoDecoder.json_decode)

        print("read:", json_read)
        self.assertEqual(json_read, self.info)

    def test_json_read(self):
        data = """
        {
           "bill_info":{
              "service_name":"150Mb Fibre Connection - Broadband Only",
              "invoice_date":"2022-07-10",
              "invoice_value":"\u00a329.00"
           },
           "pdf_location":"arn:aws:s3:::billfetcherstack-billfetcherbucket83d4f83e-w2t4ey3ronlp/2022-07-10/bill.pdf"
        }"""
        json_read: BillInfoResult = json.loads(data, object_hook=BillInfoDecoder.json_decode)

        self.assertEqual(json_read.pdf_location, "arn:aws:s3:::billfetcherstack-billfetcherbucket83d4f83e-w2t4ey3ronlp/2022-07-10/bill.pdf")

