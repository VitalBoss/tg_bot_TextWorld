import textworld

request_infos = textworld.EnvInfos(
    # Основное состояние игры (динамические)
    admissible_commands=True,      # Все допустимые команды в текущем состоянии
    description=True,              # Описание текущей комнаты (look)
    feedback=True,                 # Ответ игры на предыдущую команду
    intermediate_reward=True,      # Промежуточное вознаграждение за прогресс
    inventory=True,                # Содержимое инвентаря игрока
    last_action=True,              # Последнее выполненное действие
    last_command=True,             # Последняя выполненная команда
    location=True,                 # Текущее местоположение игрока
    lost=True,                     # Флаг проигрыша
    moves=True,                    # Количество сделанных ходов
    policy_commands=True,          # Последовательность команд к победе
    score=True,                    # Текущий счет
    won=True,                      # Флаг выигрыша
    
    # Информация о мире (статическая/динамическая)
    facts=True,                    # Все истинные факты о мире
    
    # Метаданные игры (статические)
    command_templates=True,        # Шаблоны команд, которые понимает игра
    entities=True,                 # Все сущности в игре
    fail_facts=True,               # Факты, приводящие к провалу квестов
    game=True,                     # Сериализованная версия игры
    max_score=True,                # Максимально возможный счет
    objective=True,                # Текстовая цель игры
    possible_admissible_commands=True, # Все возможные допустимые команды
    possible_commands=True,        # Все возможные команды
    typed_entities=True,           # Все сущности с их типами
    verbs=True,                    # Все глаголы, которые понимает игра
    win_facts=True,                # Факты, приводящие к успеху квестов
    
    # Дополнительная информация
    extras=[],                     # Список дополнительных метаданных (не булево!)
)