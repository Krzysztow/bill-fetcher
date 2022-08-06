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
