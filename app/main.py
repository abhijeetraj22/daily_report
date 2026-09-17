from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
import json
import base64
from fastapi.middleware.cors import CORSMiddleware

# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI()
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


# ============================================================
# GITHUB CONFIGURATION
# ============================================================

REPO_OWNER = "abhijeetraj22"
REPO_NAME = "daily_report_storage"
BRANCH = "main"


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def home():

    return {
        "status": "online",
        "service": "Daily Report"
    }


# ============================================================
# IMAGE SAVE
# ============================================================

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


    # --------------------------------------------------------
    # CHECK EXISTING FILE
    # --------------------------------------------------------

    r = requests.get(
        url,
        headers=headers
    )

    sha = None

    if r.status_code == 200:

        sha = r.json()["sha"]


    # --------------------------------------------------------
    # GITHUB PAYLOAD
    # --------------------------------------------------------

    payload = {

        "message": f"Save report {data.date}",

        "content": data.image,

        "branch": BRANCH
    }


    if sha:

        payload["sha"] = sha


    # --------------------------------------------------------
    # SAVE FILE
    # --------------------------------------------------------

    response = requests.put(
        url,
        headers=headers,
        json=payload
    )


    return {

        "github_status":
            response.status_code,

        "github_response":
            response.json()
    }


# ============================================================
# JSON REPORT MODEL
# ============================================================

class ReportJSON(BaseModel):

    date: str

    day: str

    rows: list


# ============================================================
# BULLET + ICON SUPPORT
# ============================================================

def process_rows(rows):

    """
    Preserve the complete row structure.

    Supported fields:

        type
        cells
        bullets
        icon

    Example:

    {
        "type": "data",
        "cells": [
            "4",
            "Collected notebooks from the following classes:",
            "",
            ""
        ],
        "bullets": [
            "5 ZETA [SCIENCE]",
            "6 OMEGA [HINDI]",
            "6 ZETA [MATHS]"
        ],
        "icon": "mdi:notebook-multiple"
    }

    IMPORTANT:

    - Existing icons are preserved.
    - Existing bullets are preserved.
    - No icon is generated.
    - No bullet is removed.
    - Empty bullets remain [].
    """


    processed_rows = []


    for row in rows:


        # ----------------------------------------------------
        # Make sure row is a dictionary
        # ----------------------------------------------------

        if not isinstance(row, dict):

            processed_rows.append(row)

            continue


        # ----------------------------------------------------
        # TYPE
        # ----------------------------------------------------

        row_type = row.get(
            "type",
            "data"
        )


        # ----------------------------------------------------
        # CELLS
        # ----------------------------------------------------

        cells = row.get(
            "cells",
            []
        )


        if not isinstance(cells, list):

            cells = []


        processed_cells = []


        for cell in cells:

            if cell is None:

                processed_cells.append("")

            else:

                # Preserve line breaks and bullet characters

                text = str(cell)

                text = text.replace(
                    "\r\n",
                    "\n"
                )

                text = text.replace(
                    "\r",
                    "\n"
                )

                processed_cells.append(
                    text
                )


        # ----------------------------------------------------
        # BULLETS
        # ----------------------------------------------------

        bullets = row.get(
            "bullets",
            []
        )


        if bullets is None:

            bullets = []


        if not isinstance(
            bullets,
            list
        ):

            bullets = [str(bullets)]


        processed_bullets = []


        for bullet in bullets:

            if bullet is None:

                continue


            bullet_text = str(
                bullet
            ).strip()


            if bullet_text:

                processed_bullets.append(
                    bullet_text
                )


        # ----------------------------------------------------
        # ICON
        # ----------------------------------------------------

        icon = row.get(
            "icon",
            ""
        )


        if icon is None:

            icon = ""


        icon = str(icon)


        # ----------------------------------------------------
        # BUILD ROW
        # ----------------------------------------------------

        processed_row = {

            "type":
                row_type,

            "cells":
                processed_cells,

            "bullets":
                processed_bullets,

            "icon":
                icon
        }


        processed_rows.append(
            processed_row
        )


    return processed_rows


# ============================================================
# SAVE JSON REPORT
# ============================================================

@app.post("/save-report-json")
def save_report_json(data: ReportJSON):

    file_path = (
        f"json/{data.date}.json"
    )


    url = (
        f"https://api.github.com/repos/"
        f"{REPO_OWNER}/{REPO_NAME}/contents/{file_path}"
    )


    headers = {

        "Authorization":
            f"token {GITHUB_TOKEN}",

        "Accept":
            "application/vnd.github+json"
    }


    # --------------------------------------------------------
    # CHECK EXISTING JSON
    # --------------------------------------------------------

    sha = None


    r = requests.get(
        url,
        headers=headers
    )


    if r.status_code == 200:

        sha = r.json()["sha"]


    # --------------------------------------------------------
    # PROCESS ROWS
    # --------------------------------------------------------

    processed_rows = process_rows(
        data.rows
    )


    # --------------------------------------------------------
    # CREATE REPORT DATA
    # --------------------------------------------------------

    report_data = {

        "date":
            data.date,

        "day":
            data.day,

        "rows":
            processed_rows
    }


    # --------------------------------------------------------
    # CONVERT JSON
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

        content_json.encode(
            "utf-8"
        )

    ).decode(
        "utf-8"
    )


    # --------------------------------------------------------
    # GITHUB PAYLOAD
    # --------------------------------------------------------

    payload = {

        "message":
            f"Save report JSON {data.date}",

        "content":
            encoded,

        "branch":
            BRANCH
    }


    if sha:

        payload["sha"] = sha


    # --------------------------------------------------------
    # SAVE TO GITHUB
    # --------------------------------------------------------

    response = requests.put(

        url,

        headers=headers,

        json=payload
    )


    # --------------------------------------------------------
    # RETURN RESULT
    # --------------------------------------------------------

    return {

        "status":
            "json saved",

        "github_status":
            response.status_code,

        "github_response":
            response.json()
    }


# ============================================================
# SECURITY CODE
# ============================================================

class CodeCheck(BaseModel):

    code: str


@app.post("/verify-code")
def verify_code(data: CodeCheck):

    # ========================================================
    # KEEP YOUR ORIGINAL WORKING LOGIN
    # ========================================================

    SECRET_CODE = os.getenv(
        "SECRET_KEY"
    )


    # ========================================================
    # VERIFY CODE
    # ========================================================

    if data.code == SECRET_CODE:

        return {
            "status": "success"
        }

    else:

        return {
            "status": "fail"
        }
