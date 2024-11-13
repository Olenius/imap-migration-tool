import json
import imaplib
import email
import ssl
import base64
import socket
import sqlite3
import time
import logging
import os
from email import header
from typing import List, Dict

def setup_logger(source_email: str) -> logging.Logger:
    """Setup logger for both file and console output."""
    # Create logs directory if it doesn't exist
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Create a logger with the source email as the name
    logger = logging.getLogger(source_email)
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # File handler - use source_email in filename
    safe_email = source_email.replace('@', '_at_').replace('.', '_')
    file_handler = logging.FileHandler(os.path.join(logs_dir, f'{safe_email}.log'))
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Add both handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def decode_subject(subject):
    """Decode MIME-encoded subject to Unicode."""
    try:
        decoded_parts = header.decode_header(subject)
        decoded_subject = ''.join(
            part.decode(encoding or 'utf-8') if isinstance(part, bytes) else part
            for part, encoding in decoded_parts
        )
        return decoded_subject
    except Exception as e:
        # self.logger.warning(f"Failed to decode subject '{subject}': {str(e)}")
        return subject  # Fallback to original if decoding fails
    
def decode_folder_name(encoded_name):
    raw_encoded_name = encoded_name
    try:
        # Remove the initial '&' if present
        if encoded_name.startswith('&'):
            encoded_name = encoded_name[1:]
        
        # Replace ',' with '/'
        encoded_name = encoded_name.replace(',', '/')
        
        # Replace '-' with '='
        encoded_name = encoded_name.replace('-', '=')
        
        # Add padding if needed
        padding_length = len(encoded_name) % 4
        if padding_length:
            encoded_name += '=' * (4 - padding_length)

        # Decode base64
        decoded_bytes = base64.b64decode(encoded_name)
        
        # Convert to UTF-16 BE (Big Endian)
        decoded_text = decoded_bytes.decode('utf-16be')
        
        return decoded_text
    except Exception as e:
        # self.logger.warning(f"Error decoding: {str(e)}")
        pass

    return raw_encoded_name

class EmailConfig:
    def __init__(self, config: Dict[str, str]):
        self.source_host = config['source_host']
        self.source_email = config['source_email']
        self.source_password = config['source_password']
        self.dest_host = config['dest_host']
        self.dest_email = config['dest_email']
        self.dest_password = config['dest_password']

        self.logger = setup_logger(self.source_email)

def load_email_configs(config_file: str) -> List[EmailConfig]:
    """Load email configurations from JSON file."""
    try:
        with open(config_file, 'r') as f:
            configs = json.load(f)
            return [EmailConfig(config) for config in configs]
    except Exception as e:
        logging.error(f"Error loading config file: {str(e)}")
        raise

class IMAPMigration:
    def __init__(self, email_config: EmailConfig, db_path='migrated_uids.db'):
        self.source_host = email_config.source_host
        self.source_user = email_config.source_email
        self.source_pass = email_config.source_password
        self.dest_host = email_config.dest_host
        self.dest_user = email_config.dest_email
        self.dest_pass = email_config.dest_password
        self.db_path = db_path
        self.logger = email_config.logger
        
        # Initialize connections
        self.source = None
        self.dest = None
        
        # Initialize the database for storing migrated UIDs
        self.init_db()
        
    def init_db(self):
        """Initialize SQLite database to store migrated UIDs with dest_email."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS migrated_messages (
                    folder TEXT,
                    uid TEXT,
                    dest_email TEXT,
                    PRIMARY KEY (folder, uid, dest_email)
                )
            ''')
            conn.commit()
        
    def connect(self):
        """Establish connections to both IMAP servers."""
        try:
            context = ssl.create_default_context()
            
            self.source = imaplib.IMAP4_SSL(self.source_host, ssl_context=context, timeout=30)
            self.source.login(self.source_user, self.source_pass)
            self.logger.info("Successfully connected to source IMAP server")

            self.dest = imaplib.IMAP4_SSL(self.dest_host, ssl_context=context, timeout=30)
            self.dest.login(self.dest_user, self.dest_pass)
            self.logger.info("Successfully connected to destination IMAP server")
            
            return True
        except Exception as e:
            self.logger.error(f"Connection error: {str(e)}")
            return False
    
    def reconnect(self, folder=None):
        """Reconnect to both IMAP servers in case of an error."""
        try:
            if self.source:
                self.source.logout()
            if self.dest:
                self.dest.logout()
        except:
            pass  # Ignore logout errors
        time.sleep(1)  # Small delay before reconnecting
        
        if not self.connect():
            return False  # Return False if reconnect fails
    
        if folder:
            # Re-select the folder after reconnecting
            self.source.select(folder)
            self.logger.info(f"Re-selected folder: {decode_folder_name(folder)}")
        
        return True
    
    def get_migrated_uids(self, folder):
        """Retrieve UIDs of already migrated messages for the specified folder and dest_email."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT uid FROM migrated_messages WHERE folder = ? AND dest_email = ?",
                (folder, self.dest_user)
            )
            return {row[0] for row in cursor.fetchall()}
    
    def store_migrated_uid(self, folder, uid):
        """Store a migrated UID in the database with dest_email."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO migrated_messages (folder, uid, dest_email) VALUES (?, ?, ?)",
                (folder, uid, self.dest_user)
            )
            conn.commit()

    def get_folders(self):
        """Get list of folders from source account."""
        _, folders = self.source.list()
        return [f.decode().split('"')[-2] for f in folders]
    
    def create_folder(self, folder):
        """Create folder in destination if it doesn't exist."""
        try:
            self.dest.create(folder)
            self.logger.info(f"Created folder: {decode_folder_name(folder)}")
        except:
            self.logger.info(f"Folder already exists: {decode_folder_name(folder)}")
    
    def migrate_folder(self, folder):
        """Migrate messages from one folder to another, avoiding duplicates."""
        try:
            self.source.select(folder)
            _, messages = self.source.search(None, 'ALL')
            message_nums = messages[0].split()
            
            # Get already migrated UIDs
            migrated_uids = self.get_migrated_uids(folder)
            
            self.logger.info(f"Migrating {decode_folder_name(folder)}, total messages: {len(message_nums)}")
            
            # Select destination folder
            self.dest.select(folder)
            
            # Migrate each message
            for num in message_nums:
                _, uid_data = self.source.fetch(num, '(UID)')
                uid = uid_data[0].decode().split()[2]  # Extract UID
                
                if uid in migrated_uids:
                    self.logger.info(f"Skipping already migrated message UID {uid} in folder {decode_folder_name(folder)}")
                    continue  # Skip already migrated message
                
                # Fetch and migrate the message with retry logic
                success = self.migrate_message(num, folder, uid)
                if not success:
                    self.logger.error(f"Failed to migrate message UID {uid} in folder {decode_folder_name(folder)} after multiple attempts.")
                
            return True
        except Exception as e:
            self.logger.error(f"Error migrating folder {decode_folder_name(folder)}: {str(e)}")
            return False

    def migrate_message(self, num, folder, uid, retries=3):
        """Fetch and migrate a single message with retries."""
        for attempt in range(retries):
            try:
                _, msg_data = self.source.fetch(num, '(RFC822 FLAGS)')
                email_body = msg_data[0][1]
                flags = imaplib.ParseFlags(msg_data[0][0])

                # Append message to destination
                self.dest.append(folder, flags, None, email_body)
                
                # Store the migrated UID
                self.store_migrated_uid(folder, uid)

                msg = email.message_from_bytes(email_body)
                subject = decode_subject(msg['subject']) if msg['subject'] else "(No Subject)"
                exit

                self.logger.info(f"Successfully migrated message UID {uid} ({subject}) in folder {decode_folder_name(folder)}")
                
                return True
            except socket.error as e:
                if e.errno == 54:  # Connection reset by peer
                    self.logger.error(f"Connection reset by peer for message UID {uid}, attempt {attempt + 1}/{retries}. Reconnecting...")
                    self.reconnect(folder)  # Attempt reconnect and retry
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.logger.warning(f"Socket error for message UID {uid}: {e}")
                    return False
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1}/{retries} failed for message UID {uid}: {e}")
                
                if attempt < retries - 1:
                    if "BAD_LENGTH" in str(e) or "socket error" in str(e):
                        self.logger.info("Attempting to reconnect and retry...")
                        self.reconnect(folder)  # Reconnect in case of SSL/socket errors
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.logger.error(f"Final failure migrating message UID {uid}: {e}")
                    return False

    def migrate_all(self):
        """Migrate all folders and their contents."""
        if not self.connect():
            return False
        
        try:
            folders = self.get_folders()
            for folder in folders:
                self.create_folder(folder)
                self.migrate_folder(folder)
            
            self.logger.info("Migration completed")
        finally:
            if self.source:
                self.source.logout()
            if self.dest:
                self.dest.logout()



# Usage
if __name__ == "__main__":
    try:
        # Load configurations from JSON file
        email_configs = load_email_configs('emails.json')
        
        # Process each email configuration
        for config in email_configs:
            config.logger.info(f"Starting migration for {config.source_email} -> {config.dest_email}")
            migrator = IMAPMigration(config)
            migrator.migrate_all()
            
    except Exception as e:
        logging.error(f"Migration failed: {str(e)}")