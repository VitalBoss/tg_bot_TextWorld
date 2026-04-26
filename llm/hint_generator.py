# llm/hint_generator.py
import os
from typing import List
from langchain_gigachat import GigaChat
from dotenv import load_dotenv

load_dotenv()

# Инициализируем один экземпляр модели на всё приложение
model = GigaChat(
    credentials=os.getenv("GIGACHAT_CREDENTIALS"),
    verify_ssl_certs=False,
    temperature=0.01,
    max_tokens=200,
)

async def generate_hint(feedback: str, admissible_commands: List[str]) -> str:
    """
    Принимает текущее описание мира и список доступных команд.
    Возвращает короткую подсказку на русском языке.
    """
    if not admissible_commands:
        commands_str = "Нет доступных команд"
    else:
        commands_str = ", ".join(admissible_commands)
        
    prompt = (
        "Ты — помощник в текстовой игре. На основе описания ситуации и списка доступных команд "
        "предложи игроку одно логичное действие и кратко объясни почему. Отвечай строго на русском языке, "
        "не более 3 предложений.\n\n"
        f"Описание: {feedback}\n"
        f"Доступные команды: {commands_str}\n\n"
        "Подсказка:"
    )
    
    # Асинхронный вызов модели
    response = await model.ainvoke(prompt)
    return response.strip()