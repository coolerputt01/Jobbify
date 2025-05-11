# Requests Library is used to habdle HTTP requests across the web through TCP - Transmission Control Protocol.
import requests

#I used this specially to bypass Cloudfare.
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
# BeautifulSoup is the library that is making the scraping possible.
from bs4 import BeautifulSoup

# Dotenv was used so that I can save my credentials in a .env file and allow my script to access them while running.
from dotenv import load_dotenv

# Schedule is just a library used to automate the task for a particular fixed period of intervals of time.
import schedule
# This is a library to get time device time.
import time
# I used this to parse some objects so that they can be decoded in base64, or simply just to parse an object
import json
# Base64 endcoding library.
import base64
# OS for os-based operations.
import os
# To generate a file.
import tempfile

# Telegram Bot credentials.
API_TOKEN = os.getenv("API_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Github Credentials.
GTOKEN = os.getenv("GITHUB_TOKEN")
G_URL = os.getenv("GITHUB_API_URL")
REPO_OWNER = os.getenv("REPO_OWNER")
REPO_NAME = os.getenv("REPO_NAME")
FILE_PATH = os.getenv("FILE_PATH")

# My JSON file-path.
JSON_PATH = f"{G_URL}/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"

# Github header for writing and reading data from file on github.
headers = {
    "Authorization": f"token {GTOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

# Get selenium headless browser up and running.
def get_driver():
    options = Options()
    service = Service(ChromeDriverManager().install())
    options.headless = True
    options.add_argument("--headless=new")
    options.add_argument('--no-sandbox')
    # This fixes CI/CD container issues btw.
    options.add_argument('--disable-dev-shm-usage')
    # I'm trying to prevent user session from clashing
    user_data_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={user_data_dir}")
    web_driver = webdriver.Chrome(
        service=service ,
        options = options
    )
    return web_driver

# Send message logic.
def send_message_to_group(message):
    try:
        URL = f"https://api.telegram.org/bot{API_TOKEN}/sendMessage"
        payload = {
            "chat_id":CHAT_ID,
            "text":message
        }
        response = requests.post(URL,payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending message :{e}")
        return None

# This just checks for repeating jobs and prevents them from being sent.
def check_valid_jobs(path,headers):
    try:
        response = requests.get(path,headers)
        data = response.json()
        # I have to decode because Github API returns the document content in a base64 format.
        decoded = base64.b64decode(data['content']).decode('utf-8').strip()
        # json.loads() returns value as a text btw.
        return json.loads(decoded)
    except Exception as e :
        print(e)

# Function to scrape jobs.
def scrape_jobs():
    # I am using Jobberman btw.
    URL = "https://www.jobberman.com/jobs/software-data"
    driver = get_driver()
    driver.get(URL)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    job_cards = soup.find_all('div', attrs={'data-cy':'listing-cards-components'})
    job_list = []

    for card in job_cards:
        # --- Job Title ---
        title_tag = card.find('p',class_='text-lg')
        job_title = title_tag.get_text(strip=True) if title_tag else "No Title"

        # --- Job Link ---
        link_tag = card.find('a', class_='relative',attrs={'data-cy':'listing-title-link'})
        job_link = f"{link_tag['href']}"

        # --- Salary (optional) ---
        description_tag = card.find('p', class_="md:pl-5")
        job_desc = description_tag.get_text(strip=True)

        job_data = {
            'title': job_title,
            'link': job_link,
            'description': f"{job_desc} | Description: {job_desc}"
        }

        job_list.append(job_data)

    json_arrays = check_valid_jobs(JSON_PATH,headers)
    # Now I am checking for duplicate jibs to avoid repitition usinga list comprehension method.
    saved_links = [job['link'] for job in json_arrays]
    new_jobs = [job for job in job_list if job['link'] not in saved_links]
    return new_jobs

# Function to post jobs to my public JSON server.
def post_jobs_to_json_server(path,array,headers):
    try:
        response = requests.get(path,headers=headers)
        file_info = response.json()
        sha = file_info['sha']

        # Github forces me to encode the content I pass into it.
        encoded_content = base64.b64encode(json.dumps(array).encode('utf-8')).decode('utf-8')
        
        update_data = {
            "message": "Updating job listings",
            "committer": {
                "name": REPO_OWNER,
                "email": "olumideadekolu9@gmail.com"
            },
            "sha": sha,
            "content": encoded_content
        }
        response = requests.put(path, headers=headers, data=json.dumps(update_data))
    except Exception as e :
        print(e)

# Handle sending and updating messages.
def send_job_updates():
    job_lists = scrape_jobs()
    message = "🚀 New Job Listings:\n\n"
    if not job_lists:
        print("No Jobs Available")
        message = "No Available Jobs"
        send_message_to_group(message)
        return
    
    for jobs in job_lists:
        message = f"{jobs['title']} \n {jobs['description']} \n {jobs['link']}\n"
        post_jobs_to_json_server(JSON_PATH,job_lists,headers)
        send_message_to_group(message)

# Run code every 5 minutes.
schedule.every(5).minutes.do(send_job_updates)


# Keeping it to run a loop on start.
if __name__ == "__main__":
    print("Jobbify is working")
    while True:
        schedule.run_pending()
        time.sleep(30)
