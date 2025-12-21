#!/usr/bin/env python3
import asyncio
import argparse
import logging
import sys
from rich.console import Console
from rich.prompt import Prompt
from aimpyfly import aim_client

console = Console()

async def message_received(sender, message):
    console.print(f"\n[bold green]{sender}:[/] {message}")

async def main(args):
    client = aim_client.AIMClient(
        server=args.server,
        port=args.port,
        username=args.username,
        password=args.password,
        loglevel=logging.INFO # Changed to INFO to reduce spam, set to DEBUG if needed
    )
    client.set_message_callback(message_received)

    # 1. CONNECT FIRST
    try:
        await client.connect()
        console.print("[bold blue]Connected successfully![/]")
    except Exception as e:
        console.print(f"[bold red]Initial connection failed: {e}[/]")
        return

    # Create the task for processing
    processing_task = asyncio.create_task(client.process_incoming_packets())

    while True:
        # Check if the processing task died (e.g., due to Broken Pipe)
        if processing_task.done():
            try:
                # This will raise the actual error that killed the task
                processing_task.result()
            except Exception as e:
                console.print(f"\n[bold red]Connection lost (Broken Pipe): {e}[/]")
                console.print("[yellow]Attempting to reconnect in 5 seconds...[/]")
                await asyncio.sleep(5)
                # You could add logic here to call client.connect() again
                break # For now, let's exit so you can debug the server logs

        try:
            # We use a timeout so the loop can check if the connection is still alive
            input_str = await asyncio.wait_for(ainput("> "), timeout=1.0)
            
            if not input_str: continue
            if input_str.startswith("/quit"): break
            
            # ... (Rest of your message sending logic) ...

        except asyncio.TimeoutError:
            # Just a heartbeat to check if processing_task is still running
            continue
        except Exception as e:
            console.print(f"[bold red]Input Error: {e}[/]")
            break

    processing_task.cancel()

    # 2. START PROCESSING ONLY AFTER CONNECTED
    # The 'reader' attribute is now initialized within the client
    processing_task = asyncio.create_task(client.process_incoming_packets())

    # Interactive loop for user input
    while True:
        try:
            input_str = await ainput("> ")
            if not input_str:
                continue
            if input_str.startswith("/quit"):
                break
            elif input_str.startswith("/help"):
                console.print("[bold yellow]Commands:[/]\n/quit - exit\nrecipient:message - send message")
                continue
            elif ":" not in input_str:
                console.print("[bold red]Invalid format. Use recipient:message[/]")
                continue

            recipient, message = input_str.split(":", 1)
            await client.send_message(recipient.strip(), message.strip())
            console.print(f"[bold cyan]You to {recipient}:[/] {message.strip()}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            console.print(f"[bold red]Error: {e}[/]")

    # 3. CLEANUP
    processing_task.cancel()
    try:
        await processing_task
    except asyncio.CancelledError:
        pass
    console.print("[bold blue]Disconnecting...[/]")

async def ainput(prompt: str) -> str:
    # Use run_in_executor to prevent blocking the event loop while waiting for typing
    return await asyncio.get_event_loop().run_in_executor(None, lambda: Prompt.ask(prompt))

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
