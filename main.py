from playwright.sync_api import sync_playwright
import time
from flask import Flask, render_template, request, redirect, send_file
import requests
from bs4 import BeautifulSoup
import csv

app = Flask(__name__)
"""
Do this when scraping a website to avoid getting blocked.
headers = {
      'User-Agent':
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
      'Accept':
      'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
      'Accept-Language': 'en-US,en;q=0.5',
}
response = requests.get(URL, headers=headers)
"""


def get_content(keyword):
    page_contents = {}
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=False)

    urls = {
        "berlinstartupjobs":
        f"https://berlinstartupjobs.com/skill-areas/{keyword}/",
        "web3":
        f"https://web3.career/{keyword}-jobs",
        "wwr":
        f"https://weworkremotely.com/remote-jobs/search?utf8=%E2%9C%93&term={keyword}"
    }
    for key in urls:
        page = browser.new_page()
        page.goto(urls[key])

        for x in range(3):
            time.sleep(1)
            page.keyboard.down("End")
        page_contents[f"{key}"] = page.content()
    p.stop()

    return page_contents


class Job:

    def __init__(self, language, platform, title, company, link):
        self.language = language
        self.platform = platform
        self.title = title
        self.company = company
        self.link = link


class Job_db:

    def __init__(self, platform):
        self.platform = platform
        self.jobs = []

    def add_job(self, job):
        new_job = Job(job.language, self.platform, job.title, job.company,
                      job.link)
        self.jobs.append(new_job)


def get_job_data_berlin(language, content):

    job_platform = Job_db("berlinstartupjobs")
    soup = BeautifulSoup(content["berlinstartupjobs"], "html.parser")
    jobs = soup.find_all("li", class_="bjs-jlid")

    for job in jobs:
        link = job.find('a')['href']
        title = job.find("h4", class_="bjs-jlid__h").text
        company = job.find("a", class_="bjs-jlid__b").text
        job = Job(language, "berlinstartupjobs", title, company, link)
        job_platform.add_job(job)
    return job_platform


def get_job_data_web3(language, content):

    job_platform = Job_db("web3")
    soup = BeautifulSoup(content["web3"], "html.parser")
    jobs = soup.find_all("tr", class_="table_row")
    for job in jobs:
        link = f"https://web3.career{job.find('a')['href']}"
        title = job.find("a").text
        company = job.find("td", class_="job-location-mobile").text
        job = Job(language, "web3", title, company, link)
        job_platform.add_job(job)

    return job_platform


def get_job_data_wwr(language, content):

    job_platform = Job_db("wwr")
    soup = BeautifulSoup(content["wwr"], "html.parser")
    jobs = soup.find_all("a", class_="listing-link--unlocked")

    for job in jobs:
        link = f"https://weworkremotely.com{job['href']}"
        title = job.find("h3", class_="new-listing__header__title").text
        company = job.find("p", class_="new-listing__company-name").text
        job = Job(language, "wwr", title, company, link)
        job_platform.add_job(job)

    return job_platform


def write_down_csv_oop(job_db, keyword=""):
    file = open(f"jobs_OOP_{keyword}.csv",
                "w",
                encoding="utf-8-sig",
                newline="")
    writer = csv.writer(file)
    writer.writerow(["Playform", "Language", "Title", "Company", "Link"])

    for job in job_db:
        writer.writerow(
            [job.platform, job.language, job.company, job.title, job.link])
    file.close()


db = {}


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/search")
def search():
    keyword = request.args.get("keyword")
    if keyword == None:
        return redirect("/")
    if keyword in db:
        job_data = db[keyword]
    else:
        contents = get_content(keyword)
        job_data = get_job_data_berlin(keyword, contents).jobs
        job_data = job_data + get_job_data_web3(keyword, contents).jobs
        job_data = job_data + get_job_data_wwr(keyword, contents).jobs
        db[keyword] = job_data
    return render_template("search.html", keyword=keyword, jobs=job_data)


@app.route("/export")
def export():
    keyword = request.args.get("keyword")
    if keyword == None:
        return redirect("/")
    if keyword not in db:
        return redirect(f"/search?keyword={keyword}")
    write_down_csv_oop(db[keyword], keyword)
    return send_file(f"jobs_OOP_{keyword}.csv", as_attachment=True)


if __name__ == "__main__":
    app.run()
