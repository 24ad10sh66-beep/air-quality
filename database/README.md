# Database

MySQL is the planned primary database. The service was found running locally
on `127.0.0.1:3306`. The application reads credentials from a local `.env`
file, which is ignored by Git.

Copy `.env.example` to `.env` and fill in local values before running:

```powershell
Copy-Item .env.example .env
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\check_database.py
```

The health check is read-only. After the database name and access account have
been verified, apply the initial schema with:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\init_database.py
```

The schema uses `CREATE TABLE IF NOT EXISTS`; it does not drop or truncate
tables. Never use a production database for development or tests.
