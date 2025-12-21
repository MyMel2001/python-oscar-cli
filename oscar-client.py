#!/usr/bin/env python3
import asyncio
import argparse
import logging
import sys
import datetime
import time
from rich.console import Console

# Silence standard logs
logging.getLogger("aimpyfly").setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.CRITICAL)

console = Console()
chat_log_file = "chat_log.txt"

# --- GLOBAL STATE ---
is_away = False
away_message = ""
# Dictionary to store {buddy_name: last_reply_timestamp}
responded_buddies = {} 
# Cooldown in seconds (e.g., 300 seconds = 5 minutes)
AUTO_REPLY_COOLDOWN = 300 
current_client = None

def log_chat(text):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(chat_log_file, "a") as f:
        f.write(f"[{timestamp}] {text}\n")

async def message_received(sender, message):
    global is_away, away_message, responded_buddies, current_client
    
    time_str = datetime.datetime.now().strftime("%H:%M:%S")
    log_chat(f"{sender}: {message}")
    
    # 1. Print the incoming message
    sys.stdout.write("\r\033[K") 
    console.print(f"[dim][{time_str}][/] [bold green]{sender}:[/] {message}")
    sys.stdout.write("> ")
    sys.stdout.flush()

    # 2. IMPROVED AUTO-RESPONDER LOGIC
    if is_away and current_client:
        current_time = time.time()
        last_reply_time = responded_buddies.get(sender, 0)

        # Check if we've never replied OR if the cooldown has passed
        if (current_time - last_reply_time) > AUTO_REPLY_COOLDOWN:
            await current_client.send_message(sender, f"[Auto-Reply] {away_message}")
            responded_buddies[sender] = current_time
            log_chat(f"Auto-Replied to {sender}: {away_message}")

async def get_input():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sys.stdin.readline)

async def main(args):
    global is_away, away_message, responded_buddies, current_client
    from aimpyfly import aim_client
    
    current_client = aim_client.AIMClient(
        server=args.server, port=args.port,
        username=args.username, password=args.password,
        loglevel=logging.CRITICAL
    )
    current_client.set_message_callback(message_received)

    try:
        console.print(f"[yellow]Connecting to {args.server}...[/]")
        await current_client.connect()
        console.print("[bold blue]Connected![/] Away format: /away <msg>")
    except Exception as e:
        console.print(f"[bold red]Connection failed: {e}[/]")
        return

    processing_task = asyncio.create_task(current_client.process_incoming_packets())

    while not processing_task.done():
        try:
            sys.stdout.write("> ")
            sys.stdout.flush()
            
            line = await get_input()
            if not line: break
            cmd = line.strip()
            if not cmd: continue

            # Reset Away Status if the user sends ANY manual message
            if is_away and not cmd.startswith("/"):
                is_away = False
                responded_buddies.clear()
                console.print("[bold green]Welcome back! Auto-responder disabled.[/]")

            if cmd.lower() == "/quit":
                break
            
            elif cmd.lower().startswith("/away "):
                away_message = cmd[6:].strip()
                is_away = True
                responded_buddies.clear() 
                console.print(f"[bold yellow]Away status active:[/] {away_message}")

            elif cmd.lower() == "/back":
                is_away = False
                responded_buddies.clear()
                console.print("[bold green]Auto-responder disabled.[/]")

            elif ":" in cmd:
                recipient, message = cmd.split(":", 1)
                r_clean = recipient.strip()
                m_clean = message.strip()
                
                await current_client.send_message(r_clean, m_clean)
                log_chat(f"You to {r_clean}: {m_clean}")
                
                # Visual cleanup
                time_str = datetime.datetime.now().strftime("%H:%M:%S")
                sys.stdout.write("\033[F\033[K") 
                console.print(f"[dim][{time_str}][/] [bold cyan]You to {r_clean}:[/] {m_clean}")
            
            else:
                console.print("[red]Format: recipient:message , /away message , /back or /quit[/]")

        except Exception as e:
            break

    processing_task.cancel()
    console.print("\n[blue]Disconnected.[/]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--port", type=int, default=5190)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        sys.exit(0)
