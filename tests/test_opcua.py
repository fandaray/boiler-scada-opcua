"""Интеграционный тест: настоящий OPC UA сервер на свободном порту + клиент."""
import socket

import pytest

import config
from opc_server import BoilerOpcUaServer
from opcua_client import BoilerOpcUaClient, validate_value


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server_and_client():
    port = free_port()
    server = BoilerOpcUaServer(endpoint=f"opc.tcp://127.0.0.1:{port}/boiler/server/")
    server.server.start()
    client = BoilerOpcUaClient(endpoint=f"opc.tcp://127.0.0.1:{port}/boiler/server/")
    client.connect()
    yield server, client
    client.disconnect()
    server.server.stop()


def tick(server, n=1):
    """Один цикл сервера без sleep: уставки -> шаг модели -> публикация."""
    for _ in range(n):
        server._apply_setpoints_from_space()
        server.model.step(config.MODEL_STEP_SECONDS)
        server._publish_state()


def test_client_reads_all_tags(server_and_client):
    server, client = server_and_client
    tick(server)
    values = client.get_all_values()
    assert values["outlet_valve"] == 100.0
    assert values["interlock_dry_heat"] is True
    assert 0 <= values["level"] <= 100


def test_setpoint_written_by_client_reaches_model(server_and_client):
    server, client = server_and_client
    client.set_value("outlet_valve", 0.0)
    tick(server, 20)
    assert server.model.state.outlet_valve_pct == 0.0
    assert client.get_value("level") > 10


def test_read_only_tag_cannot_be_written(server_and_client):
    _, client = server_and_client
    with pytest.raises(ValueError):
        client.set_value("level", 50.0)


@pytest.mark.parametrize("tag, raw, expected", [
    ("hot_valve", 150, 100.0),
    ("hot_valve", -5, 0.0),
    ("temperature_setpoint", 200, 95.0),
    ("valve_travel_time", 0, 0.1),
    ("level_auto", 1, True),
])
def test_validate_value_clamps(tag, raw, expected):
    assert validate_value(tag, raw) == expected
