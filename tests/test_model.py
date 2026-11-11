import pytest

from boiler_model import BoilerModel, BoilerState


def run(model, seconds, dt=1.0):
    for _ in range(int(seconds / dt)):
        model.step(dt)
    return model.state


def test_initial_conditions_match_task():
    s = BoilerModel().state
    assert s.level_pct == 0.0
    assert (s.hot_valve_pct, s.cold_valve_pct, s.outlet_valve_pct) == (50.0, 50.0, 100.0)


def test_unknown_controller_rejected():
    with pytest.raises(ValueError):
        BoilerModel(controller="fuzzy")


def test_tank_fills_when_outlet_closed():
    m = BoilerModel()
    m.set_outlet_valve(0)                  # слив закрывается за 5 с (travel time)
    # приток 2.5*0.5 + 3.0*0.5 = 2.75 л/с в бак 300 л -> ~0.9 %/с
    assert 45 < run(m, 60).level_pct < 60


def test_mixing_temperature_without_heater():
    # горячая 2.5 л/с при 90 °C + холодная 3.0 л/с при 10 °C -> ~46.4 °C
    m = BoilerModel()
    m.set_outlet_valve(0)
    s = run(m, 30)
    assert s.temperature_c == pytest.approx((2.5 * 90 + 3.0 * 10) / 5.5, abs=0.5)


def test_level_never_exceeds_100():
    m = BoilerModel()
    m.set_outlet_valve(0)
    m.set_hot_valve(100)
    m.set_cold_valve(100)
    levels = [m.step(1.0).level_pct for _ in range(300)]
    assert max(levels) <= 100.0


def test_overflow_interlock_closes_inlets():
    m = BoilerModel()
    m.set_outlet_valve(0)
    m.set_hot_valve(100)
    m.set_cold_valve(100)
    tripped = False
    for _ in range(300):
        s = m.step(1.0)
        if s.interlock_overflow:
            tripped = True
            assert s.hot_valve_effective_pct == 0 and s.cold_valve_effective_pct == 0
    assert tripped


def test_dry_heat_interlock_blocks_heater_in_empty_tank():
    m = BoilerModel()
    m.set_heater(100)
    s = m.step(1.0)
    assert s.interlock_dry_heat
    assert s.heater_effective_pct == 0.0


def test_heater_at_full_power_from_empty_tank_does_not_boil():
    """Регрессия: без блокировки сухого нагрева температура уходила в 130 °C."""
    m = BoilerModel()
    m.set_heater(100)
    temps = [m.step(1.0).temperature_c for _ in range(300)]
    assert max(temps) < BoilerModel.OVERTEMP_TRIP + 5


def test_auto_start_has_no_temperature_spike():
    """Регрессия: старт в AUTO из пустого бака давал скачок до ~108 °C."""
    for controller in ("p", "pid"):
        m = BoilerModel(controller=controller)
        m.set_level_auto(True)
        m.set_temperature_auto(True)
        temps = [m.step(1.0).temperature_c for _ in range(120)]
        assert max(temps) < 65, controller


def test_overtemp_interlock_switches_heater_off():
    state = BoilerState(level_pct=50.0, temperature_c=96.0, interlock_dry_heat=False)
    m = BoilerModel(state=state)
    m.set_outlet_valve(0)
    m.set_hot_valve(0)
    m.set_cold_valve(0)
    m.set_heater(100)
    s = m.step(1.0)
    assert s.interlock_overtemp
    assert s.heater_effective_pct == 0.0


def test_valve_travel_time_limits_speed():
    m = BoilerModel()
    m.set_valve_travel_time(10.0)          # 10 %/с
    m.set_hot_valve(100)
    s = m.step(1.0)
    assert s.hot_valve_actual_pct == pytest.approx(60.0)


@pytest.mark.parametrize("controller, max_error", [("pid", 0.2), ("p", 2.0)])
def test_auto_control_reaches_setpoints(controller, max_error):
    m = BoilerModel(controller=controller)
    m.set_level_setpoint(60)
    m.set_temperature_setpoint(60)
    m.set_level_auto(True)
    m.set_temperature_auto(True)
    s = run(m, 400)
    assert abs(s.level_pct - 60) < max_error
    assert abs(s.temperature_c - 60) < max_error


def test_pid_removes_static_error_of_p_controller():
    results = {}
    for controller in ("p", "pid"):
        m = BoilerModel(controller=controller)
        m.set_level_setpoint(60)
        m.set_temperature_setpoint(60)
        m.set_level_auto(True)
        m.set_temperature_auto(True)
        s = run(m, 400)
        results[controller] = abs(s.level_pct - 60) + abs(s.temperature_c - 60)
    assert results["pid"] < results["p"] / 5
