"""
src/utils/db.py
SQLite database wrapper for local storage of telemetry and AI interpretations.
"""
import sqlite3
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "aegis_local.db")

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Telemetry table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_str TEXT,
                data JSON
            )
        ''')
        
        # Interpretations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interpretations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_str TEXT,
                specialty TEXT,
                findings TEXT,
                severity TEXT,
                severity_score REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("SQLite database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize SQLite db: {e}")

def insert_telemetry(snapshot: dict):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        now_str = datetime.now().isoformat()
        cursor.execute(
            'INSERT INTO telemetry (timestamp_str, data) VALUES (?, ?)',
            (now_str, json.dumps(snapshot))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to insert telemetry: {e}")

def get_latest_telemetry() -> dict:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT data FROM telemetry ORDER BY id DESC LIMIT 1'
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
    except Exception as e:
        logger.error(f"Failed to fetch latest telemetry: {e}")
    return {}

def insert_interpretation(specialty: str, findings: str, severity: str, severity_score: float):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        now_str = datetime.now().isoformat()
        cursor.execute(
            'INSERT INTO interpretations (timestamp_str, specialty, findings, severity, severity_score) VALUES (?, ?, ?, ?, ?)',
            (now_str, specialty, findings, severity, severity_score)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to insert interpretation: {e}")

def get_latest_interpretations() -> Dict[str, Any]:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT specialty, findings, severity, severity_score, timestamp_str
            FROM interpretations
            WHERE id IN (
                SELECT MAX(id)
                FROM interpretations
                GROUP BY specialty
            )
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        results = {}
        for row in rows:
            spec, finds, sev, score, tstamp = row
            results[spec] = {
                "interpretation": finds,
                "severity": sev,
                "severity_score": score,
                "generated_at": tstamp
            }
        return results
    except Exception as e:
        logger.error(f"Failed to fetch interpretations: {e}")
    return {}
