# migrate_metadata_to_meta.py

"""
Migration script to rename 'metadata' column to 'meta' in agent_messages table
"""

import sqlite3
import os

def migrate_sqlite_database():
    """Migrate SQLite database to rename metadata column"""
    
    db_path = "autoplc.db"
    
    if not os.path.exists(db_path):
        print("No existing database found. No migration needed.")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if metadata column exists
        cursor.execute("PRAGMA table_info(agent_messages)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'metadata' in columns and 'meta' not in columns:
            print("Migrating metadata column to meta...")
            
            # Rename the column
            cursor.execute("ALTER TABLE agent_messages RENAME COLUMN metadata TO meta")
            conn.commit()
            
            print("✅ Migration completed successfully!")
        elif 'meta' in columns:
            print("Migration already completed.")
        else:
            print("No metadata column found. No migration needed.")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("Suggestion: Delete the database file and let it recreate: rm autoplc_enhanced.db")

if __name__ == "__main__":
    migrate_sqlite_database()
