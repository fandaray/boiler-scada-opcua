"""
Сравнение П-регуляторов исходной сборки и ПИ(Д)-регуляторов на модели бойлера.

Сценарий: пустой бак, AUTO уровня (60 %) и температуры (60 °C);
на 450-й секунде уставки меняются на 40 % и 75 °C.

Запуск (из корня репозитория):
    pip install matplotlib
    python scripts/compare_controllers.py
Результат: docs/controllers.png и таблица метрик в консоли.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from boiler_model import BoilerModel  # noqa: E402

DURATION_S = 900
STEP_AT_S = 450
PHASES = [  # (начало, конец, уставка уровня, уставка температуры)
    (0, STEP_AT_S, 60.0, 60.0),
    (STEP_AT_S, DURATION_S, 40.0, 75.0),
]
TOLERANCE = 1.0  # коридор установления: ±1 % уровня и ±1 °C


def simulate(controller: str) -> dict:
    m = BoilerModel(controller=controller)
    m.set_level_auto(True)
    m.set_temperature_auto(True)
    level, temp, heater = [], [], []
    for t in range(DURATION_S):
        for start, _, level_sp, temp_sp in PHASES:
            if t == start:
                m.set_level_setpoint(level_sp)
                m.set_temperature_setpoint(temp_sp)
        s = m.step(1.0)
        level.append(s.level_pct)
        temp.append(s.temperature_c)
        heater.append(s.heater_effective_pct)
    return {"level": level, "temp": temp, "heater": heater}


def settling_time(series, setpoint):
    """Через сколько секунд сигнал входит в коридор ±TOLERANCE и больше не выходит."""
    for i in range(len(series)):
        if all(abs(v - setpoint) <= TOLERANCE for v in series[i:]):
            return i
    return None


def metrics(series, start, end, setpoint, previous):
    seg = series[start:end]
    steady = sum(seg[-60:]) / 60
    overshoot = (max(seg) - setpoint) if setpoint >= previous else (setpoint - min(seg))
    return {
        "static_error": round(abs(setpoint - steady), 2),
        "overshoot": round(max(overshoot, 0.0), 2),
        "settling_s": settling_time(seg, setpoint),
    }


def main():
    runs = {name: simulate(name) for name in ("p", "pid")}

    print(f"{'регулятор':<10}{'величина':<13}{'фаза':<6}{'стат. ошибка':>14}{'перерегул.':>12}{'установл., с':>14}")
    for name, r in runs.items():
        for key, label, idx in (("level", "уровень, %", 2), ("temp", "темп., °C", 3)):
            prev = 0.0
            for n, phase in enumerate(PHASES, 1):
                m = metrics(r[key], phase[0], phase[1], phase[idx], prev)
                prev = phase[idx]
                settle = m["settling_s"] if m["settling_s"] is not None else "—"
                print(f"{name.upper():<10}{label:<13}{n:<6}{m['static_error']:>14}{m['overshoot']:>12}{settle:>14}")
    print(f"Макс. температура: P {max(runs['p']['temp']):.1f} °C, PID {max(runs['pid']['temp']):.1f} °C")

    t = range(DURATION_S)
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    styles = {"p": dict(color="#d62728", lw=1.4, label="П-регулятор (исходный)"),
              "pid": dict(color="#1f77b4", lw=1.8, label="ПИ-регулятор")}
    for name, r in runs.items():
        axes[0].plot(t, r["level"], **styles[name])
        axes[1].plot(t, r["temp"], **styles[name])
        axes[2].plot(t, r["heater"], **styles[name])
    for ax, idx in ((axes[0], 2), (axes[1], 3)):
        for start, end, *sps in PHASES:
            ax.hlines(sps[idx - 2], start, end, colors="grey", linestyles=":", lw=1.2)
    axes[0].set_ylabel("Уровень, %")
    axes[1].set_ylabel("Температура, °C")
    axes[2].set_ylabel("Мощность ТЭНа, %")
    axes[2].set_xlabel("Время, с")
    axes[0].set_title("П против ПИ: уставки (пунктир) 60 % / 60 °C, на 450 с — 40 % / 75 °C")
    axes[0].legend(loc="lower right")
    for ax in axes:
        ax.grid(alpha=0.3)
    fig.tight_layout()
    out = ROOT / "docs" / "controllers.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=140)
    print(f"График: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
