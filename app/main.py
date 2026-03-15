from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app = FastAPI()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = "abhijeetraj22"
REPO_NAME = "daily_report"
BRANCH = "main"

class Report(BaseModel):
    date: str
    image: str

@app.post("/save-report")
def save_report(data: Report):

    file_path = f"reports/{data.date}.png"

    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}"

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    payload = {
        "message": f"Save report {data.date}",
        "content": data.image,
        "branch": BRANCH
    }

    response = requests.put(url, headers=headers, json=payload)

    return {
        "status": "saved",
        "github_response": response.json()
    }
