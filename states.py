from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    confirming_name = State()
    waiting_for_car = State()
    waiting_for_car_passengers = State()
    waiting_for_role = State()

class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()
    waiting_for_broadcast_role = State()


class AccusationStates(StatesGroup):
    waiting_for_suspect = State()
    waiting_for_evidence_1 = State()
    waiting_for_evidence_2 = State()
    waiting_for_rationale = State()
