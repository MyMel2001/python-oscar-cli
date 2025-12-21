#!/usr/bin/env python3
import asyncio
import argparse
import logging
import sys
from rich.console import Console

# --- 1. EMERGENCY LOG SILENCING ---
# We do this BEFORE anything else to catch library logs
logging.getLogger("aimpyfly").setLevel(logging.CRITICAL)
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

console = Console()

async def message_received(sender, message):
    # Move to start of line, clear line, print message, then reprint prompt
    sys.stdout.write(f"\r\033[K[bold green]{sender}:[/] {message}\n> ")
    sys.stdout.flush()

async def get_input():
    """Non-blocking way to read line from stdin"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sys.stdin.readline)

async def main(args):
    from aimpyfly import aim_client
    
    client = aim_client.AIMClient(
        server=args.server,
        port=args.port,
        username=args.username,
        password=args.password,
        loglevel=logging.CRITICAL
    )
    client.set_message_callback(message_received)

    try:
        console.print(f"[yellow]Connecting to {args.server}...[/]")
        await client.connect()
        console.print("[bold blue]Connected! Commands: recipient:msg or /quit[/]")
    except Exception as e:
        console.print(f"[bold red]Connection failed: {e}[/]")
        return

    # Start the background processor
    processing_task = asyncio.create_task(client.process_incoming_packets())

    while not processing_task.done():
        try:
            # Print prompt manually
            sys.stdout.write("> ")
            sys.stdout.flush()
            
            # Read input without blocking the whole loop
            line = await get_input()
            if not line:
                break
                
            cmd = line.strip()
            if not cmd:
                continue

            if cmd.lower() == "/quit":
                break
            elif cmd.lower() == "/help":
                console.print("[bold yellow]Format:[/] recipient:message\n[bold yellow]Exit:[/] /quit")
                continue
            elif ":" in cmd:
                recipient, message = cmd.split(":", 1)
                await client.send_message(recipient.strip(), message.strip())
                console.print(f"[bold cyan]Sent to {recipient.strip()}:[/] {message.strip()}")
            else:
                console.print("[red]Invalid format. Use recipient:message[/]")

        except Exception as e:
            console.print(f"[red]Error: {e}[/]")
            break

    processing_task.cancel()
    console.print("\n[blue]Disconnected.[/]")

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
