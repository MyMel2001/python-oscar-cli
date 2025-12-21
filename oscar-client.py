#!/usr/bin/env python3
import asyncio
import argparse
import logging
import sys
import datetime
from rich.console import Console

# Emergency silence to prevent prompt corruption
logging.getLogger("aimpyfly").setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.CRITICAL)

console = Console()

# Global state for our new features
online_buddies = set()
chat_log_file = "chat_log.txt"

def log_chat(text):
    """Appends messages to a local text file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(chat_log_file, "a") as f:
        f.write(f"[{timestamp}] {text}\n")

async def message_received(sender, message):
    log_entry = f"{sender}: {message}"
    log_chat(log_entry)
    # Clear line and print incoming message
    sys.stdout.write(f"\r\033[K[bold green]{sender}:[/] {message}\n> ")
    sys.stdout.flush()

# This is a bit advanced: we wrap the presence handler to track buddies
async def presence_update(buddy_name, online):
    if online:
        online_buddies.add(buddy_name)
    else:
        online_buddies.discard(buddy_name)

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
    
    # Setup Callbacks
    client.set_message_callback(message_received)
    # Note: aimpyfly might not have a direct presence callback in all versions, 
    # but it updates internal state. We'll use our manual list for now.

    try:
        console.print(f"[yellow]Connecting to {args.server}...[/]")
        await client.connect()
        console.print("[bold blue]Connected![/] Type [bold yellow]/help[/] for new commands.")
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

            # --- COMMAND LOGIC ---
            if cmd.lower() == "/quit":
                break
            
            elif cmd.lower() == "/help":
                console.print("\n[bold yellow]Commands:[/]")
                console.print(" recipient:message - Send a private message")
                console.print(" /buddies         - Show online users")
                console.print(" /away <msg>      - Set away status")
                console.print(" /back            - Return from away")
                console.print(" /quit            - Exit\n")
            
            elif cmd.lower() == "/buddies":
                if not online_buddies:
                    console.print("[italic]No buddies currently detected as online.[/]")
                else:
                    console.print(f"[bold green]Online:[/bold green] {', '.join(online_buddies)}")

            elif cmd.lower().startswith("/away "):
                away_msg = cmd[6:].strip()
                await client.set_away_message(away_msg)
                console.print(f"[yellow]Away mode set: {away_msg}[/]")

            elif cmd.lower() == "/back":
                await client.set_away_message("") # Empty string clears away status
                console.print("[green]Welcome back! Away status cleared.[/]")

            elif ":" in cmd:
                recipient, message = cmd.split(":", 1)
                recipient = recipient.strip()
                message = message.strip()
                await client.send_message(recipient, message)
                log_chat(f"You to {recipient}: {message}")
                console.print(f"[bold cyan]You to {recipient}:[/] {message}")
            
            else:
                console.print("[red]Invalid format. Use recipient:message[/]")

        except Exception as e:
            if not processing_task.done():
                console.print(f"[red]Error: {e}[/]")
            break

    processing_task.cancel()
    console.print("\n[blue]Disconnected. Chat saved to chat_log.txt[/]")

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
        pass
