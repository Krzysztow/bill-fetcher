import requests
from selenium import webdriver as wd
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait


def accept_cookies(driver):
    # TODO: check why we cannot set cookie instead of interacting
    # driver.add_cookie({'name': 'ho_cookie_consent', 'value': 'essential'})
    accept_cookies_form_el = driver.find_element(By.ID, 'cookie_policy')
    accept_cookies_buttons_el = accept_cookies_form_el.find_element(By.CLASS_NAME, "accept")
    accept_cookies_buttons_el.click()


def fill_and_submit_login_form(driver, username, password):
    login_form_el = driver.find_element(By.ID, "loginForm")

    email_el = login_form_el.find_element(By.ID, "email")
    email_el.send_keys(username)

    password_el = login_form_el.find_element(By.ID, "password")
    password_el.send_keys(password)

    login_form_el.find_element(By.ID, "btnSubmit").click()


def retrieve_last_bill_data(driver, right_col):
    return None


def retrieve_last_bill_pdf(driver, right_col, out_pdf_path):
    right_col.find_element(By.XPATH, "//button[text()='View latest bill']").click()

    src = driver.find_element(By.ID, 'iframeBill').get_attribute("src")
    driver.get(src)

    cookies_dict = {c['name']: c['value'] for c in driver.get_cookies()}
    response = requests.get(src, cookies=cookies_dict)
    with open(out_pdf_path, mode="wb") as f:
        f.write(response.content)


def get_last_bill_info(webdriver_location, username, password):
    with wd.Chrome(webdriver_location) as driver:
        driver.get("https://hyperoptic.com/myaccount-login/")

        accept_cookies(driver)
        fill_and_submit_login_form(driver, username, password)

        WebDriverWait(driver, 10).until(ec.presence_of_element_located((By.ID, "right-column")))
        right_col = driver.find_element(By.ID, "right-column")

        last_bill_data = retrieve_last_bill_data(driver, right_col)
        retrieve_last_bill_pdf(driver, right_col, "/tmp/requests.pdf")

        pass


def main():
    webdriver_location = "/tmp/chromedriver/chromedriver"
    username = ""
    password = ""

    get_last_bill_info(webdriver_location, username, password)


main()
