# python-oscar-cli

A simple command-line interface (CLI) client for AOL Instant Messenger (AIM) using the OSCAR protocol. This tool allows you to connect to an AIM-compatible server, send and receive messages, set away status with auto-replies, and log chats.

## Features

- Connect to an AIM server with username and password.
- Send messages in a simple format: `recipient:message`.
- Receive real-time messages with timestamped output.
- Set away status with custom message: `/away <message>`.
- Auto-reply to incoming messages when away, with a 5-minute cooldown per buddy to avoid spamming.
- Disable away status: `/back`.
- Quit the session: `/quit`.
- Chat logging to `chat_log.txt` with timestamps.
- Colorful console output using the `rich` library.
- Automatic reset of away status when sending manual messages.

## Requirements

- Python 3.12+
- Dependencies:
  - `aimpyfly`: For OSCAR protocol handling.
  - `rich`: For enhanced console output.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/MyMel2001/python-oscar-cli.git
cd python-oscar-cli
```
2. Install dependencies using `requirements.txt`:
```bash
pip install -r requirements.txt
```

## Usage

Run the script with the required arguments:
```oscar-client.py [-h] --server SERVER [--port PORT] --username USERNAME --password PASSWORD```

- `--server`: The AIM server address (required).
- `--port`: The server port (default: 5190).
- `--username`: Your AIM username (required).
- `--password`: Your AIM password (required).

### Example
```./oscar_client.py --server aim.example.com --username myuser --password mypass```


Once connected, you'll see a prompt `>`. Use it to:

- Send a message: `buddyname:Hello, how are you?`
- Set away: `/away Out for lunch`
- Return: `/back`
- Quit: `/quit`

Incoming messages are displayed in real-time with timestamps. Chats are logged to `chat_log.txt`.

## Notes

- The auto-reply feature only triggers if you're away and hasn't replied to that buddy within the last 5 minutes.
- Logs are appended to `chat_log.txt` in the current directory.
- Error handling is basic; connection failures are displayed in the console.
- This is a stateful CLI session—use Ctrl+C to exit if needed.

## Contributing

Contributions are welcome! Feel free to open issues or pull requests on [GitHub](https://github.com/MyMel2001/python-oscar-cli).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
