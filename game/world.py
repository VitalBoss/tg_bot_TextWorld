import subprocess
import tempfile
import uuid
from config import request_infos
import textworld
import logging
logger = logging.getLogger("game.world")


def make_new_world(difficulty: str = "medium"):
    """
    Возвращает (game_path, quest_name) или (None, None) при ошибке.
    difficulty: 'easy', 'medium', 'hard'
    """
    # Параметры для tw-make
    settings = {
        'easy':   {'world_size': 3, 'nb_objects': 3, 'quest_length': 3},
        'medium': {'world_size': 5, 'nb_objects': 5, 'quest_length': 5},
        'hard':   {'world_size': 7, 'nb_objects': 7, 'quest_length': 7},
    }
    cfg = settings.get(difficulty, settings['medium'])
    
    cmd = [
        "tw-make", "custom",
        "--world-size", str(cfg['world_size']),
        "--nb-objects", str(cfg['nb_objects']),
        "--quest-length", str(cfg['quest_length']),
        "--output"
    ]
    with tempfile.NamedTemporaryFile(suffix='.z8', delete=False) as tmp:
        game_path = tmp.name
        cmd.append(game_path)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Ошибка генерации игры: {result.stderr}")
            return None, None
        quest_name = f"Quest-{uuid.uuid4().hex[:8]}"
        return game_path, quest_name

class GameSession:
    def __init__(self, game_path: str):
        try:
            self.env = textworld.start(game_path, request_infos)
            self.state = self.env.reset()
        except Exception as e:
            logger.exception(f"Failed to start game session for {game_path}")
            raise 

    def step(self, command: str):
        self.state, reward, done = self.env.step(command)
        return self.state['feedback'], self.state['admissible_commands'], done, reward