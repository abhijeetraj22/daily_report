from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
import json
import base64
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

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


@app.get("/")
def home():
    return {
        "status": "online",
        "service": "Daily Report"
    }


class Report(BaseModel):
    date: str
    image: str


@app.post("/save-report")
def save_report(data: Report):
    file_path = f"reports/{data.date}.png"

    url = (
        f"https://api.github.com/repos/"
        f"{REPO_OWNER}/{REPO_NAME}/contents/{file_path}"
    )

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
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

    response = requests.put(
        url,
        headers=headers,
        json=payload
    )

    return {
        "github_status": response.status_code,
        "github_response": response.json()
    }


class ReportJSON(BaseModel):
    date: str
    day: str
    rows: list


@app.post("/save-report-json")
def save_report_json(data: ReportJSON):
    file_path = f"json/{data.date}.json"

    url = (
        f"https://api.github.com/repos/"
        f"{REPO_OWNER}/{REPO_NAME}/contents/{file_path}"
    )

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    # Check existing JSON so GitHub can update it.
    sha = None

    r = requests.get(
        url,
        headers=headers
    )

    if r.status_code == 200:
        sha = r.json()["sha"]

    # IMPORTANT:
    # Save the rows exactly as received from the OLD frontend.
    #
    # This means:
    #   cells   -> remains cells
    #   bullets -> remains bullets
    #   no icon is generated
    #   no bullet is moved into cells
    #   no extra fields are added
    report_data = {
        "date": data.date,
        "day": data.day,
        "rows": data.rows
    }

    content_json = json.dumps(
        report_data,
        indent=2,
        ensure_ascii=False
    )

    encoded = base64.b64encode(
        content_json.encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": f"Save report JSON {data.date}",
        "content": encoded,
        "branch": BRANCH
    }

    if sha:
        payload["sha"] = sha

    response = requests.put(
        url,
        headers=headers,
        json=payload
    )

    return {
        "status": "json saved",
        "github_status": response.status_code,
        "github_response": response.json()
    }


class CodeCheck(BaseModel):
    code: str


@app.post("/verify-code")
def verify_code(data: CodeCheck):
    # KEEP ORIGINAL WORKING LOGIN UNCHANGED
    SECRET_CODE = os.getenv("SECRET_KEY")

    if data.code == SECRET_CODE:
        return {"status": "success"}
    else:
        return {"status": "fail"}
