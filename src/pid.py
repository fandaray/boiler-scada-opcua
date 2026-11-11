"""
ПИД-регулятор с защитой от интегрального насыщения (anti-windup).

Основа - решение golubeva (студент): если выход упёрся в ограничение
(клапан полностью открыт или закрыт), последнее приращение интеграла
откатывается, чтобы интеграл не "накапливал" ошибку впустую и регулятор
не давал большого перерегулирования после выхода из насыщения.
"""


class PIDController:
    def __init__(self, kp: float, ki: float, kd: float,
                 output_min: float = 0.0, output_max: float = 100.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self._integral = 0.0
        self._prev_error: float | None = None

    def reset(self):
        """Сбрасывает интеграл и память о предыдущей ошибке (при включении AUTO)."""
        self._integral = 0.0
        self._prev_error = None

    def compute(self, setpoint: float, measured_value: float, dt: float) -> float:
        error = setpoint - measured_value

        self._integral += error * dt
        if self._prev_error is None or dt <= 0:
            derivative = 0.0
        else:
            derivative = (error - self._prev_error) / dt
        self._prev_error = error

        raw = self.kp * error + self.ki * self._integral + self.kd * derivative
        out = max(self.output_min, min(self.output_max, raw))

        # anti-windup: выход в насыщении - откатываем приращение интеграла
        if out != raw:
            self._integral -= error * dt
        return out
