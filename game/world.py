import textworld
from textworld.generator import compile_game
import subprocess
import tempfile
from config import request_infos

def make_new_world() -> str:
    """Генерирует игру и возвращает путь к .ulx файлу."""
    cmd = [
            "tw-make", "custom",
            "--world-size", str(5),
            "--nb-objects", str(5),
            "--quest-length", str(5),
            "--output"
        ]
    with tempfile.NamedTemporaryFile(suffix='.z8', delete=False) as tmp:
        game_path = tmp.name
        cmd.append(game_path)
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Ошибка генерации игры: {result.stderr}")
            return None
        
        return game_path

class GameSession:
    def __init__(self, game_path: str):
        self.env = textworld.start(game_path, request_infos)
        self.state = self.env.reset()   # начальное состояние

    def step(self, command: str):
        """Делает ход и возвращает текстовый ответ + признак завершения."""
        self.state, reward, done = self.env.step(command)
        return self.state['feedback'], self.state['admissible_commands'], done