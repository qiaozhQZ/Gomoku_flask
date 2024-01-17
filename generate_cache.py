import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By


options = webdriver.ChromeOptions()
options.add_experimental_option("detach", True)
driver = webdriver.Chrome(options=options)
# driver = webdriver.Chrome(r"./driver/chromedriver") 

def launch_browser(url):
    driver.get(url)
    return driver

# def connect_gomoku():
#     pass

def goto_training():
    time.sleep(10)
    consent_agree_button = driver.find_element_by_link_text("I agree")
    consent_agree_button.click()
    insturctions_yes_button = driver.find_element_by_link_text("yes")
    insturctions_yes_button.click()

def random_click():
    pass

if __name__ == "__main__":
    url = "https://gomoku.apprentice.ai/consent"
    driver = launch_browser(url)
    goto_training()