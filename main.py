import random
import re
import json
import os
import logging
from datetime import datetime

from ai import call_gpt  

# ANSI Color Codes
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
CYAN = '\033[36m'
MAGENTA = '\033[35m'
WHITE = '\033[37m'
RESET = '\033[0m'

# Logging Setup
logging.basicConfig(
    filename="knights_of_theseus.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

# Constants
INITIAL_HEALTH = 100
INITIAL_REPUTATION = {"Townsfolk": 0, "Guard": 0, "Outlaws": 0}
SAVE_DIR = "saves"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)
SKILL_THRESHOLDS = {"easy": 10, "medium": 15, "hard": 20, "very hard": 25}

# Utility Functions

def colored(text, color):
    return f"{color}{text}{RESET}"

def print_title():
    title = """
  _  ___   _ ___ ____ _   _ _____ ____           __ 
 | |/ / \ | |_ _/ ___| | | |_   _/ ___|    ___  / _|
 | ' /|  \| || | |  _| |_| | | | \___ \   / _ \| |_ 
 | . \| |\  || | |_| |  _  | | |  ___) | | (_) |  _|
 |_|\_\_| \_|___\____|_| |_|_|_|_|____/___\___/|_|  
 |_   _| | | | ____/ ___|| ____| | | / ___|         
    | | | |_| |  _| \___ \|  _| | | | \___ \         
    | | |  _  | |___ ___) | |___| |_| |___) |        
    |_| |_| |_|_____|____/|_____|\___/|____/         
    """
    print(colored(title, CYAN))
    print(colored("A text adventure set in a dark and dangerous medieval world.\n", YELLOW))

def print_status(player, world_state):
    print(colored("\n--- Status ---", GREEN))
    print(f"Health: {colored(player.health, RED if player.health < 30 else WHITE)}")
    for stat, value in player.stats.items():
        print(f"{stat}: {value}")
    print(f"Inventory: {player.inventory if player.inventory else 'Empty'}")
    if player.quests:
        print("Quests:")
        for quest, status in player.quests.items():
            print(f"  - {quest}: {status}")
    if player.reputation:
        print("Reputation:")
        for faction, standing in player.reputation.items():
            print(f"  - {faction}: {standing}")
    print("---")

def log_event(event):
    logging.info(event)

def autosave(game):
    game.save(slot_name="autosave")

def safe_json_parse(text):
    if "[object Object]" in text:
        log_event("AI response contained [object Object], skipping turn.")
        print(colored("The story falters for a moment... (AI error). Try again or load a previous save.", RED))
        return {}
    match = re.search(r"\{[\s\S]*?\}", text)
    if match:
        try:
            return json.loads(match.group())
        except Exception as e:
            log_event(f"JSON parse error: {e} | Text: {text}")
            print(colored("There was a problem understanding the game's response. Please try again or load a previous save.", RED))
    return {}

def get_choices_from_ai(ai_response):
    choices = re.findall(r"\d+\.\s*(.+)", extract_narrative(ai_response))
    return choices if choices else ["Continue"]

def get_state_changes_from_ai(ai_response):
    match = re.search(r"STATE_CHANGES:?\s*(\{.*\})", ai_response, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception as e:
            log_event(f"AI state changes parse error: {e}")
            print(colored("There was a problem updating your state. Skipping changes.", RED))
    return {}

def skill_check(player, skill, difficulty):
    modifier = player.stats.get(skill, 0)
    roll = random.randint(1, 20)
    total = roll + modifier
    threshold = SKILL_THRESHOLDS.get(difficulty.lower(), 15)
    print(f"Skill check: {skill} ({difficulty}) - Rolled {roll} + {modifier} = {total} vs {threshold}")
    if roll == 20:
        print(colored("Critical Success!", GREEN))
        return True, True
    elif roll == 1:
        print(colored("Critical Failure!", RED))
        return False, True
    return total >= threshold, False

def input_with_commands(prompt, choices=None, allow_save=True, allow_quit=True):
    while True:
        user_input = input(prompt).strip().lower()
        if allow_save and user_input in {"save", "s"}:
            return "save"
        if allow_quit and user_input in {"quit", "q"}:
            return "quit"
        if choices:
            if user_input.isdigit() and 1 <= int(user_input) <= len(choices):
                return int(user_input)
            else:
                print(f"Please enter a number between 1 and {len(choices)}, or type 'save'/'quit'.")
        else:
            return user_input

def extract_narrative(text):
    split_text = re.split(r'STATE_CHANGES:?', text, flags=re.IGNORECASE)
    return split_text[0].strip()

# Classes

class Player:
    def __init__(self, health, stats, inventory, quests, reputation):
        self.health = health
        self.stats = stats
        self.inventory = inventory
        self.quests = quests
        self.reputation = reputation

    def apply_state_changes(self, changes):
        if not changes:
            return
        # Health
        if "health" in changes:
            self.health = max(0, min(INITIAL_HEALTH, self.health + changes["health"]))
        # Inventory
        for item in changes.get("inventory_add", []):
            if item not in self.inventory:
                self.inventory.append(item)
        for item in changes.get("inventory_remove", []):
            if item in self.inventory:
                self.inventory.remove(item)
        # Quests
        for quest, status in changes.get("quest_update", {}).items():
            self.quests[quest] = status
        # Reputation
        for faction, change in changes.get("reputation", {}).items():
            self.reputation[faction] = self.reputation.get(faction, 0) + change

class Game:
    def __init__(self, player=None, world_state=None, current_situation=""):
        self.player = player
        self.world_state = world_state if world_state is not None else {}
        self.current_situation = current_situation

    def save(self, slot_name=None):
        if not slot_name:
            slot_name = input("Enter save slot name (or press Enter for timestamp): ").strip()
            if not slot_name:
                slot_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(SAVE_DIR, f"{slot_name}.json")
        data = {
            "player": {
                "health": self.player.health,
                "stats": self.player.stats,
                "inventory": self.player.inventory,
                "quests": self.player.quests,
                "reputation": self.player.reputation
            },
            "world_state": self.world_state,
            "current_situation": self.current_situation
        }
        try:
            with open(save_path, "w") as f:
                json.dump(data, f, indent=2)
            print(colored(f"Game saved to {save_path}", GREEN))
            log_event(f"Game saved to {save_path}")
        except Exception as e:
            print(colored("Error saving game!", RED))
            log_event(f"Save error: {e}")

    @staticmethod
    def load(slot_name=None):
        saves = [f for f in os.listdir(SAVE_DIR) if f.endswith(".json")]
        if not saves:
            print(colored("No saved games found.", YELLOW))
            return None
        if not slot_name:
            print("Available saves:")
            for idx, fname in enumerate(saves, 1):
                print(f"{idx}. {fname}")
            while True:
                sel = input("Select save to load: ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(saves):
                    slot_name = saves[int(sel) - 1]
                    break
                else:
                    print("Invalid selection.")
        save_path = os.path.join(SAVE_DIR, slot_name)
        try:
            with open(save_path, "r") as f:
                data = json.load(f)
            player_data = data["player"]
            player = Player(
                player_data["health"],
                player_data["stats"],
                player_data["inventory"],
                player_data["quests"],
                player_data["reputation"]
            )
            return Game(player, data["world_state"], data["current_situation"])
        except Exception as e:
            print(colored("Error loading save!", RED))
            log_event(f"Load error: {e}")
            return None

    def autosave(self):
        self.save(slot_name="autosave")

    def character_creation(self):
        print(colored("\n--- Character Creation ---", MAGENTA))
        print("Answer the following questions to shape your character's stats.")
        # Generate questions via AI
        prompt = (
            "Generate 4 distinct and numbered questions for character creation in a medieval fantasy text adventure. "
            "For each question, provide 3 distinct and numbered answer choices. Format:\n"
            "1. Question text\n"
            "   1. Choice A\n"
            "   2. Choice B\n"
            "   3. Choice C\n"
            "2. ... etc."
        )
        response = call_gpt(prompt).strip()
        questions = []
        q_blocks = re.split(r"\n(?=\d+\.)", response)
        for block in q_blocks:
            lines = block.strip().split('\n')
            if not lines or not lines[0].strip():
                continue
            q_match = re.match(r"\d+\.\s*(.*)", lines[0])
            if not q_match:
                continue
            question = q_match.group(1).strip()
            choices = []
            for line in lines[1:]:
                c_match = re.match(r"\s*\d+\.\s*(.*)", line)
                if c_match:
                    choices.append(c_match.group(1).strip())
            if question and choices:
                questions.append({"question": question, "choices": choices})

        player_choices = []
        for q in questions:
            print(f"\n{q['question']}")
            for idx, choice in enumerate(q["choices"], 1):
                print(f"{idx}. {choice}")
            while True:
                ans = input_with_commands("> ", choices=q["choices"])
                if ans == "save":
                    self.save()
                elif ans == "quit":
                    print(colored("Goodbye!", YELLOW))
                    return  # Clean exit
                elif isinstance(ans, int):
                    player_choices.append(q["choices"][ans-1])
                    break

        # Generate stats via AI
        prompt = (
            "You are a game master. Based on the following player choices, generate stats for Strength, Dexterity, Intelligence, and Charisma. "
            "Each stat should be between 5 and 10. "
            "Reply ONLY with a valid JSON object, with keys exactly: Strength, Dexterity, Intelligence, Charisma. No explanation, no extra text, just the JSON.\n"
            "Player choices:\n"
        )
        for i, choice in enumerate(player_choices, 1):
            prompt += f"{i}. {choice}\n"
        response = call_gpt(prompt).strip()
        stats = safe_json_parse(response)
        if stats and all(k in stats for k in ["Strength", "Dexterity", "Intelligence", "Charisma"]):
            try:
                stats = {k: int(stats[k]) for k in ["Strength", "Dexterity", "Intelligence", "Charisma"]}
            except Exception:
                stats = {"Strength": 7, "Dexterity": 7, "Intelligence": 7, "Charisma": 7}
        else:
            print(colored("AI stat generation failed, using default stats.", RED))
            stats = {"Strength": 7, "Dexterity": 7, "Intelligence": 7, "Charisma": 7}
        print(colored("\nYour stats have been determined:", CYAN))
        for stat, val in stats.items():
            print(f"{stat}: {val}")
        self.player = Player(INITIAL_HEALTH, stats, [], {}, INITIAL_REPUTATION.copy())

    def introduction(self):
        introduction_prompt = (
            "Describe the beginning of a medieval fantasy text adventure called Knights of Theseus. "
            "You are a newly initiated knight. Set a dark and mysterious tone, hinting at an urgent quest and the immediate surroundings. "
            "Generate three numbered choices for your first action, with one potentially involving a skill check (mention the skill and difficulty). "
            "After the narrative, output a JSON block in this exact format: "
            "STATE_CHANGES: {\"health\": 0, \"inventory_add\": [], \"inventory_remove\": [], \"quest_update\": {}, \"reputation\": {}}"
        )
        first_scene = call_gpt(introduction_prompt)
        print(colored(extract_narrative(first_scene), WHITE))
        self.current_situation = first_scene

    def main_loop(self):
        print_title()
        print(colored("\nYour adventure begins.", YELLOW))
        while self.player.health > 0:
            print_status(self.player, self.world_state)
            # Get next choices from AI
            ai_choice_prompt = (
                f"{self.current_situation}\n",,,,,,,,...........
                f"Player stats: {self.player.stats}, inventory: {self.player.inventory}, quests: {self.player.quests}, reputation: {self.player.reputation}.\n"
                "Generate three distinct and numbered choices for what the player can do next. "
                "For at least one choice, suggest an action that might involve a skill check (mention the skill and a difficulty like easy, medium, or hard). "
                "After the choices, output a JSON block in the same STATE_CHANGES format as before."
            )
            ai_choices_response = call_gpt(ai_choice_prompt)
            log_event(f"AI Choices Response: {ai_choices_response}")
            choices = get_choices_from_ai(ai_choices_response)
            print(colored("\nWhat do you do next?", CYAN))
            for idx, choice in enumerate(choices, 1):
                print(f"{idx}. {choice}")
            # Input
            while True:
                user_input = input_with_commands("> ", choices=choices)
                if user_input == "save":
                    self.save()
                    continue
                elif user_input == "quit":
                    print(colored("Thanks for playing!", YELLOW))
                    return  
                elif isinstance(user_input, int):
                    selected_choice = user_input
                    break
            # Outcome
            ai_outcome_prompt = (
                f"The player chose option {selected_choice} from: '{choices[selected_choice-1]}'. "
                "Describe the detailed outcome, including any skill checks attempted by the player (mention the skill and difficulty), "
                "enemies encountered (with a brief description), items found (and their properties), changes in health, "
                "updates to the player's inventory or quest progress, and changes in reputation or world state. "
                "After the narrative, output a JSON block in the same STATE_CHANGES format as before."
            )
            outcome_response = call_gpt(ai_outcome_prompt)
            log_event(f"AI Outcome Response: {outcome_response}")
            narrative = extract_narrative(outcome_response)
            print("\n" + colored(narrative, WHITE))
            state_changes = get_state_changes_from_ai(outcome_response)
            self.player.apply_state_changes(state_changes)
            self.current_situation = narrative
            # Skill check logic
            skill_check_match = re.search(
                r"(?:attempt|make|perform) (?:a|an)?\s*([\w\s]+?)\s*\((\w+) check, difficulty: (\w+)\)", narrative, re.IGNORECASE)
            if skill_check_match:
                action = skill_check_match.group(1).strip()
                skill = skill_check_match.group(2).capitalize()
                difficulty = skill_check_match.group(3).lower()
                if skill in self.player.stats:
                    success, critical = skill_check(self.player, skill, difficulty)
                    if success:
                        print(colored(f"You successfully {action} (succeeded on a {skill} check).", GREEN))
                    else:
                        print(colored(f"You fail to {action} (failed on a {skill} check).", RED))
                        penalty = random.randint(5, 15)
                        if critical:
                            penalty += 10
                        self.player.health = max(0, self.player.health - penalty)
                        print(colored(f"You suffer a setback and lose {penalty} health.", RED))
            # Autosave after each turn
            self.autosave()
        print(colored("\nYour health has reached 0. The darkness consumes you. Game Over.", RED))
        while True:
            choice = input("Would you like to restart? (y/n): ").strip().lower()
            if choice == "y":
                main()
                break
            elif choice == "n":
                print(colored("Farewell, brave knight.", YELLOW))
                break
            else:
                print("Please enter 'y' or 'n'.")

# Main Function

def main():
    print(colored("Welcome to Knights of Theseus!", CYAN))
    print("Type 'save' or 's' at any prompt to save your game, or 'quit'/'q' to exit.")
    print("Type 'load' at the main menu to load a saved game.")
    while True:
        print("\n1. New Game\n2. Load Game\n3. Quit")
        choice = input_with_commands("> ", choices=["New Game", "Load Game", "Quit"], allow_save=False)
        if choice == 1:
            game = Game()
            game.character_creation()
            if not game.player:
                return
            game.introduction()
            break
        elif choice == 2:
            game = Game.load()
            if game:
                break
        elif choice == 3 or choice == "quit":
            print(colored("Goodbye!", YELLOW))
            return
        else:
            print("Invalid choice.")
    game.main_loop()

if __name__ == '__main__':
    main()
