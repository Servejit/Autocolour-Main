import os
import io
import re
import json
import hashlib
import sqlite3
from datetime import datetime, date

import pandas as pd
import numpy as np
import requests
import yfinance as yf
import streamlit as st

from openpyxl import load_workbook, Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="6thSense (6S-FO200) Vardaan",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CONSTANTS / DIRECTORIES
# ============================================================

APP_TITLE = "6thSense (6S-FO200) Vardaan"

DATA_DIR = "data"
MASTER_DIR = os.path.join(DATA_DIR, "master")
DB_FILE = os.path.join(DATA_DIR, "vardaan.db")
MASTER_FILE = os.path.join(MASTER_DIR, "Master.xlsx")

OUTPUT_FILENAME = "6thsense(6S-FO200)Vardaan.xlsx"

DEFAULT_BLUE = "ADD8E6"
DEFAULT_GREEN = "90EE90"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MASTER_DIR, exist_ok=True)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>
    .main-title {
        text-align: center;
        font-size: 32px;
        font-weight: 700;
        margin-top: 5px;
        margin-bottom: 20px;
    }

    .login-box {
        max-width: 430px;
        margin: 35px auto;
        padding: 25px;
        border-radius: 14px;
        border: 1px solid #dddddd;
        background: #fafafa;
    }

    .admin-box {
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #dddddd;
        margin-bottom: 15px;
    }

    .status-box {
        padding: 12px;
        border-radius: 10px;
        background: #f4f4f4;
        border: 1px solid #dddddd;
        margin-bottom: 12px;
    }

    div.stButton > button {
        width: 100%;
        font-weight: 600;
    }

    .small-note {
        color: #666666;
        font-size: 13px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )

    conn.commit()

    defaults = {
        "blue_color": DEFAULT_BLUE,
        "green_color": DEFAULT_GREEN,
        "telegram_enabled": "0",
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "alert_operator": "<",
        "alert_value": "-1.00",
    }

    for key, value in defaults.items():
        cur.execute(
            "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
            (key, value),
        )

    conn.commit()
    conn.close()


init_db()


# ============================================================
# PASSWORD / SETTINGS
# ============================================================

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_setting(key, default=""):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT value FROM settings WHERE key=?",
        (key,),
    )

    row = cur.fetchone()
    conn.close()

    if row is None:
        return default

    return row["value"]


def set_setting(key, value):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO settings(key, value)
        VALUES (?, ?)
        ON CONFLICT(key)
        DO UPDATE SET value=excluded.value
        """,
        (key, str(value)),
    )

    conn.commit()
    conn.close()


# ============================================================
# ADMIN CREDENTIALS
# ============================================================

def get_admin_credentials():

    username = None
    password = None

    try:
        username = st.secrets.get("ADMIN_USERNAME")
        password = st.secrets.get("ADMIN_PASSWORD")
    except Exception:
        pass

    # Local development fallback.
    # For Streamlit Cloud, use Secrets instead.
    if not username:
        username = os.environ.get(
            "ADMIN_USERNAME",
            "VardaanAdmin"
        )

    if not password:
        password = os.environ.get(
            "ADMIN_PASSWORD",
            "MyPassword@123"
        )

    return str(username), str(password)


# ============================================================
# USER MANAGEMENT
# ============================================================

def add_user(username, password):
    username = username.strip()

    if not username or not password:
        return False, "Username and password are required."

    admin_username, _ = get_admin_credentials()

    if username.lower() == admin_username.lower():
        return False, "This username is reserved for Admin."

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT username FROM users WHERE username=?",
        (username,),
    )

    if cur.fetchone():
        conn.close()
        return False, "User already exists."

    cur.execute(
        """
        INSERT INTO users(
            username,
            password_hash,
            enabled,
            created_at
        )
        VALUES (?, ?, 1, ?)
        """,
        (
            username,
            hash_password(password),
            datetime.now().isoformat(),
        ),
    )

    conn.commit()
    conn.close()

    return True, "User created successfully."


def change_user_password(username, new_password):
    if not username or not new_password:
        return False, "Username and new password are required."

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE users
        SET password_hash=?
        WHERE username=?
        """,
        (
            hash_password(new_password),
            username,
        ),
    )

    changed = cur.rowcount > 0

    conn.commit()
    conn.close()

    if not changed:
        return False, "User not found."

    return True, "Password changed successfully."


def delete_user(username):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM users WHERE username=?",
        (username,),
    )

    deleted = cur.rowcount > 0

    conn.commit()
    conn.close()

    if not deleted:
        return False, "User not found."

    return True, "User deleted."


def set_user_enabled(username, enabled):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE users
        SET enabled=?
        WHERE username=?
        """,
        (
            1 if enabled else 0,
            username,
        ),
    )

    changed = cur.rowcount > 0

    conn.commit()
    conn.close()

    if not changed:
        return False, "User not found."

    conn.commit()
    conn.close()

    return True, "User status updated."


def get_users():
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT username, enabled, created_at
        FROM users
        ORDER BY username
        """
    )

    rows = cur.fetchall()
    conn.close()

    return rows


def authenticate(username, password):

    admin_username, admin_password = get_admin_credentials()

    if (
        username.strip() == admin_username
        and password == admin_password
    ):
        return True, "admin"

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT username, password_hash, enabled
        FROM users
        WHERE username=?
        """,
        (username.strip(),),
    )

    row = cur.fetchone()
    conn.close()

    if row is None:
        return False, None

    if not row["enabled"]:
        return False, "disabled"

    if row["password_hash"] != hash_password(password):
        return False, None

    return True, "user"


# ============================================================
# EXCEL HELPERS
# ============================================================

def normalize_header(value):

    if value is None:
        return ""

    value = str(value).strip().lower()

    value = re.sub(
        r"[^a-z0-9]+",
        "",
        value
    )

    return value


def find_heading(ws, names):

    normalized = {
        normalize_header(name)
        for name in names
    }

    for col in range(1, ws.max_column + 1):

        value = ws.cell(
            row=1,
            column=col
        ).value

        if normalize_header(value) in normalized:
            return col

    return None


def find_heading_contains(ws, text):

    text_norm = normalize_header(text)

    for col in range(1, ws.max_column + 1):

        value = ws.cell(
            row=1,
            column=col
        ).value

        header_norm = normalize_header(value)

        if text_norm in header_norm:
            return col

    return None


def numeric_value(value):

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float, np.number)):

        if pd.isna(value):
            return None

        return float(value)

    text = str(value).strip()

    if not text:
        return None

    text = text.replace(",", "")

    match = re.search(
        r"[-+]?\d+(?:\.\d+)?",
        text
    )

    if not match:
        return None

    try:
        return float(match.group(0))
    except Exception:
        return None


def first_number(value):

    if value is None:
        return None

    text = str(value)

    match = re.search(
        r"[-+]?\d+(?:\.\d+)?",
        text
    )

    if not match:
        return None

    try:
        return float(match.group(0))
    except Exception:
        return None


def number_inside_parentheses(value):

    if value is None:
        return None

    text = str(value)

    match = re.search(
        r"\(\s*([-+]?\d+(?:\.\d+)?)\s*\)",
        text
    )

    if not match:
        return None

    try:
        return float(match.group(1))
    except Exception:
        return None


def make_fill(hex_color):

    hex_color = str(hex_color).replace("#", "").upper()

    if not re.fullmatch(r"[0-9A-F]{6}", hex_color):
        hex_color = DEFAULT_BLUE

    return PatternFill(
        fill_type="solid",
        fgColor=hex_color
    )


# ============================================================
# DATE DETECTION
# ============================================================

MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def extract_date_from_heading(value):

    if value is None:
        return None

    text = str(value).strip()

    # --------------------------------------------------------
    # dd Mon
    # Example: 10 Sep O2L
    # --------------------------------------------------------

    match = re.search(
        r"\b(\d{1,2})\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"\b",
        text,
        re.IGNORECASE
    )

    if match:

        day = int(match.group(1))
        month = MONTHS[
            match.group(2).lower()[:3]
        ]

        year = datetime.now().year

        try:
            return date(
                year,
                month,
                day
            )
        except Exception:
            pass

    # --------------------------------------------------------
    # dd/mm
    # Example: 10/09 O2L
    # --------------------------------------------------------

    match = re.search(
        r"\b(\d{1,2})[/-](\d{1,2})\b",
        text
    )

    if match:

        day = int(match.group(1))
        month = int(match.group(2))

        year = datetime.now().year

        try:
            return date(
                year,
                month,
                day
            )
        except Exception:
            pass

    return None


def find_recent_p2l_column(ws):

    candidates = []

    for col in range(1, ws.max_column + 1):

        heading = ws.cell(
            row=1,
            column=col
        ).value

        if heading is None:
            continue

        text = str(heading).upper()

        if "P2L" not in text and "O2L" not in text:
            continue

        dt = extract_date_from_heading(heading)

        if dt is not None:
            candidates.append(
                (
                    dt,
                    col,
                    heading
                )
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return candidates[0][1]


# ============================================================
# MASTER EXCEL PROCESSING
# ============================================================

def process_master_excel(master_bytes):

    source = io.BytesIO(master_bytes)

    source_wb = load_workbook(
        source,
        data_only=True
    )

    if "summary" not in source_wb.sheetnames:
        raise ValueError(
            "The uploaded Master Excel does not contain a 'summary' sheet."
        )

    source_ws = source_wb["summary"]

    output_wb = Workbook()

    output_ws = output_wb.active
    output_ws.title = "summary"

    # --------------------------------------------------------
    # COPY VALUES ONLY
    # --------------------------------------------------------

    for row in source_ws.iter_rows():

        for cell in row:

            output_ws.cell(
                row=cell.row,
                column=cell.column,
                value=cell.value
            )

    # --------------------------------------------------------
    # BASIC EXCEL FORMAT
    # --------------------------------------------------------

    output_ws.freeze_panes = "A2"

    if output_ws.max_row >= 1 and output_ws.max_column >= 1:

        output_ws.auto_filter.ref = (
            f"A1:{get_column_letter(output_ws.max_column)}"
            f"{output_ws.max_row}"
        )

    for cell in output_ws[1]:

        cell.font = Font(
            bold=True
        )

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

    # --------------------------------------------------------
    # COLUMN WIDTH
    # --------------------------------------------------------

    for col in range(
        1,
        output_ws.max_column + 1
    ):

        max_length = 0

        for row in range(
            1,
            min(output_ws.max_row, 1000) + 1
        ):

            value = output_ws.cell(
                row=row,
                column=col
            ).value

            if value is None:
                continue

            length = len(str(value))

            if length > max_length:
                max_length = length

        width = min(
            max(max_length + 2, 10),
            35
        )

        output_ws.column_dimensions[
            get_column_letter(col)
        ].width = width

    # --------------------------------------------------------
    # COLORS
    # --------------------------------------------------------

    blue_color = get_setting(
        "blue_color",
        DEFAULT_BLUE
    )

    green_color = get_setting(
        "green_color",
        DEFAULT_GREEN
    )

    blue_fill = make_fill(blue_color)
    green_fill = make_fill(green_color)

    # --------------------------------------------------------
    # FIND IMPORTANT COLUMNS
    # --------------------------------------------------------

    sum_i_col = find_heading(
        output_ws,
        ["Sum I"]
    )

    col_16_gt = find_heading(
        output_ws,
        ["16> C-B / Avg.4"]
    )

    col_16_lt = find_heading(
        output_ws,
        ["16< D-B / Avg.4"]
    )

    sum_o2h_col = find_heading_contains(
        output_ws,
        "Sum O2H.10"
    )

    sum_o2l_col = find_heading_contains(
        output_ws,
        "Sum O2L.10"
    )

    recent_p2l_col = find_recent_p2l_column(
        output_ws
    )

    # --------------------------------------------------------
    # SYMBOL COLUMN
    # --------------------------------------------------------

    symbol_col = find_heading(
        output_ws,
        [
            "Symbol",
            "Stock",
            "Scrip",
            "Ticker",
            "Name"
        ]
    )

    # --------------------------------------------------------
    # CONDITION COUNTER
    # --------------------------------------------------------

    condition_counts = {}

    for row in range(
        2,
        output_ws.max_row + 1
    ):

        count = 0

        # ----------------------------------------------------
        # 1. Sum I < -4.00
        # ----------------------------------------------------

        if sum_i_col:

            value = numeric_value(
                output_ws.cell(
                    row=row,
                    column=sum_i_col
                ).value
            )

            if value is not None and value < -4.00:

                output_ws.cell(
                    row=row,
                    column=sum_i_col
                ).fill = blue_fill

                output_ws.cell(
                    row=row,
                    column=1
                ).fill = blue_fill

                count += 1

        # ----------------------------------------------------
        # 2. 16> C-B / Avg.4
        #
        # Example:
        # 16>0.25, Avg.4(0.44)
        #
        # Condition:
        # parenthesized value < 0.50
        # ----------------------------------------------------

        if col_16_gt:

            cell_value = output_ws.cell(
                row=row,
                column=col_16_gt
            ).value

            avg_value = number_inside_parentheses(
                cell_value
            )

            if (
                avg_value is not None
                and avg_value < 0.50
            ):

                output_ws.cell(
                    row=row,
                    column=col_16_gt
                ).fill = blue_fill

                output_ws.cell(
                    row=row,
                    column=1
                ).fill = blue_fill

                count += 1

        # ----------------------------------------------------
        # 3. 16< D-B / Avg.4
        #
        # Example:
        # 16<-1.09, Avg.4(-1.23)
        #
        # Condition:
        # Avg.4 < first value
        # AND
        # Avg.4 < -1.00
        # ----------------------------------------------------

        if col_16_lt:

            cell_value = output_ws.cell(
                row=row,
                column=col_16_lt
            ).value

            first_val = first_number(
                cell_value
            )

            avg_val = number_inside_parentheses(
                cell_value
            )

            if (
                first_val is not None
                and avg_val is not None
                and avg_val < first_val
                and avg_val < -1.00
            ):

                output_ws.cell(
                    row=row,
                    column=col_16_lt
                ).fill = blue_fill

                output_ws.cell(
                    row=row,
                    column=1
     
