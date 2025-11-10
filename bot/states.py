from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """Состояния при регистрации"""
    waiting_for_subscription = State()  # Ожидание подписки на канал
    choosing_address_method = State()  # Выбор способа ввода адреса
    entering_street = State()  # Ввод улицы
    entering_house = State()  # Ввод номера дома
    choosing_queue = State()  # Ручной выбор черги (если адрес не найден)
    confirming_location = State()  # Підтвердження адреси з геолокації (НОВОЕ!)
    selecting_from_similar = State()  # ← ДОБАВЬ ЭТУ СТРОКУ




class SettingsStates(StatesGroup):
    """Состояния в настройках"""
    choosing_setting = State()  # Выбор настройки
    changing_address = State()  # Изменение адреса
    changing_warning_times = State()  # Изменение времени предупреждений


class ReportStates(StatesGroup):
    """Состояния при отправке краудрепорта"""
    choosing_report_type = State()  # Выбор типа (есть свет / нет света)
    confirming_address = State()  # Подтверждение адреса


class CrowdReportStates(StatesGroup):
    """Стейти для краудрепортів про світло"""
    waiting_for_status = State()  # Очікування вибору статусу (є світло / немає світла)