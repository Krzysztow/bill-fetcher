from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class BillInfo:
    service_name: str
    invoice_value: str
    invoice_date: date


@dataclass(frozen=True)
class BillInfoResult:
    bill_info: BillInfo
    pdf_location: str


class BillInfoEncoder:
    @staticmethod
    def json_encode(o):
        if isinstance(o, BillInfoResult):
            return {"bill_info": o.bill_info, "pdf_location": o.pdf_location}
        elif isinstance(o, BillInfo):
            return {"service_name": o.service_name, "invoice_date": o.invoice_date.isoformat(),
                    "invoice_value": o.invoice_value}


class BillInfoDecoder:
    @staticmethod
    def json_decode(o):
        if "service_name" in o:
            return BillInfo(
                service_name=o["service_name"],
                invoice_date=date.fromisoformat(o["invoice_date"]),
                invoice_value=o["invoice_value"]
            )
        elif "bill_info" in o:
            return BillInfoResult(
                bill_info=o["bill_info"],
                pdf_location=o["pdf_location"]
            )
