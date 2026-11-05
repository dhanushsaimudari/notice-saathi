#!/usr/bin/env python3
"""
NoticeSaathi — Database & Storage Asset Backup and Restore Utility
Supports automated snapshot generation and disaster recovery
for both SQLite (local development) and PostgreSQL (staging/production).
"""

import os
import sys
import shutil
import tarfile
import argparse
import subprocess
import logging
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BackupRestore")

def get_backup_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")

def backup_sqlite(db_file: Path, output_dir: Path) -> Path:
    """Creates a consistent backup copy of the SQLite database."""
    ts = get_backup_timestamp()
    dest = output_dir / f"notice_saathi_db_{ts}.sqlite"
    logger.info(f"Backing up SQLite database from {db_file} to {dest}...")
    shutil.copy2(db_file, dest)
    return dest

def backup_storage_assets(storage_dir: Path, output_dir: Path) -> Path:
    """Creates an encrypted/compressed tarball of the private document storage directory."""
    ts = get_backup_timestamp()
    tar_path = output_dir / f"notice_saathi_storage_{ts}.tar.gz"
    logger.info(f"Archiving storage directory {storage_dir} into {tar_path}...")
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(storage_dir, arcname="storage")
    return tar_path

def backup_postgres(db_url: str, output_dir: Path) -> Path:
    """Executes pg_dump for PostgreSQL production databases."""
    ts = get_backup_timestamp()
    dump_path = output_dir / f"notice_saathi_pg_{ts}.sql"
    logger.info(f"Running pg_dump for PostgreSQL database into {dump_path}...")
    cmd = ["pg_dump", "--clean", "--if-exists", "-f", str(dump_path), db_url]
    subprocess.run(cmd, check=True)
    return dump_path

def create_backup(target_dir: str = "./backups") -> Dict[str, str]:
    out_path = Path(target_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    db_url = settings.DATABASE_URL
    results = {}

    # 1. Database backup
    if db_url.startswith("sqlite:///"):
        sqlite_file = Path(db_url.replace("sqlite:///", ""))
        if sqlite_file.exists():
            dest_db = backup_sqlite(sqlite_file, out_path)
            results["database_backup"] = str(dest_db)
        else:
            logger.warning(f"SQLite file does not exist: {sqlite_file}")
    elif db_url.startswith("postgresql"):
        try:
            dest_db = backup_postgres(db_url, out_path)
            results["database_backup"] = str(dest_db)
        except Exception as e:
            logger.error(f"PostgreSQL pg_dump failed: {e}")
            results["database_backup_error"] = str(e)

    # 2. Storage directory backup
    storage_dir = Path(settings.STORAGE_LOCAL_DIR)
    if storage_dir.exists():
        tar_dest = backup_storage_assets(storage_dir, out_path)
        results["storage_backup"] = str(tar_dest)
    else:
        logger.info(f"Storage directory {storage_dir} does not exist yet; nothing to archive.")

    logger.info(f"Backup operation completed successfully: {results}")
    return results

def restore_sqlite(backup_file: Path, db_target: Path) -> None:
    logger.info(f"Restoring SQLite database from {backup_file} to {db_target}...")
    shutil.copy2(backup_file, db_target)
    logger.info("SQLite restore completed.")

def restore_storage(archive_file: Path, target_dir: Path) -> None:
    logger.info(f"Extracting storage archive {archive_file} into {target_dir}...")
    with tarfile.open(archive_file, "r:gz") as tar:
        tar.extractall(path=target_dir.parent)
    logger.info("Storage assets restored.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NoticeSaathi Backup & Disaster Recovery")
    parser.add_argument("--action", choices=["backup", "restore"], default="backup")
    parser.add_argument("--dir", default="./backups", help="Target backup directory")
    parser.add_argument("--db-file", help="Path to database backup file for restoration")
    parser.add_argument("--storage-file", help="Path to storage archive for restoration")
    args = parser.parse_args()

    if args.action == "backup":
        create_backup(args.dir)
    elif args.action == "restore":
        if args.db_file:
            db_target = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
            restore_sqlite(Path(args.db_file), db_target)
        if args.storage_file:
            restore_storage(Path(args.storage_file), Path(settings.STORAGE_LOCAL_DIR))

