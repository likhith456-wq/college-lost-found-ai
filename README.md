# College Lost & Found AI

A Streamlit app for college lost-and-found reports with CLIP image suggestions, SQLite storage, account sign-in, an admin dashboard, report completion controls, and optional email notifications. The interface uses a crimson-red and green color theme.

## Run locally

Use Python 3.12. From this directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit. The first image identification downloads the CLIP model and can take a few minutes. The database and uploaded photos are stored in this directory by default.

## Deploy this standalone repository to Render with Docker

1. Push this repository to GitHub. In Render, choose **New + → Web Service** and connect the repository.
2. Select **Docker** as the runtime. Leave **Root Directory** blank so Render uses the repository root and its `Dockerfile`. If deploying from the original Replit-Clone repository instead, set **Root Directory** to `lost_found_app`.
3. Add a persistent disk mounted at `/var/data`. SQLite data, photos, and the downloaded model cache are stored there. A persistent disk requires a paid Render service; without one, the files can be lost when the service restarts or redeploys.
4. Add these environment variables in the Render service settings:

   | Variable | Required | Purpose |
   | --- | --- | --- |
   | `BOOTSTRAP_ADMIN_EMAIL` | Yes | Email address for the initial administrator |
   | `BOOTSTRAP_ADMIN_PASSWORD` | Yes | Password for the initial administrator, used when creating that account |
   | `ADMIN_EMAILS` | No | Comma-separated recipients for new-report notifications |
   | `SMTP_HOST` | No | SMTP server host; leave unset to disable email |
   | `SMTP_PORT` | No | SMTP port; defaults to `587` |
   | `SMTP_USERNAME` | No | SMTP login |
   | `SMTP_PASSWORD` | No | SMTP password or provider app password |
   | `SMTP_FROM_EMAIL` | No | Sender address; defaults to `SMTP_USERNAME` |
   | `SMTP_USE_TLS` | No | Defaults to `true` |
   | `APP_DATA_DIR` | No | Defaults to `/var/data` in Docker |
   | `HF_HOME` | No | Defaults to `/var/data/huggingface` in Docker |

   Set secrets through Render's environment settings, not in source control. The `PORT` variable is supplied by Render and is used by the Docker command.

5. Deploy. On the first startup the administrator account is created from the bootstrap variables. If the account already exists, it is promoted to admin without changing its password. Register student accounts using the sign-up page.
6. Open the public URL shown on the Render service page and test sign-in, a report submission, the **My Reports** page, and the **Mark my report as done** action. Users can complete their own reports; admins can complete any report. Completion is visible and can be filtered in Saved Reports.

For persistent SQLite storage, run only one service instance. This app is not configured for multiple replicas or concurrent shared-disk database access. Keep the admin password and SMTP credentials private, and rotate them in the provider if they are exposed.

## Optional email notifications

Email sending is disabled until `SMTP_HOST` is configured. Use SMTP credentials from an email provider (often an app password), then set `ADMIN_EMAILS` to the campus staff recipients. The app records notification attempts in its SQLite database.

## Data and accounts

Set `APP_DATA_DIR` to a writable persistent directory to keep the SQLite database and photos across deployments. New passwords are stored using PBKDF2; existing SHA-256 password hashes are upgraded when those users next sign in.
