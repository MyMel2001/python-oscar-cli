#!/usr/bin/env python3
import asyncio
import argparse
import logging
import sys
from rich.console import Console
from rich.prompt import Prompt
from aimpyfly import aim_client

console = Console()

# Set library logging to WARNING to prevent "keep-alive" spam in the UI
logging.basicConfig(level=logging.WARNING, format='%(asctime)s [%(levelname)s]: %(message)s')
logger = logging.getLogger("aimpyfly")
logger.setLevel(logging.WARNING)

async def message_received(sender, message):
    # Print on a new line to avoid clashing with the prompt
    console.print(f"\n[bold green]{sender}:[/] {message}")

async def ainput(prompt: str) -> str:
    """Run the blocking rich prompt in a thread to keep the loop alive."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: Prompt.ask(prompt))

async def main(args):
    client = aim_client.AIMClient(
        server=args.server,
        port=args.port,
        username=args.username,
        password=args.password,
        loglevel=logging.WARNING # Keep internal logs quiet
    )
    client.set_message_callback(message_received)

    # 1. Connect and handle the BOS redirection
    try:
        console.print(f"[yellow]Connecting to {args.server}...[/]")
        await client.connect()
        
        # Check if BOS connection actually succeeded
        if not hasattr(client, 'writer') or client.writer is None or client.writer.is_closing():
            console.print("[bold red]Error: Connection established but BOS handshake failed.[/]")
            console.print("[red]Hint: Check if your server is redirecting to 0.0.0.0 instead of its real IP.[/]")
            return
            
        console.print("[bold blue]Connected successfully![/]")
    except Exception as e:
        console.print(f"[bold red]Connection failed: {e}[/]")
        return

    # 2. Start the background packet processor
    processing_task = asyncio.create_task(client.process_incoming_packets())

    # 3. Main Input Loop
    while not processing_task.done():
        try:
            # We wait for input. If the background task dies, we want to know.
            # Using a timeout allows us to check the status of the connection.
            input_str = await asyncio.wait_for(ainput("> "), timeout=1.0)
            
            if not input_str:
                continue
            if input_str.strip().lower() == "/quit":
                break
            elif input_str.strip().lower() == "/help":
                console.print("[bold yellow]Commands:[/]\n/quit - exit\nrecipient:message - send message")
                continue
            elif ":" not in input_str:
                console.print("[bold red]Invalid format. Use recipient:message[/]")
                continue

            recipient, message = input_str.split(":", 1)
            await client.send_message(recipient.strip(), message.strip())
            console.print(f"[bold cyan]You to {recipient.strip()}:[/] {message.strip()}")

        except asyncio.TimeoutError:
            # Just loop back and check if the processing_task is still alive
            continue
        except EOFError:
            break
        except Exception as e:
            console.print(f"[bold red]Error: {e}[/]")
            break

    # 4. Cleanup
    console.print("[bold blue]Shutting down...[/]")
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
        sys.exit(0)
