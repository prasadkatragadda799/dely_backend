# Quick Setup Guide

## Database Setup Options

### Option 1: SQLite (Recommended for Development - No Setup Required)

SQLite is the easiest option for development. No database server needed!

1. **Update `.env` file** (or create it):
   ```env
   DATABASE_URL=sqlite:///./dely.db
   ```

2. **Run migrations**:
   ```bash
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head
   ```

That's it! The database file `dely.db` will be created automatically.

### Option 2: PostgreSQL (Production Ready)

1. **Install PostgreSQL** (if not installed):
   - Windows: Download from https://www.postgresql.org/download/windows/
   - Mac: `brew install postgresql`
   - Linux: `sudo apt-get install postgresql`

2. **Create database**:
   ```sql
   CREATE DATABASE dely_db;
   CREATE USER dely_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE dely_db TO dely_user;
   ```

3. **Update `.env` file**:
   ```env
   DATABASE_URL=postgresql://dely_user:your_password@localhost:5432/dely_db
   ```

4. **Run migrations**:
   ```bash
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head
   ```

### Option 3: MySQL (Hostinger Compatible)

1. **Install MySQL** (if not installed)

2. **Create database**:
   ```sql
   CREATE DATABASE dely_db;
   CREATE USER 'dely_user'@'localhost' IDENTIFIED BY 'your_password';
   GRANT ALL PRIVILEGES ON dely_db.* TO 'dely_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

3. **Update `.env` file**:
   ```env
   DATABASE_URL=mysql+pymysql://dely_user:your_password@localhost:3306/dely_db
   ```

4. **Install MySQL driver** (if using MySQL):
   ```bash
   pip install pymysql cryptography
   ```

5. **Update `requirements.txt`** to include:
   ```
   pymysql==1.1.0
   cryptography==41.0.7
   ```

6. **Run migrations**:
   ```bash
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head
   ```

## Quick Start with SQLite

1. **Create `.env` file** in the project root:
   ```env
   DATABASE_URL=sqlite:///./dely.db
   SECRET_KEY=your-secret-key-change-this-in-production
   DEBUG=True
   ```

2. **Run migrations**:
   ```bash
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head
   ```

3. **Start the server**:
   ```bash
   python run.py
   # OR
   uvicorn app.main:app --reload
   ```

4. **Access API docs**:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Troubleshooting

### Connection Refused Error
- **SQLite**: Make sure the path is correct and you have write permissions
- **PostgreSQL**: Ensure PostgreSQL service is running
  - Windows: Check Services app
  - Mac/Linux: `sudo service postgresql start`
- **MySQL**: Ensure MySQL service is running
  - Windows: Check Services app
  - Mac/Linux: `sudo service mysql start`

### Migration Errors
- Make sure your `.env` file has the correct `DATABASE_URL`
- Check that the database exists (for PostgreSQL/MySQL)
- Verify user permissions

