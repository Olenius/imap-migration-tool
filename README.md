# IMAP Email Migration Tool

A robust Python tool for migrating emails between IMAP servers with support for multiple email accounts, folder structure preservation, and progress tracking. The tool handles connection issues gracefully, supports resuming interrupted migrations, and provides detailed logging for each migration process.

## Features

- 📧 Migrate multiple email accounts in sequence
- 📁 Preserve folder structure and message flags
- ▶️ Resume capability (tracks migrated messages)
- 🔄 Automatic reconnection on connection issues
- 📝 Detailed per-account logging
- 🔒 SSL/TLS support for secure connections
- 🗃️ SQLite database for migration progress tracking
- 💪 Robust error handling and retries
- 🌐 Support for non-ASCII folder names and subjects

## Prerequisites

- Python 3.6 or higher
- SQLite3
- Internet connection
- IMAP access enabled on both source and destination email servers

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Olenius/imap-migration-tool.git
cd imap-migration-tool
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

## Configuration

Create a `emails.json` file in the project directory with your email configurations:

```json
[
    {
        "source_host": "imap.source-server.com",
        "source_email": "user@source-server.com",
        "source_password": "your-source-password",
        "dest_host": "imap.destination-server.com",
        "dest_email": "user@destination-server.com",
        "dest_password": "your-destination-password"
    },
    {
        // Add more email configurations as needed
    }
]
```

## Usage

1. Set up your email configurations in `emails.json`
2. Run the migration script:
```bash
python imap_migration.py
```

The script will:
- Process each email configuration sequentially
- Create necessary folders on the destination server
- Migrate messages while preserving their flags
- Skip already migrated messages
- Log progress to both console and files

## Logging

Logs are stored in the `logs` directory, with separate log files for each source email address:
- Console output shows progress for all migrations
- Individual log files (e.g., `user_at_domain_com.log`) contain detailed information for each account
- Logs include timestamps, success/failure status, and error details

## Error Handling

The tool includes robust error handling for common IMAP issues:
- Connection timeouts
- SSL/TLS errors
- Server disconnections
- Authentication failures
- Message size limits
- Folder permission issues

## Database Structure

The tool uses SQLite to track migrated messages:
```sql
CREATE TABLE migrated_messages (
    folder TEXT,
    uid TEXT,
    dest_email TEXT,
    PRIMARY KEY (folder, uid, dest_email)
);
```

## Common Issues & Solutions

### Connection Timeouts
- The tool automatically retries with exponential backoff
- Adjust the `timeout` parameter in the IMAP connection if needed

### Memory Issues with Large Mailboxes
- Messages are processed one at a time
- Progress is saved after each successful migration
- Can be stopped and resumed safely

### SSL/TLS Errors
- Verify server certificates are valid
- Check if the server requires specific SSL/TLS versions

## Security Considerations

- Credentials are stored in plaintext in `emails.json` - secure this file appropriately
- Use app-specific passwords when available (especially for Gmail)
- Consider using environment variables for sensitive credentials
- Ensure proper file permissions on configuration and log files

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to all contributors who have helped with testing and improvements
- Built using Python's `imaplib` and standard library modules
- Inspired by the need for reliable email migration tools

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.

## Author

Olenius
- GitHub: [@Olenius](https://github.com/Olenius)
- Email: infawn@gmail.com

## Disclaimer

This tool is provided as-is with no warranties. Always test with a small batch of emails first and ensure you have backups before performing large migrations.
