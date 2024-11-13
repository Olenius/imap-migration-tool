import sqlite3
import sys
import logging

DATABASE = "migrated_uids.db"
TABLE = "migrated_messages"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def delete_rows(email):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Check rows before deletion
    cursor.execute(f"SELECT COUNT(*) FROM {TABLE} WHERE dest_email = ?", (email,))
    count_before = cursor.fetchone()[0]
    logger.info(f"Rows with '{email}' before deletion: {count_before}")

    if count_before > 0:
        # Execute the delete query
        cursor.execute(f"DELETE FROM {TABLE} WHERE dest_email = ?", (email,))
        conn.commit()
        logger.info(f"Rows with '{email}' deleted successfully.")

        # Check rows after deletion
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE} WHERE dest_email = ?", (email,))
        count_after = cursor.fetchone()[0]
        logger.info(f"Rows with '{email}' after deletion: {count_after}")
    else:
        logger.info(f"No rows found with '{email}' to delete.")

    # Close the connection
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.info("Usage: python delete_rows.py <email>")
    else:
        delete_rows(sys.argv[1])
