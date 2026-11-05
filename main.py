import os
import json
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from rich.console import Console
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN or HF_TOKEN == "hf_your_actual_token_here":
    print("❌ ERROR: Missing token! Please ensure your .env file exists and contains a valid HF_TOKEN.")
    exit()

# Using Qwen2.5-Coder-7B-Instruct for high-fidelity JSON parsing and deep roleplay
client = InferenceClient(model="Qwen/Qwen2.5-Coder-7B-Instruct", token=HF_TOKEN)
console = Console()


def generate_procedural_case():
    console.print("[bold yellow]🌀 Ingesting files... Contacting Hugging Face to generate a unique case...[/bold yellow]")
    
    prompt = """
    Generate a unique, creative cyberpunk or classic noir murder mystery case profile in strict JSON format. 
    Do not include any introductory text, concluding remarks, markdown syntax, or backticks (like ```json). Return ONLY the raw JSON string.

    The JSON must follow this exact structure:
    {
      "victim": "Name of the victim",
      "crime_scene": "Description of where it happened",
      "weapon": "The murder weapon",
      "killer_name": "Name of the actual killer",
      "suspects": [
        {
          "name": "Suspect 1 Name",
          "occupation": "Job title",
          "alibi": "Where they claim they were",
          "secret": "A dark hidden secret or motive they try to hide",
          "trigger_word": "A specific object, clue, or topic word that makes them slip up if mentioned"
        },
        {
          "name": "Suspect 2 Name",
          "occupation": "Job title",
          "alibi": "Where they claim they were",
          "secret": "A dark hidden secret or motive they try to hide",
          "trigger_word": "A specific object, clue, or topic word that makes them slip up if mentioned"
        },
        {
          "name": "Suspect 3 Name",
          "occupation": "Job title",
          "alibi": "Where they claim they were",
          "secret": "A dark hidden secret or motive they try to hide",
          "trigger_word": "A specific object, clue, or topic word that makes them slip up if mentioned"
        }
      ]
    }
    Make sure one of the suspects matches the killer_name perfectly.
    """
    
    response = client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
        temperature=0.85
    )
    
    raw_text = response.choices.message.content.strip()
    
    # Cleaning up accidental markdown wrappings if the model includes them
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        raw_text = "\n".join(lines).strip()
        
    return json.loads(raw_text)


def ask_suspect(case, suspect, player_question):
    is_killer = "YES" if suspect['name'].lower() == case['killer_name'].lower() else "NO"
    
    system_prompt = f"""
    You are roleplaying as {suspect['name']}, a {suspect['occupation']} in a murder mystery terminal game.
    The victim is {case['victim']}. You are currently being interrogated by a detective.
    Your Alibi: {suspect['alibi']}
    Your Secret/Motive: {suspect['secret']}
    Are you secretly the killer?: {is_killer}
    Your breaking point keyword: '{suspect['trigger_word']}'

    RULES:
    1. Respond strictly in character. Be suspicious, nervous, defensive, or arrogant depending on your role.
    2. Do NOT reveal your secret or admit you are the killer right away.
    3. CRITICAL: If the player's question contains your breaking point keyword '{suspect['trigger_word']}' (or close variations of it), you must break composure, panic, and accidentally reveal your secret or drop a massive incriminating hint.
    4. Keep your response under 3 sentences. Do not break character.
    """

    response = client.chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": player_question}
        ],
        max_tokens=150,
        temperature=0.7
    )
    return response.choices.message.content.strip()

# =====================================================================
# 4. REFRESHING THE USER INTERFACE
# =====================================================================
def draw_ui(case, turns, logs):
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1)
    )
    layout["body"].split_row(
        Layout(name="sidebar", ratio=1),
        Layout(name="main_log", ratio=2)
    )

    # Header Panel
    layout["header"].update(Panel(
        f"🕵️‍♂️ [bold cyan]SYNTHETIC NOIR[/bold cyan] | 🩸 Victim: [bold red]{case['victim']}[/bold red] | ⏳ Interrogations Remaining: [bold yellow]{turns}[/bold yellow]", 
        style="green"
    ))

    # Sidebar Content
    sidebar_content = (
        f"📍 [bold white]Scene:[/bold white] [dim]{case['crime_scene']}[/dim]\n"
        f"⚙️ [bold white]Weapon:[/bold white] {case['weapon']}\n\n"
        f"-----------------------------------------\n"
        f"[bold green]Instructions:[/bold green]\n"
        f"Type [cyan]1, 2, or 3[/cyan] to target a suspect.\n"
        f"Type [magenta]A[/magenta] to close the case and Accuse.\n"
        f"Type [red]Q[/red] to exit the terminal."
    )
    layout["sidebar"].update(Panel(sidebar_content, title="[bold white]Case Dossier[/bold white]", border_style="blue"))

    # Conversation History Display
    log_history = "\n\n".join(logs[-4:])  # Renders the 4 most recent interactions
    layout["main_log"].update(Panel(
        log_history if log_history else "[dim italic]Select a suspect file below to begin your cross-examination...[/dim italic]", 
        title="[bold white]Interrogation Room Feed[/bold white]",
        border_style="magenta"
    ))

    # Print Layout & Suspect Table Data
    console.clear()
    console.print(layout)

    table = Table(expand=True, border_style="dim")
    table.add_column("ID", justify="center", style="cyan", width=4)
    table.add_column("Suspect Name", style="bold white", width=25)
    table.add_column("Occupation", style="dim text")
    
    for idx, s in enumerate(case['suspects'], 1):
        table.add_row(str(idx), s['name'], s['occupation'])
    
    console.print(table)

# =====================================================================
# 5. EXECUTION LOOP
# =====================================================================
def play_game():
    try:
        case = generate_procedural_case()
    except Exception as e:
        console.print(f"[bold red]Failed to establish case data or parse JSON structure via Hugging Face API: {e}[/bold red]")
        return

    turns = 8
    dialogue_logs = []
    
    while turns > 0:
        draw_ui(case, turns, dialogue_logs)
        
        action = Prompt.ask("\n[bold green]Action Command[/bold green]")
        
        if action.lower() == 'q':
            console.print("[yellow]Closing investigation dashboard... Goodbye, Detective.[/yellow]")
            break
            
        elif action.lower() == 'a':
            draw_ui(case, turns, dialogue_logs)
            console.print("\n[bold red]🚨 ENTER ARREST WARPING TARGET 🚨[/bold red]")
            accused = Prompt.ask("[bold white]Type the exact name of your primary suspect[/bold white]")
            
            if accused.strip().lower() == case['killer_name'].lower():
                console.print(f"\n🎉 [bold green]CASE SOLVED![/bold green] You successfully caught [bold white]{case['killer_name']}[/bold white]! Justice served.")
            else:
                console.print(f"\n❌ [bold red]CRITICAL MISCARRIAGE OF JUSTICE![/bold red] You pinned it on an innocent citizen. The killer was [bold yellow]{case['killer_name']}[/bold yellow]. You've been stripped of your badge.")
            break
            
        elif action in ['1', '2', '3']:
            target_suspect = case['suspects'][int(action) - 1]
            question = Prompt.ask(f"[bold cyan]Question to {target_suspect['name']}[/bold cyan]")
            
            with console.status("[dim]Analyzing voice stress patterns...[/dim]", spinner="bouncingBar"):
                reply = ask_suspect(case, target_suspect, question)
            
            dialogue_logs.append(f"[bold cyan]Detective:[/bold cyan] {question}\n[bold yellow]{target_suspect['name']}:[/bold yellow] {reply}")
            turns -= 1
        else:
            console.print("[bold red]Command not recognized. Enter 1-3, A, or Q.[/bold red]")
            
    if turns == 0:
        console.print(f"\n💥 [bold red]INVESTIGATION WINDOW CLOSED![/bold red] You ran out of authority. The killer escaped. The true culprit was [bold yellow]{case['killer_name']}[/bold yellow].")

if __name__ == "__main__":
    play_game()