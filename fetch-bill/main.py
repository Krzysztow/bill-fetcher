import datetime
import logging
import os

import requests
from selenium import webdriver as wd
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from bill_info_result import BillInfo, BillInfoResult

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class BillFetcher:
    _driver: WebDriver

    def __init__(self):
        opts = Options()
        opts.add_argument("--headless")
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        self._driver = wd.Chrome(options=opts)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._driver.close()

    def accept_cookies(self):
        # TODO: check why we cannot set cookie instead of interacting
        # driver.add_cookie({'name': 'ho_cookie_consent', 'value': 'essential'})
        logger.info("Accept cookies")
        accept_cookies_form_el = self._driver.find_element(By.ID, 'cookie_policy')
        accept_cookies_buttons_el = accept_cookies_form_el.find_element(By.CLASS_NAME, "accept")
        accept_cookies_buttons_el.click()

    def fill_and_submit_login_form(self, username: str, password: str):
        logger.info("Submitting logging information")
        login_form_el = self._driver.find_element(By.ID, "loginForm")

        email_el = login_form_el.find_element(By.ID, "email")
        email_el.send_keys(username)

        password_el = login_form_el.find_element(By.ID, "password")
        password_el.send_keys(password)

        login_form_el.find_element(By.ID, "btnSubmit").click()

    def retrieve_last_bill_data(self, left_col: WebElement, right_col: WebElement) -> BillInfo:
        def find_column_value_for(col: WebElement, value_description: str) -> str:
            return col.find_element(By.XPATH, f'//p[text()="{value_description}"]/../following-sibling::div[1]/p').text

        logger.info("Retrieve last bill data")
        invoice_date_str = find_column_value_for(right_col, "Last invoice date")
        bi = BillInfo(
            invoice_value=find_column_value_for(right_col, "Current invoice"),
            invoice_date=datetime.datetime.strptime(invoice_date_str, "%d %b %Y").date(),
            service_name=find_column_value_for(left_col, "My package")
        )

        return bi

    def retrieve_last_bill_pdf(self, right_col, out_pdf_path):
        """
        <div id="billModal" tabindex="-1" role="dialog" aria-labelledby="myModalLabel" class="modal fade data-hj-suppress in" style="display: block; padding-right: 15px;">
           <div role="document" style="height:90%;" class="modal-dialog modal-lg">
              <div style="width:100%;height:100%;position:absolute;" class="modal-content">
                 <div class="modal-header">
                    <button type="button" data-dismiss="modal" aria-label="Close" class="close"><span aria-hidden="true"></span></button>
                    <h2 class="modal-title">View latest bill - 10 Jul 2022</h2>
                 </div>
                 <div style="position:absolute;top:100px;right:0;bottom:0;left:0;">
                    <div id="sLoader" class="loader custom" style="display: none;">
                       <div class="spinner"></div>
                    </div>
                    <iframe id="iframeBill" style="width:100%;height:100%;box-sizing:border-box;border:none;" title="Bill 10 Jul 2022" src="https://hyperoptic.com/myaccount-get-bill/?invoiceId=29237809"></iframe>
                 </div>
              </div>
           </div>
        </div>
        """
        logger.info("Retrieving PDF")
        right_col.find_element(By.XPATH, "//button[text()='View latest bill']").click()

        src = self._driver.find_element(By.ID, 'iframeBill').get_attribute("src")
        logger.debug(f"Opening PDF source {src}")
        self._driver.get(src)

        logger.debug("Fetching PDF with requests")
        cookies_dict = {c['name']: c['value'] for c in self._driver.get_cookies()}
        response = requests.get(src, cookies=cookies_dict)
        logger.debug(f"Fetching PDF with requests: {response.status_code}")
        with open(out_pdf_path, mode="wb") as f:
            f.write(response.content)

    def get_last_bill_info(self, username, password) -> BillInfoResult:
        self._driver.implicitly_wait(10)
        self._driver.get("https://hyperoptic.com/myaccount-login/")

        self.accept_cookies()
        self.fill_and_submit_login_form(username, password)

        #WebDriverWait(driver, 10).until(ec.presence_of_element_located((By.ID, "right-column")))
        right_col = self._driver.find_element(By.ID, "right-column")
        left_col = self._driver.find_element(By.ID, "left-column")

        pdf_location = "/tmp/requests.pdf"
        last_bill_data = self.retrieve_last_bill_data(left_col, right_col)
        self.retrieve_last_bill_pdf(right_col, pdf_location)

        return BillInfoResult(
            bill_info=last_bill_data,
            pdf_location=pdf_location
        )


def ensure_non_empty(value: str, hint_name: str):
    if not value:
        raise ValueError(f"{hint_name} can not be empty!")


def fetch_bill(username: str, password: str):
    ensure_non_empty(username, "username[HO_USERNAME]")
    ensure_non_empty(password, "username[HO_PASSWORD]")

    logging.info("Starting fetcher...")
    with BillFetcher() as fetcher:
        result = fetcher.get_last_bill_info(username, password)
    logging.info(f"Finished successfully: {result}")


def main():
    username = os.getenv("HO_USERNAME")
    password = os.getenv("HO_PASSWORD")

    fetch_bill(username, password)


main()
