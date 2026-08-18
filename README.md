# Pokemon Go Tools

A Streamlit app for tracking your Pokemon GO storage, IVs, and battle recommendations.

You create an account, add Pokemon from your inventory, and browse them on a dashboard.

https://pogo-tools.streamlit.app/

---

## What you need

Install these **before** you clone the repo:

| Tool | Why | Where |
|---|---|---|
| **Python 3.10+** | Runs the app | [python.org](https://www.python.org/downloads/) — tick **Add Python to PATH** on Windows |
| **PostgreSQL 15+** | Required if you pick **local** (see below) | [postgresql.org/download](https://www.postgresql.org/download/) |
| **Git** | Downloads the project | [git-scm.com](https://git-scm.com/) |
| **[Neon](https://neon.tech)** account | Required if you pick **Neon** (see below) | Free tier is enough |

Check that Python works:

```powershell
python --version
```

You should see `Python 3.10` or newer.

---

## Pick local or Neon

The app talks to **one** Postgres database at a time. Choose before you set up `.env`.

| | **Local Postgres** | **Neon (cloud)** |
|---|---|---|
| Speed | Fast, little to no lag | Noticeable latency (every click waits on the network) |
| Devices | Data stays on this computer only | Same data on any device that uses this Neon URL |
| You need | PostgreSQL installed on this machine | A Neon project and its connection string |

**Use local** if you only run the app on one PC and want snappy add/edit/dashboard interactions.

**Use Neon** if you want the same account and storage on a laptop, another PC, or Streamlit Cloud. Expect slower page loads.

You can keep *both* URLs in `.env` and copy data between them later with the sync scripts. The running app still uses only whichever line is uncommented in `tools/db.py`.

---

## 1. Clone the project

```powershell
git clone https://github.com/antondamar/pogo-tools.git
cd pogo-tools
```

---

## 2. Create a virtual environment and install packages

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` installs Streamlit, Postgres driver (`psycopg2-binary`), password hashing (`bcrypt`), env loading (`python-dotenv`), and login cookies.

If PowerShell blocks the activate script, run this once, then try again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## 3. Install Postgres (local only)

Skip this step if you are using **Neon only**.

Install PostgreSQL and remember the password you set for the `postgres` user. Make sure the Postgres service is running.

You do **not** need to create tables by hand. The next steps create a `.env` file, then `scripts/init_db.py` creates the `pokemon` database (if it is missing), the schema, and the Pokemon reference data.

---

## 4. Create a `.env` file

In the **project root** (same folder as `app.py`), create a file named `.env`. It is gitignored — never commit it.

```env
LOCAL_DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/pokemon
NEON_DATABASE_URL=postgresql://USER:PASSWORD@HOST.neon.tech/neondb?sslmode=require
AUTH_SECRET=replace-with-a-long-random-string
AUTH_COOKIE_DAYS=14
```

**Where the Neon URL goes:** paste the connection string from the [Neon dashboard](https://console.neon.tech) into `NEON_DATABASE_URL` in this `.env` file. Use the URI that includes `sslmode=require`. Do not put it in `app.py`. Putting it only in `.env` is not enough — you still have to select Neon in `tools/db.py` (next paragraph).

Replace:

- `YOUR_PASSWORD` with your local Postgres password (omit `LOCAL_DATABASE_URL` if you are Neon-only)
- `AUTH_SECRET` with a random string. Generate one with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

`AUTH_COOKIE_DAYS` is optional. It defaults to 14 if you omit it.

### Tell the app which database to use

Open `tools/db.py`. Leave **exactly one** of these lines uncommented:

Local (fast, this computer only):

```python
DB_URL = os.getenv("LOCAL_DATABASE_URL")
# DB_URL = os.getenv("NEON_DATABASE_URL")
```

Neon (works across devices, slower):

```python
# DB_URL = os.getenv("LOCAL_DATABASE_URL")
DB_URL = os.getenv("NEON_DATABASE_URL")
```

Restart Streamlit after you change this (`Ctrl+C`, then `streamlit run app.py` again).

---

## 5. Initialize the database

This creates the tables and loads species / moves so you can add Pokemon right away. It does **not** copy anyone else's accounts or inventory.

Local:

```powershell
python scripts/init_db.py
```

Neon:

```powershell
python scripts/init_db.py --neon
```

You should see species, moves, and species_moves row counts, then `Done`. Safe to run again: if species data is already there, it skips the seed.

---

## 6. Run the app

From the project root, with the venv still activated:

```powershell
streamlit run app.py
```

The terminal prints a local URL, usually [http://localhost:8501](http://localhost:8501). Open it in a browser.

---

## Using the app

1. Open **Create Account** and register with an email, username, and password.
2. Log in. You stay signed in for `AUTH_COOKIE_DAYS` (cookie-based).
3. On the **Dashboard**, add Pokemon from your storage (species, IVs, CP, moves, shiny/shadow/mega).
4. Open a Pokemon for details, mega preview, or battle recommendations.
5. Log out from the sidebar.

---

## Optional: copy between local and Neon

Only if you already use both databases and want to replace one with the other. Each command **overwrites** the destination.

```powershell
python db_sync_scripts/sync_neon_to_local.py
python db_sync_scripts/sync_local_to_neon.py
```

Type `YES` to continue. You need `pg_dump` / `pg_restore` (they come with PostgreSQL).

---

## Project layout

```
pogo-tools/
  app.py                 # start here: streamlit run app.py
  requirements.txt
  .env                   # you create this; not in git
  pages/                 # screens (login, register, dashboard)
  tools/                 # database, auth, inventory, battle math
  assets/                # images and type icons
  sql/                   # schema + species/moves seed
  scripts/init_db.py     # first-time database setup
  db_sync_scripts/       # optional local <-> Neon copy
```

---

## Troubleshooting

**`AUTH_SECRET is missing`**  
Add `AUTH_SECRET` to `.env` and restart Streamlit (`Ctrl+C`, then `streamlit run app.py` again).

**`Set LOCAL_DATABASE_URL` / connection refused**  
Postgres is not running, the password is wrong, or `.env` is missing. Confirm Postgres is started, then run `python scripts/init_db.py` again.

**`init_db.py` failed / missing seed files**  
Run it from the project root (`python scripts/init_db.py`), not from inside `scripts/`.

**Could not find `pg_dump`**  
Only needed for the optional Neon <-> local copy. Install PostgreSQL and add its `bin` folder to PATH, for example `C:\Program Files\PostgreSQL\17\bin`.

**Module not found (`pages`, `tools`)**  
Run `streamlit run app.py` from the project root, not from inside `pages/` or `tools/`.

**PowerShell: `Activate.ps1` cannot be loaded**  
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
