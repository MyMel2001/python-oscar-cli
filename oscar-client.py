#!/usr/bin/env python3
import asyncio
import argparse
import logging
import sys
import datetime
import struct
from rich.console import Console

# Silence standard logs to protect the UI
logging.getLogger("aimpyfly").setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.CRITICAL)

console = Console()
chat_log_file = "chat_log.txt"

def log_chat(text):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(chat_log_file, "a") as f:
        f.write(f"[{timestamp}] {text}\n")

async def message_received(sender, message):
    log_chat(f"{sender}: {message}")
    sys.stdout.write(f"\r\033[K[bold green]{sender}:[/] {message}\n> ")
    sys.stdout.flush()

# --- CUSTOM LOW-LEVEL OSCAR LOGIC ---
async def set_away_status(client, message=""):
    """
    Manually constructs a SNAC(01, 1E) to set Away status.
    Type 0x0004 TLV is used for the Away Message.
    """
    if not client.writer:
        return

    # 1. Create the Away Message TLV (Type 0x04)
    # If message is empty, we are essentially "coming back"
    msg_bytes = message.encode('utf-8')
    # Format: Type (2 bytes), Length (2 bytes), Value (N bytes)
    tlv_away = struct.pack('!HH', 0x0004, len(msg_bytes)) + msg_bytes
    
    # 2. SNAC Header: Family (01), Subtype (1E), Flags (0000), Request ID (00000000)
    snac_header = struct.pack('!HHHI', 0x0001, 0x001E, 0x0000, 0x00000000)
    
    payload = snac_header + tlv_away
    
    # 3. FLAP Header: 0x2a, Channel 2, Sequence, Length
    # We borrow the client's sequence incrementer
    client.seq_num = (client.seq_num + 1) % 65535
    flap_header = struct.pack('!BBHH', 0x2a, 0x02, client.seq_num, len(payload))
    
    client.writer.write(flap_header + payload)
    await client.writer.drain()

async def get_input():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sys.stdin.readline)

async def main(args):
    from aimpyfly import aim_client
    
    client = aim_client.AIMClient(
        server=args.server, port=args.port,
        username=args.username, password=args.password,
        loglevel=logging.CRITICAL
    )
    client.set_message_callback(message_received)

    try:
        console.print(f"[yellow]Connecting to {args.server}...[/]")
        await client.connect()
        console.print("[bold blue]Connected![/] Commands: [bold yellow]/away <msg>[/], [bold yellow]/back[/], [bold yellow]/buddies[/]")
    except Exception as e:
        console.print(f"[bold red]Connection failed: {e}[/]")
        return

    processing_task = asyncio.create_task(client.process_incoming_packets())

    while not processing_task.done():
        try:
            sys.stdout.write("> ")
            sys.stdout.flush()
            
            line = await get_input()
            if not line: break
            cmd = line.strip()
            if not cmd: continue

            if cmd.lower() == "/quit":
                break
            
            elif cmd.lower() == "/buddies":
                # Fallback to internal library buddy tracking if available
                buddies = getattr(client, 'buddies', [])
                if not buddies:
                    console.print("[italic]No buddies in list yet.[/]")
                else:
                    console.print(f"[bold green]Buddies:[/bold green] {', '.join(buddies)}")

            elif cmd.lower().startswith("/away "):
                away_msg = cmd[6:].strip()
                await set_away_status(client, away_msg)
                console.print(f"[bold yellow]Away message set:[/] {away_msg}")

            elif cmd.lower() == "/back":
                await set_away_status(client, "") # Clear away message
                console.print("[bold green]Welcome back! Status set to online.[/]")

            elif ":" in cmd:
                recipient, message = cmd.split(":", 1)
                await client.send_message(recipient.strip(), message.strip())
                log_chat(f"You to {recipient.strip()}: {message.strip()}")
                console.print(f"[bold cyan]You to {recipient.strip()}:[/] {message.strip()}")
            
            else:
                console.print("[red]Use recipient:message or /away message[/]")

        except Exception as e:
            if not processing_task.done():
                console.print(f"[red]Error: {e}[/]")
            break

    processing_task.cancel()
    console.print(f"\n[blue]Disconnected. Logs in {chat_log_file}[/]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIM CLI Client")
    parser.add_argument("--server", required=True)
    parser.add_argument("--port", type=int, default=5190)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        sys.exit(0)
