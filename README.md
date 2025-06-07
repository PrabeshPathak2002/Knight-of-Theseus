---

🛡️ Knights of Theseus

Knights of Theseus is a text-based, AI-assisted medieval fantasy adventure game. Dive into a world of mystery, danger, and choices that shape your fate. Powered by GPT for immersive storytelling and dynamic gameplay, this game lets you role-play a knight navigating quests, skill challenges, and branching narratives.


---

⚠️ Notice: Stanford CIP Dependency

This game was developed specifically for the Stanford Code in Place (CIP) IDE, which includes a custom ai module to interface with GPT.

If you're running this code outside the CIP environment, you must create your own ai.py file with a call_gpt(prompt: str) -> str function. This function should handle calls to the GPT API (such as openai.ChatCompletion.create).

Sample stub:

```python
def call_gpt(prompt: str) -> str:
    # Replace this with your actual GPT API call
    return "Mock GPT response"
```

> ⚠️ Without this module, the game will not run as intended.




---

📜 Features

🧠 AI-generated narratives, character creation questions, and stat generation

🎭 Player character with stats: Strength, Dexterity, Intelligence, Charisma

🎯 Skill checks based on dice rolls and modifiers

🎒 Inventory, quests, reputation, and health system

💾 Save and load game functionality (including autosave)

🌈 Colored terminal output for better immersion



---

🧰 Installation

```Bash
git clone https://github.com/yourusername/knights-of-theseus.git
cd knights-of-theseus
```

---

🚀 Running the Game
```Bash
python main.py
```

---

💾 Save System

All game saves are stored in the saves/ folder as .json files.

Autosave occurs during key moments.

You can load a previous save when starting the game.



---

🧠 Credits

Created by: Prabesh Pathak
Designed as a final project for: Stanford Code in Place 2025
GPT integration powered by: OpenAI


---
