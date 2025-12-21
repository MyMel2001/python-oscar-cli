#!/usr/bin/env python3
"""
Alternative CLI client for OSCAR (AIM) protocol using aimpyfly library.
Requires: pip install aimpyfly rich

Usage: python aim_cli.py --server <server> --port <port> --username <username> --password <password>

Once connected, type messages in the format: recipient:message
Type /quit to exit.
Type /help for commands.

Cross-platform, easy-to-use with rich formatting for better looks.
"""

import asyncio
import argparse
import logging
import sys
from rich.console import Console
from rich.prompt import Prompt
from aimpyfly import aim_client

console = Console()

async def message_received(sender, message):
    console.print(f"[bold green]{sender}:[/] {message}")

async def process_wrapper(client):
    try:
        await client.process_incoming_packets()
    except Exception as e:
        console.print(f"[bold red]Processing failed: {e}. Disconnecting.[/]")
        raise  # Re-raise to mark task as errored

processing_task = asyncio.create_task(process_wrapper(client))

async def main(args):
    client = aim_client.AIMClient(
        server=args.server,
        port=args.port,
        username=args.username,
        password=args.password,
        loglevel=logging.CRITICAL
    )
    client.set_message_callback(message_received)
    
    try:
        await client.connect()
        console.print("[bold blue]Connected successfully![/]")
    except Exception as e:
        console.print(f"[bold red]Connection failed: {e}[/]")
        return

    # Task for processing incoming packets
    processing_task = asyncio.create_task(client.process_incoming_packets())

    # Interactive loop for user input
    while True:
        if processing_task.done() and processing_task.exception():
            console.print("[bold red]Connection lost. Exiting.[/]")
            break

        try:
            input_str = await ainput("> ")
            if input_str.startswith("/quit"):
                break
            elif input_str.startswith("/help"):
                console.print("[bold yellow]Commands:[/]\n/quit - exit\n recipient:message - send message")
                continue
            elif ":" not in input_str:
                console.print("[bold red]Invalid format. Use recipient:message[/]")
                continue

            recipient, message = input_str.split(":", 1)
            await client.send_message(recipient.strip(), message.strip())
            console.print(f"[bold cyan]You to {recipient}:[/] {message.strip()}")
        except EOFError:
            break

    processing_task.cancel()
    console.print("[bold blue]Disconnecting...[/]")

# Async input function
async def ainput(prompt: str) -> str:
    return await asyncio.get_event_loop().run_in_executor(None, lambda: Prompt.ask(prompt))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIM CLI Client")
    parser.add_argument("--server", required=True, help="AIM server address")
    parser.add_argument("--port", type=int, default=5190, help="AIM server port")
    parser.add_argument("--username", required=True, help="Username/screenname")
    parser.add_argument("--password", required=True, help="Password")
    args = parser.parse_args()

    asyncio.run(main(args))
