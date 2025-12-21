#!/usr/bin/env python3
import asyncio
import argparse
import logging
import sys
import os
from rich.console import Console
from rich.prompt import Prompt
from aimpyfly import aim_client

# 1. Setup Console
console = Console()

# 2. SILENCE ALL LOGGING
# This prevents the SNAC warnings and keep-alive info from breaking the prompt.
# We send them to 'aim_debug.log' instead so you can still read them if you want.
logging.basicConfig(
    level=logging.DEBUG,
    filename='aim_debug.log',
    filemode='w',
    format='%(asctime)s [%(levelname)s]: %(message)s'
)
# Completely block logs from hitting the terminal
for handler in logging.root.handlers[:]:
    if not isinstance(handler, logging.FileHandler):
        logging.root.removeHandler(handler)

async def message_received(sender, message):
    # Use console.print to cleanly break the prompt line
    console.print(f"\r[bold green]{sender}:[/] {message}")

async def ainput(prompt: str) -> str:
    """Run the prompt in a way that doesn't get spammed."""
    loop = asyncio.get_event_loop()
    # We add a tiny sleep to let the event loop breathe
    await asyncio.sleep(0.1)
    return await loop.run_in_executor(None, lambda: Prompt.ask(prompt))

async def main(args):
    client = aim_client.AIMClient(
        server=args.server,
        port=args.port,
        username=args.username,
        password=args.password,
        loglevel=logging.DEBUG # Log to file, not screen
    )
    client.set_message_callback(message_received)

    try:
        console.print(f"[yellow]Connecting to {args.server}...[/]")
        await client.connect()
        
        # Verify connection safety
        if not hasattr(client, 'writer') or client.writer is None or client.writer.is_closing():
            console.print("[bold red]Connection failed: BOS redirection issue (likely 0.0.0.0).[/]")
            return
            
        console.print("[bold blue]Connected! (Type /help for commands)[/]")
    except Exception as e:
        console.print(f"[bold red]Connection failed: {e}[/]")
        return

    # Start the packet processor in the background
    processing_task = asyncio.create_task(client.process_incoming_packets())

    while not processing_task.done():
        try:
            # We use a slightly longer timeout to reduce prompt jitter
            input_str = await asyncio.wait_for(ainput(">"), timeout=2.0)
            
            if not input_str:
                continue
                
            cmd = input_str.strip()
            if cmd.lower() == "/quit":
                break
            elif cmd.lower() == "/help":
                console.print("[bold yellow]Commands:[/]\n/quit - exit\nrecipient:message - send message")
                continue
            elif ":" not in cmd:
                console.print("[bold red]Invalid format. Use recipient:message[/]")
                continue

            recipient, message = cmd.split(":", 1)
            await client.send_message(recipient.strip(), message.strip())
            console.print(f"[bold cyan]Sent to {recipient.strip()}:[/] {message.strip()}")

        except asyncio.TimeoutError:
            continue
        except (EOFError, KeyboardInterrupt):
            break
        except Exception as e:
            # Check if connection died
            if processing_task.done():
                break
            console.print(f"[bold red]Error: {e}[/]")

    console.print("\n[bold blue]Disconnecting...[/]")
    processing_task.cancel()
    try:
        await processing_task
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIM CLI Client")
    parser.add_argument("--server", required=True, help="AIM server address")
    parser.add_argument("--port", type=int, default=5190, help="AIM server port")
    parser.add_argument("--username", required=True, help="Username/screenname")
    parser.add_argument("--password", required=True, help="Password")
    args = parser.parse_args()

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        pass
