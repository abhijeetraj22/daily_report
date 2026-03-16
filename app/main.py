from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
import json
import base64
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

REPO_OWNER = "abhijeetraj22"
REPO_NAME = "daily_report_storage"
BRANCH = "main"


# ---------- IMAGE SAVE ----------
class Report(BaseModel):
    date: str
    image: str


@app.post("/save-report")
def save_report(data: Report):

    file_path = f"reports/{data.date}.png"

    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    r = requests.get(url, headers=headers)

    sha = None
    if r.status_code == 200:
        sha = r.json()["sha"]

    payload = {
        "message": f"Save report {data.date}",
        "content": data.image,
        "branch": BRANCH
    }

    if sha:
        payload["sha"] = sha

    response = requests.put(url, headers=headers, json=payload)

    return {
        "github_status": response.status_code,
        "github_response": response.json()
    }


# ---------- JSON SAVE ----------
class ReportJSON(BaseModel):
    date: str
    day: str
    rows: list


@app.post("/save-report-json")
def save_report_json(data: ReportJSON):

    file_path = f"json/{data.date}.json"

    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    # check if file exists
    r = requests.get(url, headers=headers)

    sha = None
    if r.status_code == 200:
        sha = r.json()["sha"]

    # convert JSON to text
    content_text = json.dumps(data.dict(), indent=2)

    # encode to base64 (GitHub requirement)
    encoded_content = base64.b64encode(content_text.encode()).decode()

    payload = {
        "message": f"Save report JSON {data.date}",
        "content": encoded_content,
        "branch": BRANCH
    }

    if sha:
        payload["sha"] = sha

    response = requests.put(url, headers=headers, json=payload)

    return {
        "github_status": response.status_code,
        "github_response": response.json()
    }
