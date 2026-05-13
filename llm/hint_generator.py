import os
import logging
from typing import List
from dotenv import load_dotenv
from langchain_gigachat import GigaChat
from ollama import AsyncClient

load_dotenv()
logger = logging.getLogger("llm.hint_generator")

# Клиенты
gigachat_model = GigaChat(
    credentials=os.getenv("GIGACHAT_CREDENTIALS"),
    verify_ssl_certs=False,
    temperature=0.7,
    max_tokens=200,
)
ollama_client = AsyncClient(host="http://ollama:11434")
LOCAL_MODEL_NAME = os.getenv("LOCAL_MODEL_NAME", "qwen-custom")

def _build_prompt(feedback: str, admissible_commands: List[str]) -> str:
    if not admissible_commands:
        commands_str = "Нет доступных команд"
    else:
        commands_str = ", ".join(admissible_commands)
    return (
        "Ты — помощник в текстовой игре. На основе описания ситуации и списка доступных команд "
        "предложи игроку одно логичное действие и кратко объясни почему. Отвечай строго на русском языке, "
        "не более 3 предложений.\n\n"
        f"Описание: {feedback}\n"
        f"Доступные команды: {commands_str}\n\n"
        "Подсказка:"
    )

async def generate_hint_gigachat(feedback: str, admissible_commands: List[str]) -> str:
    """Генерация подсказки через GigaChat (большая LLM)."""
    prompt = _build_prompt(feedback, admissible_commands)
    try:
        response = await gigachat_model.ainvoke(prompt)
        return response.content.strip()
    except Exception as e:
        logger.exception("Ошибка генерации подсказки через GigaChat")
        return "Извините, большая языковая модель сейчас недоступна."

async def generate_hint_local(feedback: str, admissible_commands: List[str]) -> str:
    """Генерация подсказки через дообученную Qwen (малая LLM)."""
    prompt = _build_prompt(feedback, admissible_commands)
    try:
        response = await ollama_client.generate(
            model=LOCAL_MODEL_NAME,
            prompt=prompt,
            options={"temperature": 0.7, "num_predict": 200}
        )
        return response['response'].strip()
    except Exception as e:
        logger.exception("Ошибка генерации подсказки через локальную модель")
        return "Извините, малая языковая модель сейчас недоступна."