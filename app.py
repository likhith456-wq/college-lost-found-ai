import hashlib
import hmac
import os
import smtplib
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image
from transformers import pipeline


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("APP_DATA_DIR", str(APP_DIR))).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "lost_found.db"
UPLOAD_DIR = DATA_DIR / "item_photos"
UPLOAD_DIR.mkdir(exist_ok=True)

st.set_page_config(
    page_title="College Lost & Found AI",
    page_icon="🔎",
    layout="wide",
)


ITEMS = {
    "smartphone": "Electronics",
    "laptop": "Electronics",
    "tablet": "Electronics",
    "headphones": "Electronics",
    "charger": "Electronics",
    "USB flash drive": "Electronics",
    "calculator": "Electronics",
    "college ID card": "Cards and documents",
    "ID card holder": "Cards and documents",
    "bank card": "Cards and documents",
    "student bus pass": "Cards and documents",
    "notebook": "Books and stationery",
    "textbook": "Books and stationery",
    "pen": "Books and stationery",
    "pencil": "Books and stationery",
    "eraser": "Books and stationery",
    "geometry box": "Books and stationery",
    "file folder": "Books and stationery",
    "backpack": "Bags",
    "handbag": "Bags",
    "lunch bag": "Bags",
    "pencil pouch": "Bags",
    "water bottle": "Daily-use items",
    "lunch box": "Daily-use items",
    "coffee mug": "Daily-use items",
    "umbrella": "Daily-use items",
    "raincoat": "Daily-use items",
    "hand sanitizer": "Daily-use items",
    "keys": "Daily-use items",
    "keychain": "Daily-use items",
    "wallet": "Daily-use items",
    "spectacles": "Daily-use items",
    "sunglasses": "Daily-use items",
    "wristwatch": "Daily-use items",
    "comb": "Daily-use items",
    "towel": "Daily-use items",
    "jacket": "Clothing and accessories",
    "sweater": "Clothing and accessories",
    "cap": "Clothing and accessories",
    "scarf": "Clothing and accessories",
    "shoes": "Clothing and accessories",
    "football": "Sports items",
    "cricket bat": "Sports items",
    "tennis racket": "Sports items",
    "other item": "Other",
}

CATEGORIES = sorted(set(ITEMS.values()))

TEXT_HINTS = {
    "smartphone": ["phone", "mobile", "smartphone", "iphone"],
    "laptop": ["laptop", "notebook computer"],
    "tablet": ["tablet", "ipad"],
    "headphones": ["headphones", "earphones", "earbuds"],
    "charger": ["charger", "charging cable", "power adapter"],
    "USB flash drive": ["usb", "pendrive", "pen drive", "flash drive"],
    "calculator": ["calculator"],
    "college ID card": ["college id", "student id", "id card"],
    "ID card holder": ["id card holder", "card holder"],
    "bank card": ["bank card", "debit card", "credit card"],
    "student bus pass": ["bus pass", "student pass"],
    "notebook": ["notebook", "notes book", "class notes"],
    "textbook": ["textbook", "text book"],
    "pen": ["pen", "ballpoint"],
    "pencil": ["pencil"],
    "eraser": ["eraser"],
    "geometry box": ["geometry box", "maths box"],
    "file folder": ["file folder", "document folder"],
    "backpack": ["backpack", "school bag", "college bag", "rucksack"],
    "handbag": ["handbag", "purse bag"],
    "lunch bag": ["lunch bag", "tiffin bag"],
    "pencil pouch": ["pencil pouch", "pencil case"],
    "water bottle": ["water bottle", "bottle", "flask"],
    "lunch box": ["lunch box", "lunchbox", "tiffin box", "food container"],
    "coffee mug": ["coffee mug", "mug"],
    "umbrella": ["umbrella"],
    "raincoat": ["raincoat", "rain coat"],
    "hand sanitizer": ["hand sanitizer", "sanitizer"],
    "keys": ["keys", "set of keys"],
    "keychain": ["keychain", "key ring"],
    "wallet": ["wallet"],
    "spectacles": ["spectacles", "eyeglasses"],
    "sunglasses": ["sunglasses", "sun glasses"],
    "wristwatch": ["wristwatch", "wrist watch"],
    "comb": ["comb"],
    "towel": ["towel"],
    "jacket": ["jacket"],
    "sweater": ["sweater"],
    "cap": ["cap", "hat"],
    "scarf": ["scarf"],
    "shoes": ["shoes", "footwear"],
    "football": ["football", "soccer ball"],
    "cricket bat": ["cricket bat"],
    "tennis racket": ["tennis racket"],
    "other item": [],
}


def apply_theme():
    st.markdown(
        """
        <style>
        :root {
            --bg: #10130f;
            --panel: #191d18;
            --panel-alt: #252c25;
            --primary: #b2183a;
            --secondary: #2e9b57;
            --accent: #dc4660;
            --text: #f4f2ed;
            --muted: #b8c0b5;
            --danger: #e04a5f;
        }
        html, body, [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #17100f, #211518 48%, #111b14);
            color: var(--text);
        }
        .stApp {
            background: transparent;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        div[data-testid="stSidebar"] {
            background: rgba(23, 18, 18, 0.96);
            border-right: 1px solid rgba(255,255,255,0.06);
        }
        [data-testid="stButton"] > button {
            border-radius: 12px;
            background: linear-gradient(135deg, var(--secondary), #58bd79);
            color: #07160c;
            font-weight: 700;
            border: none;
        }
        [data-testid="stButton"] > button:hover {
            filter: brightness(1.05);
        }
        .stTabs [role="tablist"] {
            gap: 0.5rem;
        }
        .stTabs [role="tab"] {
            background: rgba(255,255,255,0.04);
            border-radius: 8px 8px 0 0;
        }
        div[data-testid="stAlert"] {
            border-radius: 12px;
        }
        .metric-card {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 1rem;
        }
        [data-testid="stFormSubmitButton"] > button {
            background: linear-gradient(135deg, var(--primary), #dc4660);
            color: #fff;
        }
        [data-testid="stAlert"][kind="success"] {
            border-color: var(--secondary);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@contextmanager
def get_db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database():
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student',
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER,
                status TEXT NOT NULL,
                item_name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                location TEXT,
                image_path TEXT,
                created_at TEXT NOT NULL,
                is_completed INTEGER NOT NULL DEFAULT 0,
                completed_at TEXT,
                FOREIGN KEY (reporter_id) REFERENCES users(id)
            )
            """
        )
        report_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(reports)").fetchall()
        }
        if "reporter_id" not in report_columns:
            connection.execute(
                "ALTER TABLE reports ADD COLUMN reporter_id INTEGER REFERENCES users(id)"
            )
        if "is_completed" not in report_columns:
            connection.execute(
                "ALTER TABLE reports ADD COLUMN is_completed INTEGER NOT NULL DEFAULT 0"
            )
        if "completed_at" not in report_columns:
            connection.execute(
                "ALTER TABLE reports ADD COLUMN completed_at TEXT"
            )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS email_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER,
                recipient TEXT,
                subject TEXT,
                sent_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'sent'
            )
            """
        )
        bootstrap_admin()


def hash_password(password):
    salt = os.urandom(16)
    iterations = 310_000
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password, stored_hash):
    parts = stored_hash.split("$")
    if len(parts) == 4 and parts[0] == "pbkdf2_sha256":
        _, iterations, salt, expected = parts
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            int(iterations),
        )
        return hmac.compare_digest(digest.hex(), expected), False

    legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy_hash, stored_hash), True


def bootstrap_admin():
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    if not email and not password:
        return
    if not email or not password:
        raise ValueError(
            "Set both BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD."
        )

    with get_db_connection() as connection:
        user = connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if user:
            connection.execute(
            "UPDATE users SET role = 'admin' WHERE id = ?",
            (user["id"],),
            )
        else:
            connection.execute(
            """
            INSERT INTO users (name, email, password_hash, role, created_at)
            VALUES (?, ?, ?, 'admin', ?)
            """,
            (
                "Campus administrator",
                email,
                hash_password(password),
                datetime.now().isoformat(timespec="seconds"),
            ),
            )


def update_password_hash(user_id, password_hash):
    with get_db_connection() as connection:
        connection.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (password_hash, user_id),
        )


def get_user_by_email(email):
    with get_db_connection() as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
    return dict(user) if user else None


def create_user(name, email, password, role="student"):
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (name, email, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name.strip(),
                email.strip().lower(),
                hash_password(password),
                role,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )


def get_all_reports():
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT r.*, u.name AS reporter_name, u.email AS reporter_email
            FROM reports r
            LEFT JOIN users u ON u.id = r.reporter_id
            ORDER BY r.id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def save_report(user_id, status, item_name, category, description, location, image_path):
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO reports (
                reporter_id, status, item_name, category, description,
                location, image_path, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                status,
                item_name,
                category,
                description,
                location,
                image_path,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        return cursor.lastrowid


def mark_report_completed(report_id, user):
    with get_db_connection() as connection:
        if user["role"] == "admin":
            result = connection.execute(
                """
                UPDATE reports
                SET is_completed = 1, completed_at = ?
                WHERE id = ? AND is_completed = 0
                """,
                (datetime.now().isoformat(timespec="seconds"), report_id),
            )
        else:
            result = connection.execute(
                """
                UPDATE reports
                SET is_completed = 1, completed_at = ?
                WHERE id = ? AND reporter_id = ? AND is_completed = 0
                """,
                (
                    datetime.now().isoformat(timespec="seconds"),
                    report_id,
                    user["id"],
                ),
            )
    return result.rowcount > 0


def send_email(subject, body, recipients):
    if not recipients:
        return False

    host = os.getenv("SMTP_HOST")
    if not host:
        return False

    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM_EMAIL", username)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender or "college-lost-found@localhost"
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port) as server:
            if os.getenv("SMTP_USE_TLS", "true").lower() == "true":
                server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(msg)
        return True
    except Exception:
        return False


def log_email(report_id, recipient, subject, status):
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO email_log (report_id, recipient, subject, sent_at, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                report_id,
                recipient,
                subject,
                datetime.now().isoformat(timespec="seconds"),
                status,
            ),
        )


def notify_admins_and_reporter(report_id, item_name, user):
    admin_emails = [
        email.strip()
        for email in os.getenv("ADMIN_EMAILS", "").split(",")
        if email.strip()
    ]

    if not user:
        return

    reporter_subject = "Your report has been received"
    reporter_body = (
        f"Hello {user['name']},\n\n"
        f"Your {item_name} report was successfully saved in the College Lost & Found system.\n"
        "We will notify you if a matching claim is found.\n\n"
        "Thank you."
    )
    reporter_ok = send_email(reporter_subject, reporter_body, [user["email"]])
    log_email(report_id, user["email"], reporter_subject, "sent" if reporter_ok else "failed")

    if admin_emails:
        admin_subject = "New lost & found item reported"
        admin_body = (
            f"A new report has been submitted by {user['name']} ({user['email']}).\n\n"
            f"Item: {item_name}\n"
            "Please review the dashboard for details."
        )
        admin_ok = send_email(admin_subject, admin_body, admin_emails)
        for email in admin_emails:
            log_email(report_id, email, admin_subject, "sent" if admin_ok else "failed")


def identify_from_text(description):
    text = description.lower()
    for item, keywords in TEXT_HINTS.items():
        for keyword in keywords:
            if keyword in text:
                return item
    return None


@st.cache_resource
def load_model():
    return pipeline(
        task="zero-shot-image-classification",
        model="openai/clip-vit-base-patch32",
        device=-1,
    )


def render_login_page():
    st.title("🔐 College Lost & Found AI")
    st.caption("Sign in to report items, track submissions, and manage campus alerts.")

    tab1, tab2 = st.tabs(["Login", "Sign up"])

    with tab1:
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

        if submitted:
            if not email or not password:
                st.warning("Please enter both email and password.")
            else:
                user = get_user_by_email(email)
                if user:
                    password_valid, needs_upgrade = verify_password(
                        password,
                        user["password_hash"],
                    )
                else:
                    password_valid, needs_upgrade = False, False

                if password_valid:
                    if needs_upgrade:
                        user["password_hash"] = hash_password(password)
                        update_password_hash(user["id"], user["password_hash"])
                    st.session_state["user"] = user
                    st.session_state["auth_message"] = "Logged in successfully."
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

    with tab2:
        with st.form("signup_form", clear_on_submit=False):
            name = st.text_input("Full name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create account")

        if submitted:
            if not name or not email or not password:
                st.warning("Please fill in all fields.")
            elif password != confirm_password:
                st.warning("Passwords do not match.")
            elif get_user_by_email(email):
                st.error("This email is already registered.")
            else:
                create_user(name, email, password, role="student")
                new_user = get_user_by_email(email)
                st.session_state["user"] = new_user
                st.success("Account created successfully.")
                st.rerun()


def render_dashboard(user):
    stats = get_all_reports()
    total = len(stats)
    lost = sum(1 for item in stats if item["status"] == "Lost an Item")
    found = sum(1 for item in stats if item["status"] == "Found an Item")
    completed = sum(1 for item in stats if item["is_completed"])

    st.title("📊 Dashboard")
    st.caption(f"Welcome back, {user['name']}.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total reports", total)
    col2.metric("Lost", lost)
    col3.metric("Found", found)
    col4.metric("Completed", completed)

    recent = stats[:5]
    if recent:
        st.subheader("Recent reports")
        for item in recent:
            with st.container(border=True):
                st.markdown(f"### {item['item_name']}")
                st.write(f"**Status:** {item['status']}")
                st.write(
                    "**Resolution:** "
                    f"{'Completed' if item['is_completed'] else 'Open'}"
                )
                st.write(f"**Category:** {item['category']}")
                st.write(f"**Location:** {item['location'] or 'Not specified'}")
                st.caption(f"Reported by: {item.get('reporter_name') or 'Unknown'}")
    else:
        st.info("No reports yet. Submit the first item to get started.")


def render_report_page(user):
    st.title("🧾 Report a lost or found item")

    status = st.radio(
        "What do you want to report?",
        ["Lost an Item", "Found an Item"],
        horizontal=True,
    )

    description = st.text_area(
        "Item description",
        placeholder="Example: Blue water bottle with a black cap, lost near the library.",
    )

    uploaded_photo = st.file_uploader(
        "Upload item photo",
        type=["jpg", "jpeg", "png", "webp"],
    )
    if uploaded_photo:
        st.image(uploaded_photo, width=280)

    location = st.text_input(
        "Where was it lost or found?",
        placeholder="Library, Block B, Canteen, Hostel, Admin office",
    )

    if st.button("Identify and save report", type="primary"):
        if not description.strip():
            st.error("Please enter an item description.")
        elif uploaded_photo is None:
            st.error("Please upload a photo.")
        elif not location.strip():
            st.error("Please enter the location.")
        else:
            try:
                with st.spinner("AI is identifying the item..."):
                    image = Image.open(uploaded_photo).convert("RGB")
                    classifier = load_model()
                    results = classifier(image, candidate_labels=list(ITEMS.keys()))
                    image_guess = results[0]["label"]
                    text_guess = identify_from_text(description)
                    suggested_item = text_guess or image_guess

                    st.session_state["image_guess"] = image_guess
                    st.session_state["text_guess"] = text_guess
                    st.session_state["suggested_item"] = suggested_item
                    st.session_state["image_results"] = results
                    st.session_state["photo_bytes"] = uploaded_photo.getvalue()
                    st.session_state["report_status"] = status
                    st.session_state["report_description"] = description
                    st.session_state["report_location"] = location
            except Exception:
                st.error("Could not identify the item. Please try again.")

    if "suggested_item" in st.session_state:
        st.subheader("AI identification result")
        st.write(f"Image prediction: {st.session_state['image_guess']}")
        if st.session_state.get("text_guess"):
            st.write(f"Description suggestion: {st.session_state['text_guess']}")

        item_options = list(ITEMS.keys())
        with st.form("confirm_report_form"):
            final_item = st.selectbox(
                "Confirm or change the item name",
                item_options,
                index=item_options.index(st.session_state["suggested_item"]),
            )
            final_category = st.selectbox(
                "Confirm or change the category",
                CATEGORIES,
                index=CATEGORIES.index(ITEMS[final_item]),
            )
            save_clicked = st.form_submit_button("Save report")

        if save_clicked:
            import io

            photo_name = f"{uuid.uuid4().hex}.jpg"
            photo_path = UPLOAD_DIR / photo_name
            image = Image.open(io.BytesIO(st.session_state["photo_bytes"])).convert("RGB")
            image.save(photo_path, format="JPEG")

            report_id = save_report(
                user_id=user["id"],
                status=st.session_state["report_status"],
                item_name=final_item,
                category=final_category,
                description=st.session_state["report_description"],
                location=st.session_state["report_location"],
                image_path=str(photo_path),
            )

            notify_admins_and_reporter(report_id, final_item, user)

            st.success("Your item report was saved successfully.")
            for key in [
                "image_guess",
                "text_guess",
                "suggested_item",
                "image_results",
                "photo_bytes",
                "report_status",
                "report_description",
                "report_location",
            ]:
                st.session_state.pop(key, None)


def render_saved_reports(user, own_only=False):
    st.title("📋 My reports" if own_only else "📋 Saved reports")

    reports = pd.DataFrame(get_all_reports())
    if reports.empty:
        st.info("No reports are available yet.")
        return

    if own_only:
        reports = reports[reports["reporter_id"] == user["id"]].copy()
        if reports.empty:
            st.info("You have not submitted any reports yet.")
            return

    reports["status"] = reports["status"].replace({
        "Lost": "Lost an Item",
        "Found": "Found an Item",
    })

    status_filter = st.radio("Show reports", ["All", "Lost", "Found"], horizontal=True)
    filtered = reports.copy()

    if status_filter == "Lost":
        filtered = filtered[filtered["status"] == "Lost an Item"]
    elif status_filter == "Found":
        filtered = filtered[filtered["status"] == "Found an Item"]

    resolution_filter = st.radio(
        "Resolution",
        ["All", "Open", "Completed"],
        horizontal=True,
    )
    if resolution_filter == "Open":
        filtered = filtered[filtered["is_completed"] == 0]
    elif resolution_filter == "Completed":
        filtered = filtered[filtered["is_completed"] == 1]

    available_categories = sorted(filtered["category"].dropna().unique().tolist())
    category_filter = st.selectbox("Filter by category", ["All categories"] + available_categories)
    if category_filter != "All categories":
        filtered = filtered[filtered["category"] == category_filter]

    search_text = st.text_input("Search items", placeholder="Search by item, location, description, or category")
    if search_text.strip():
        columns = ["item_name", "category", "description", "location", "reporter_name"]
        matches = filtered[columns].fillna("").apply(
            lambda col: col.str.contains(search_text.strip(), case=False, regex=False)
        ).any(axis=1)
        filtered = filtered[matches]

    st.subheader(f"Results: {len(filtered)}")
    for _, row in filtered.iterrows():
        with st.container(border=True):
            st.markdown(f"### {row['item_name']}")
            if row["status"] == "Lost an Item":
                st.warning("🔍 Lost item")
            else:
                st.success("📦 Found item")
            st.write(f"**Category:** {row['category']}")
            st.write(f"**Description:** {row.get('description') or 'No description'}")
            st.write(f"**Location:** {row.get('location') or 'Not specified'}")
            if row["is_completed"]:
                st.success("✅ Item returned / report completed")
                if row.get("completed_at"):
                    st.caption(f"Completed on: {row['completed_at']}")
            else:
                st.info("Open report")
                is_report_owner = row.get("reporter_id") == user["id"]
                can_complete = user["role"] == "admin" or is_report_owner
                if can_complete and st.button(
                    "Mark my report as done" if is_report_owner else "Mark as completed",
                    key=f"complete_report_{row['id']}",
                ):
                    if mark_report_completed(int(row["id"]), user):
                        st.success("Report marked as completed.")
                        st.rerun()
                    st.warning("This report was already completed or is no longer available.")
            st.caption(f"Reported by: {row.get('reporter_name') or 'Unknown'} • {row.get('created_at') or 'Unknown time'}")


def render_admin_page(user):
    if user["role"] != "admin":
        st.warning("You do not have admin access.")
        return

    st.title("🛡️ Admin dashboard")
    reports = get_all_reports()
    if not reports:
        st.info("No reports available yet.")
        return

    df = pd.DataFrame(reports)
    st.dataframe(
        df[
            [
                "id",
                "status",
                "is_completed",
                "item_name",
                "category",
                "location",
                "reporter_name",
                "created_at",
            ]
        ],
        use_container_width=True,
    )

    status_counts = df["status"].value_counts().to_dict()
    st.subheader("Summary")
    col1, col2 = st.columns(2)
    col1.metric("Lost items", status_counts.get("Lost an Item", 0))
    col2.metric("Found items", status_counts.get("Found an Item", 0))
    st.metric("Completed reports", int(df["is_completed"].sum()))


def main():
    apply_theme()
    initialize_database()

    if "user" not in st.session_state:
        render_login_page()
        return

    user = st.session_state["user"]

    st.sidebar.title("Navigation")
    st.sidebar.write(f"👤 {user['name']}")
    st.sidebar.write(f"{user['email']}")

    pages = ["Dashboard", "Report Item", "My Reports", "Saved Reports"]
    if user["role"] == "admin":
        pages.append("Admin")

    selected_page = st.sidebar.radio("Select page", pages)

    if st.sidebar.button("Logout"):
        st.session_state.pop("user", None)
        st.rerun()

    if selected_page == "Dashboard":
        render_dashboard(user)
    elif selected_page == "Report Item":
        render_report_page(user)
    elif selected_page == "Saved Reports":
        render_saved_reports(user)
    elif selected_page == "My Reports":
        render_saved_reports(user, own_only=True)
    elif selected_page == "Admin":
        render_admin_page(user)


if __name__ == "__main__":
    main()
