import os
import shutil

def setup():
    out_dir = "submissions"
    if os.path.exists(out_dir):
        try:
            shutil.rmtree(out_dir)
        except: pass
    os.makedirs(out_dir, exist_ok=True)
    
    adversarial = {
        "team_crash": "def decide(state):\n    raise Exception('boom')\n",
        "team_invalid": "def decide(state):\n    return 'HELLO_WORLD'\n",
        "team_spam": "def decide(state):\n    print('THIS_IS_SPAM ' * 10000)\n    return 'COOPERATE'\n",
        "team_hacker": "import os\ndef decide(state):\n    os.system('echo hi')\n    return 'DEFECT'\n"
    }
    
    for team, code in adversarial.items():
        os.makedirs(f"{out_dir}/{team}", exist_ok=True)
        with open(f"{out_dir}/{team}/my_agent.py", "w") as f:
            f.write(code)
            
    for i in range(15):
        team = f"team_normal_{i}"
        os.makedirs(f"{out_dir}/{team}", exist_ok=True)
        with open(f"{out_dir}/{team}/my_agent.py", "w") as f:
            f.write("import random\ndef decide(state):\n    return random.choice(['COOPERATE', 'DEFECT', 'IGNORE'])\n")

    print(f"Created {len(adversarial) + 15} isolated submission folders.")

if __name__ == "__main__":
    setup()
