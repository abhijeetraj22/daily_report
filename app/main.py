from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS
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

    # Check if file exists
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
