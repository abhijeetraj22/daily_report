from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
import json
import base64
from fastapi.middleware.cors import CORSMiddleware

# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Daily Report OLD Backend",
    version="2.0"
)

# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# IMPORTANT:
# This OLD Render service must have its OWN variable:
#
# SECURITY_CODE = YOUR_OLD_CODE
#
# DO NOT use SECRET_KEY here.
#
SECURITY_CODE = os.getenv("SECURITY_CODE")

# ============================================================
# GITHUB CONFIGURATION
# ============================================================

REPO_OWNER = "abhijeetraj22"
REPO_NAME = "daily_report_storage"
BRANCH = "main"

# ============================================================
# BASIC HEALTH CHECK
# ============================================================

@app.get("/")
def home():

    return {
        "status": "online",
        "service": "Daily Report OLD Backend",
        "version": "2.0"
    }


# ============================================================
# GITHUB HELPER
# ============================================================

def github_headers():

    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }


def github_file_url(file_path):

    return (
        f"https://api.github.com/repos/"
        f"{REPO_OWNER}/"
        f"{REPO_NAME}/"
        f"contents/{file_path}"
    )


# ============================================================
# IMAGE REPORT MODEL
# ============================================================

class Report(BaseModel):

    date: str
    image: str


# ============================================================
# SAVE PNG REPORT TO GITHUB
# ============================================================

@app.post("/save-report")
def save_report(data: Report):

    if not GITHUB_TOKEN:

        return {
            "status": "fail",
            "message": "GITHUB_TOKEN is not configured."
        }


    file_path = f"reports/{data.date}.png"

    url = github_file_url(file_path)

    headers = github_headers()


    # --------------------------------------------------------
    # CHECK IF FILE ALREADY EXISTS
    # --------------------------------------------------------

    try:

        r = requests.get(
            url,
            headers=headers,
            timeout=30
        )

    except requests.RequestException as e:

        return {
            "status": "fail",
            "message": f"GitHub connection error: {str(e)}"
        }


    sha = None

    if r.status_code == 200:

        try:

            sha = r.json().get("sha")

        except Exception:

            sha = None

    elif r.status_code not in [404]:

        return {
            "status": "fail",
            "github_status": r.status_code,
            "github_response": r.text
        }


    # --------------------------------------------------------
    # PREPARE GITHUB PAYLOAD
    # --------------------------------------------------------

    payload = {

        "message": f"Save report {data.date}",

        "content": data.image,

        "branch": BRANCH
    }


    # If file already exists,
    # GitHub requires SHA for updating it.

    if sha:

        payload["sha"] = sha


    # --------------------------------------------------------
    # UPLOAD / UPDATE FILE
    # --------------------------------------------------------

    try:

        response = requests.put(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )

    except requests.RequestException as e:

        return {
            "status": "fail",
            "message": f"GitHub upload error: {str(e)}"
        }


    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    try:

        github_response = response.json()

    except Exception:

        github_response = {
            "message": response.text
        }


    if response.status_code in [200, 201]:

        return {

            "status": "success",

            "message": "PNG report saved successfully.",

            "github_status": response.status_code,

            "github_response": github_response
        }


    return {

        "status": "fail",

        "message": "Failed to save PNG report.",

        "github_status": response.status_code,

        "github_response": github_response
    }


# ============================================================
# JSON REPORT MODEL
# ============================================================

class ReportJSON(BaseModel):

    date: str

    day: str

    rows: list


# ============================================================
# BULLET NORMALIZATION
# ============================================================

def normalize_cell_text(text):

    """
    Preserve bullet-point text and line breaks.

    Supported examples:

    * First task
    * Second task

    • First task
    • Second task

    - First task
    - Second task

    Nested items are also preserved.

    Example:

    * Collected notebooks:
    * 5 ZETA [SCIENCE]
    * 6 OMEGA [HINDI]
    """

    if text is None:

        return ""


    text = str(text)


    # Normalize Windows line endings

    text = text.replace("\r\n", "\n")

    text = text.replace("\r", "\n")


    lines = text.split("\n")


    cleaned_lines = []


    for line in lines:

        # Remove trailing spaces only.
        # DO NOT remove leading spaces because
        # they may represent nested bullet formatting.

        line = line.rstrip()


        # Preserve completely blank lines

        if not line.strip():

            cleaned_lines.append("")

            continue


        # Preserve bullet characters exactly

        stripped = line.lstrip()


        if (
            stripped.startswith("* ")
            or stripped.startswith("• ")
            or stripped.startswith("- ")
        ):

            # Keep the bullet.
            # Remove unnecessary indentation before bullet
            # while preserving the actual bullet text.

            cleaned_lines.append(stripped)

        else:

            cleaned_lines.append(line)


    return "\n".join(cleaned_lines)


# ============================================================
# NORMALIZE ALL ROWS
# ============================================================

def normalize_rows(rows):

    normalized_rows = []


    for row in rows:

        # ----------------------------------------------------
        # Invalid row
        # ----------------------------------------------------

        if not isinstance(row, dict):

            normalized_rows.append(row)

            continue


        new_row = dict(row)


        # ----------------------------------------------------
        # ROW TYPE
        # ----------------------------------------------------

        row_type = new_row.get("type", "data")


        if row_type == "section":

            new_row["type"] = "section"

        else:

            new_row["type"] = "data"


        # ----------------------------------------------------
        # CELLS
        # ----------------------------------------------------

        cells = new_row.get("cells", [])


        if not isinstance(cells, list):

            cells = []


        new_cells = []


        for cell in cells:

            new_cells.append(
                normalize_cell_text(cell)
            )


        new_row["cells"] = new_cells


        normalized_rows.append(new_row)


    return normalized_rows


# ============================================================
# DETECT SECTION
# ============================================================

def normalize_section_name(text):

    """
    Converts section headings into clean text.

    Examples:

    *EXAMINATION WORKS:*

    EXAMINATION WORKS

    *OTHER WORK*

    OTHER WORK
    """

    if text is None:

        return ""


    text = str(text).strip()


    # Remove surrounding *

    if (
        text.startswith("*")
        and text.endswith("*")
        and len(text) > 2
    ):

        text = text[1:-1].strip()


    # Remove final colon

    text = text.rstrip(":")


    return text.strip()


# ============================================================
# JSON SAVE
# ============================================================

@app.post("/save-report-json")
def save_report_json(data: ReportJSON):

    if not GITHUB_TOKEN:

        return {

            "status": "fail",

            "message": "GITHUB_TOKEN is not configured."
        }


    # --------------------------------------------------------
    # FILE PATH
    # --------------------------------------------------------

    file_path = f"json/{data.date}.json"


    url = github_file_url(file_path)

    headers = github_headers()


    # --------------------------------------------------------
    # CHECK EXISTING FILE
    # --------------------------------------------------------

    try:

        r = requests.get(
            url,
            headers=headers,
            timeout=30
        )

    except requests.RequestException as e:

        return {

            "status": "fail",

            "message": f"GitHub connection error: {str(e)}"
        }


    sha = None


    if r.status_code == 200:

        try:

            sha = r.json().get("sha")

        except Exception:

            sha = None


    elif r.status_code != 404:

        return {

            "status": "fail",

            "github_status": r.status_code,

            "github_response": r.text
        }


    # --------------------------------------------------------
    # NORMALIZE ROWS
    # --------------------------------------------------------

    normalized_rows = normalize_rows(
        data.rows
    )


    # --------------------------------------------------------
    # BUILD FINAL JSON
    # --------------------------------------------------------

    report_data = {

        "date": data.date,

        "day": data.day,

        "rows": normalized_rows
    }


    # --------------------------------------------------------
    # CONVERT JSON TO STRING
    # --------------------------------------------------------

    content_json = json.dumps(

        report_data,

        indent=2,

        ensure_ascii=False
    )


    # --------------------------------------------------------
    # BASE64 ENCODE
    # --------------------------------------------------------

    encoded = base64.b64encode(

        content_json.encode("utf-8")

    ).decode("utf-8")


    # --------------------------------------------------------
    # GITHUB PAYLOAD
    # --------------------------------------------------------

    payload = {

        "message": f"Save report JSON {data.date}",

        "content": encoded,

        "branch": BRANCH
    }


    if sha:

        payload["sha"] = sha


    # --------------------------------------------------------
    # SAVE TO GITHUB
    # --------------------------------------------------------

    try:

        response = requests.put(

            url,

            headers=headers,

            json=payload,

            timeout=60
        )

    except requests.RequestException as e:

        return {

            "status": "fail",

            "message": f"GitHub upload error: {str(e)}"
        }


    try:

        github_response = response.json()

    except Exception:

        github_response = {

            "message": response.text
        }


    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    if response.status_code in [200, 201]:

        return {

            "status": "success",

            "message": "JSON report saved successfully.",

            "github_status": response.status_code
        }


    # --------------------------------------------------------
    # FAILURE
    # --------------------------------------------------------

    return {

        "status": "fail",

        "message": "Failed to save JSON report.",

        "github_status": response.status_code,

        "github_response": github_response
    }


# ============================================================
# SECURITY CODE MODEL
# ============================================================

class CodeCheck(BaseModel):

    code: str


# ============================================================
# VERIFY SECURITY CODE
# ============================================================

@app.post("/verify-code")
def verify_code(data: CodeCheck):

    # --------------------------------------------------------
    # Read THIS Render service's environment variable
    # --------------------------------------------------------

    configured_code = os.getenv(
        "SECURITY_CODE"
    )


    # --------------------------------------------------------
    # SECURITY CODE NOT CONFIGURED
    # --------------------------------------------------------

    if not configured_code:

        return {

            "status": "fail",

            "message":
                "Security code is not configured on this Render service."
        }


    # --------------------------------------------------------
    # VERIFY
    # --------------------------------------------------------

    if data.code == configured_code:

        return {

            "status": "success"
        }


    # --------------------------------------------------------
    # WRONG CODE
    # --------------------------------------------------------

    return {

        "status": "fail"
    }


# ============================================================
# SECURITY STATUS
# ============================================================

@app.get("/security-status")
def security_status():

    """
    Safe diagnostic endpoint.

    IMPORTANT:
    It NEVER returns the actual Security Code.
    """

    configured_code = os.getenv(
        "SECURITY_CODE"
    )


    return {

        "security_code_configured":
            bool(configured_code),

        "security_code_length":
            len(configured_code)
            if configured_code
            else 0,

        "service":
            "Daily Report OLD Backend"
    }
