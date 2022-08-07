from datetime import date
from dateutil.relativedelta import relativedelta
import json

from openpyxl import load_workbook, Workbook
from bill_info_result import BillInfoDecoder, BillInfoResult
from openpyxl.worksheet.worksheet import Worksheet


class ExpenseFormFiller:
    def __init__(self, input_xls_path: str):
        self.wb: Workbook = load_workbook(filename=input_xls_path)
        self.sheet_ranges: Worksheet = self.wb['claim form']

    def _fill_field(self, field, expected, new_value):
        old_value = self.sheet_ranges[field].value
        if old_value != expected:
            raise RuntimeError(f"Filling in the field {field}. Expected old value: {expected}, but found {old_value}")
        self.sheet_ranges[field] = new_value

    def fill_in(self, bill_info: BillInfoResult, today: date = date.today(), capped_value: int = 20, claimer: str = "Krzysztof Wielgo"):
        end_date, start_date = self.calculate_service_bill_dates(bill_info)

        def f_date(d: date): return d.strftime("%Y/%m/%d")

        fill_ins = [
            ("B4", "<claimer>", claimer),
            ("D4", "<date>", f_date(today)),
            ("J4", "<month>", today.strftime("%B")),
            ("N4", "<year>", str(today.year)),
            ("B8", "<bill-date>", bill_info.bill_info.invoice_date),
            (
                "C8",
                "<service> (<date-start>-<date-end>)",
                f"{bill_info.bill_info.service_name} ({f_date(start_date)} - {f_date(end_date)})"),
            ("L8", "<expense>", bill_info.bill_info.invoice_value),
            ("O8", "<capped-expense>", capped_value),
            ("B13", "<claimer>", claimer),
        ]

        for field, expected, new_value in fill_ins:
            self._fill_field(field, expected, new_value)

    @staticmethod
    def calculate_service_bill_dates(bill_info):
        start_date = bill_info.bill_info.invoice_date
        end_date = start_date + relativedelta(months=1, days=-1)
        return end_date, start_date

    def save(self, output_path: str):
        self.wb.save(output_path)


def main():
    local_xls_path = "/tmp/expenses.xlsx"

    with open("event.json", "r") as f:
        event_json = f.read()
    bill_info: BillInfoResult = json.loads(event_json, object_hook=BillInfoDecoder.json_decode)

    filler = ExpenseFormFiller('broadband-expenses.xlsx')
    filler.fill_in(bill_info)
    filler.save(local_xls_path)


if __name__ == "__main__":
    main()
