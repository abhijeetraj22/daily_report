```python
from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
import json
import base64
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# IMPORTANT:
# This OLD Render service must have its OWN SECURITY_CODE
SECURITY_CODE = os.getenv("SECURITY_CODE")


# =========================================================
# GITHUB CONFIGURATION
# =========================================================

REPO_OWNER = "abhijeetraj22"
REPO_NAME = "daily_report_storage"
BRANCH = "main"


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/")
def home():
    return {
        "status": "online",
        "service": "Daily Report OLD Backend"
    }


# =========================================================
# IMAGE SAVE
# =========================================================

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

    # Check whether file already exists
    r = requests.get(url, headers=headers)

    sha = None

    if r.status_code == 200:
        sha = r.json().get("sha")

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


# =========================================================
# JSON REPORT MODEL
# =========================================================

class ReportJSON(BaseModel):
    date: str
    day: str
    rows: list


# =========================================================
# BULLET NORMALIZATION
# =========================================================

def normalize_cell_text(text):
    """
    Preserve bullet-point content.

    Supported bullet styles:
        * text
        - text
        • text

    The function does NOT remove bullet characters.
    It only normalizes unnecessary spaces.
    """

    if text is None:
        return ""

    text = str(text)

    lines = text.splitlines()

    cleaned_lines = []

    for line in lines:

        line = line.rstrip()

        if not line.strip():
            cleaned_lines.append("")
            continue

        stripped = line.lstrip()

        # Preserve bullet symbols
        if (
            stripped.startswith("* ")
            or stripped.startswith("- ")
            or stripped.startswith("• ")
        ):
            cleaned_lines.append(stripped)
        else:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


# =========================================================
# PREPARE ROW DATA
# =========================================================

def normalize_rows(rows):

    normalized_rows = []

    for row in rows:

        if not isinstance(row, dict):
            normalized_rows.append(row)
            continue

        new_row = dict(row)

        cells = new_row.get("cells", [])

        if isinstance(cells, list):

            new_cells = []

            for cell in cells:
                new_cells.append(
                    normalize_cell_text(cell)
                )

            new_row["cells"] = new_cells

        normalized_rows.append(new_row)

    return normalized_rows


# =========================================================
# JSON SAVE
# =========================================================

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

    # -----------------------------------------------------
    # Check existing JSON
    # -----------------------------------------------------

    sha = None

    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        sha = r.json().get("sha")

    # -----------------------------------------------------
    # Preserve bullet-point rows
    # -----------------------------------------------------

    normalized_rows = normalize_rows(data.rows)

    report_data = {
        "date": data.date,
        "day": data.day,
        "rows": normalized_rows
    }

    # -----------------------------------------------------
    # Convert JSON to Base64
    # -----------------------------------------------------

    content_json = json.dumps(
        report_data,
        indent=2,
        ensure_ascii=False
    )

    encoded = base64.b64encode(
        content_json.encode("utf-8")
    ).decode("utf-8")

    # -----------------------------------------------------
    # GitHub payload
    # -----------------------------------------------------

    payload = {
        "message": f"Save report JSON {data.date}",
        "content": encoded,
        "branch": BRANCH
    }

    if sha:
        payload["sha"] = sha

    # -----------------------------------------------------
    # Upload to GitHub
    # -----------------------------------------------------

    response = requests.put(
        url,
        headers=headers,
        json=payload
    )

    return {
        "status": "json saved",
        "github_status": response.status_code
    }


# =========================================================
# SECURITY CODE
# =========================================================

class CodeCheck(BaseModel):
    code: str


@app.post("/verify-code")
def verify_code(data: CodeCheck):

    # Security Code comes ONLY from this Render service
    configured_code = os.getenv("SECURITY_CODE")

    if not configured_code:
        return {
            "status": "fail",
            "message": "Security code is not configured on this Render service."
        }

    if data.code == configured_code:

        return {
            "status": "success"
        }

    return {
        "status": "fail"
    }


# =========================================================
# OPTIONAL SECURITY STATUS
# =========================================================

@app.get("/security-status")
def security_status():

    configured_code = os.getenv("SECURITY_CODE")

    return {
        "security_code_configured": bool(configured_code),
        "security_code_length": len(configured_code)
        if configured_code
        else 0
    }
```
