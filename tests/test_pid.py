import pytest

from pid import PIDController


def test_proportional_only():
    pid = PIDController(kp=2.0, ki=0.0, kd=0.0, output_min=-100, output_max=100)
    assert pid.compute(10, 7, dt=1.0) == pytest.approx(6.0)


def test_output_is_clamped():
    pid = PIDController(kp=100.0, ki=0.0, kd=0.0, output_min=0, output_max=100)
    assert pid.compute(50, 0, dt=1.0) == 100
    assert pid.compute(0, 50, dt=1.0) == 0


def test_integral_accumulates():
    pid = PIDController(kp=0.0, ki=1.0, kd=0.0, output_min=-100, output_max=100)
    pid.compute(1, 0, dt=1.0)
    assert pid.compute(1, 0, dt=1.0) == pytest.approx(2.0)


def test_anti_windup_stops_integral_in_saturation():
    pid = PIDController(kp=0.0, ki=1.0, kd=0.0, output_min=0, output_max=10)
    for _ in range(100):           # ошибка 50, выход упёрся в 10
        pid.compute(50, 0, dt=1.0)
    # после смены знака ошибки регулятор быстро уходит из насыщения
    assert pid.compute(0, 50, dt=1.0) < 10


def test_reset_clears_state():
    pid = PIDController(kp=0.0, ki=1.0, kd=1.0, output_min=-100, output_max=100)
    pid.compute(5, 0, dt=1.0)
    pid.reset()
    assert pid.compute(1, 0, dt=1.0) == pytest.approx(1.0)   # без D-скачка и старого интеграла
