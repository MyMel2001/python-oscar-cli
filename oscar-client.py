#!/usr/bin/env python3
import asyncio
import argparse
import logging
import sys
import datetime
from rich.console import Console

# Emergency silence
logging.getLogger("aimpyfly").setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.CRITICAL)

console = Console()
online_buddies = set()
chat_log_file = "chat_log.txt"

def log_chat(text):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(chat_log_file, "a") as f:
            f.write(f"[{timestamp}] {text}\n")
    except Exception as e:
        pass # Don't let logging kill the app

async def message_received(sender, message):
    log_chat(f"{sender}: {message}")
    sys.stdout.write(f"\r\033[K[bold green]{sender}:[/] {message}\n> ")
    sys.stdout.flush()

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
        console.print("[bold blue]Connected![/] Commands: [bold yellow]recipient:msg[/], [bold yellow]/buddies[/], [bold yellow]/quit[/]")
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
            
            elif cmd.lower() == "/help":
                console.print("\n[bold yellow]Available Commands:[/]")
                console.print(" recipient:message - Send a private message")
                console.print(" /buddies         - Show who is online")
                console.print(" /quit            - Exit and save logs\n")
            
            elif cmd.lower() == "/buddies":
                # Most OSCAR libraries store buddies in client.buddies
                # We'll try to pull from the client's internal session if it exists
                buddies = getattr(client, 'buddies', [])
                if not buddies:
                    console.print("[italic]Buddy list is empty or hasn't loaded yet.[/]")
                else:
                    console.print(f"[bold green]Buddy List:[/bold green] {', '.join(buddies)}")

            elif ":" in cmd:
                recipient, message = cmd.split(":", 1)
                recipient = recipient.strip()
                message = message.strip()
                
                # Use the library's message sender
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
    console.print(f"\n[blue]Disconnected. Conversation saved to {chat_log_file}[/]")

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
