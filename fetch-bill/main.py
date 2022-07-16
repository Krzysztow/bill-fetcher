import datetime
from datetime import date

import requests
from dataclasses import dataclass
from selenium import webdriver as wd
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait


@dataclass(frozen=True)
class BillInfo:
    service_name: str
    invoice_value: str
    invoice_date: date


@dataclass(frozen=True)
class BillInfoResult:
    bill_info: BillInfo
    pdf_location: str


def accept_cookies(driver: WebDriver):
    # TODO: check why we cannot set cookie instead of interacting
    # driver.add_cookie({'name': 'ho_cookie_consent', 'value': 'essential'})
    accept_cookies_form_el = driver.find_element(By.ID, 'cookie_policy')
    accept_cookies_buttons_el = accept_cookies_form_el.find_element(By.CLASS_NAME, "accept")
    accept_cookies_buttons_el.click()


def fill_and_submit_login_form(driver: WebDriver, username: str, password: str):
    login_form_el = driver.find_element(By.ID, "loginForm")

    email_el = login_form_el.find_element(By.ID, "email")
    email_el.send_keys(username)

    password_el = login_form_el.find_element(By.ID, "password")
    password_el.send_keys(password)

    login_form_el.find_element(By.ID, "btnSubmit").click()


def retrieve_last_bill_data(driver: WebDriver, left_col: WebElement, right_col: WebElement) -> BillInfo:
    def find_column_value_for(col: WebElement, value_description: str) -> str:
        return col.find_element(By.XPATH, f'//p[text()="{value_description}"]/../following-sibling::div[1]/p').text

    invoice_date_str = find_column_value_for(right_col, "Last invoice date")
    bi = BillInfo(
        invoice_value=find_column_value_for(right_col, "Current invoice"),
        invoice_date=datetime.datetime.strptime(invoice_date_str, "%d %b %Y").date(),
        service_name=find_column_value_for(left_col, "My package")
    )

    return bi


def retrieve_last_bill_pdf(driver, right_col, out_pdf_path):
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
    right_col.find_element(By.XPATH, "//button[text()='View latest bill']").click()

    src = driver.find_element(By.ID, 'iframeBill').get_attribute("src")
    driver.get(src)

    cookies_dict = {c['name']: c['value'] for c in driver.get_cookies()}
    response = requests.get(src, cookies=cookies_dict)
    with open(out_pdf_path, mode="wb") as f:
        f.write(response.content)


def get_last_bill_info(webdriver_location, username, password) -> BillInfoResult:
    with wd.Chrome(webdriver_location) as driver:
        driver.get("https://hyperoptic.com/myaccount-login/")

        accept_cookies(driver)
        fill_and_submit_login_form(driver, username, password)

        WebDriverWait(driver, 10).until(ec.presence_of_element_located((By.ID, "right-column")))
        right_col = driver.find_element(By.ID, "right-column")
        left_col = driver.find_element(By.ID, "left-column")

        pdf_location = "/tmp/requests.pdf"
        last_bill_data = retrieve_last_bill_data(driver, left_col, right_col)
        retrieve_last_bill_pdf(driver, right_col, pdf_location)

        return BillInfoResult(
            bill_info=last_bill_data,
            pdf_location=pdf_location
        )


def main():
    webdriver_location = "/tmp/chromedriver/chromedriver"
    username = ""
    password = ""

    result = get_last_bill_info(webdriver_location, username, password)
    print(f"Finished successfully: {result}")


main()
