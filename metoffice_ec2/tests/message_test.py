import json
from pathlib import Path

import pandas as pd
import pytest
from metoffice_ec2.message import MetOfficeMessage


def _load_message(filename: str) -> MetOfficeMessage:
    base_path = Path(__file__).parent
    file_path = base_path / ".." / ".." / "data" / "sqs_messages" / filename
    with open(file_path) as fp:
        sqs_message = json.load(fp)
    message = MetOfficeMessage(sqs_message)
    return message


@pytest.fixture
def multi_level_wind_message() -> MetOfficeMessage:
    return _load_message("mogreps_uk_wind_speed_multilevel.json")


@pytest.fixture
def single_level_wind_message() -> MetOfficeMessage:
    return _load_message("mogreps_uk_wind_speed_10m.json")


def test_multi_level_wind(multi_level_wind_message):
    assert multi_level_wind_message.is_multi_level()
    assert (
        str(multi_level_wind_message)
        == "var_name=wind_speed; is_multi_level=True; object_size=104.6 MB; model=mo-atmospheric-mogreps-uk-prd; SQS_message_sent_timestamp=2020-05-29T22:43:50.383000; forecast_reference_time=2020-05-28T20:00:00Z; created_time=2020-05-28T22:39:18Z; time=2020-06-01T22:00:00Z; source_url=aws-earth-mo-atmospheric-mogreps-uk-prd/f721851d2a5487bf08d1f8ac0ff2c9c05bb02892.nc; SQS_approx_receive_count=1; SQS_message_ID=2f868f8c-a695-4654-99fc-7b6f73cdbd93"
    )


def test_single_level_wind(single_level_wind_message):
    assert not single_level_wind_message.is_multi_level()
    assert (
        str(single_level_wind_message)
        == "var_name=wind_speed; is_multi_level=False; object_size=3.2 MB; model=mo-atmospheric-mogreps-uk-prd; SQS_message_sent_timestamp=2020-05-29T22:36:29.372000; forecast_reference_time=2020-05-28T20:00:00Z; created_time=2020-05-28T22:26:08Z; time=2020-06-01T08:00:00Z; source_url=aws-earth-mo-atmospheric-mogreps-uk-prd/fd0640a8c5570a63424e07d2ca4f30b1d4c00692.nc; SQS_approx_receive_count=1; SQS_message_ID=6ad940c2-41bd-4fd2-bad6-76cd7a741ad8"
    )


def test_is_wanted_multi_level_wind(multi_level_wind_message):
    wanted = pd.DataFrame([{"name": "wind_speed", "height": [50]}]).set_index("name")
    assert multi_level_wind_message.is_wanted(wanted)

    wanted2 = pd.DataFrame([{"name": "wind_speed", "height": [5, 10, 50]}]).set_index(
        "name"
    )
    assert multi_level_wind_message.is_wanted(wanted2)

    not_wanted1 = pd.DataFrame([{"name": "wind_speed", "height": [123]}]).set_index(
        "name"
    )
    assert not multi_level_wind_message.is_wanted(not_wanted1)

    not_wanted2 = pd.DataFrame([{"name": "wind_direction", "height": [50]}]).set_index(
        "name"
    )
    assert not multi_level_wind_message.is_wanted(not_wanted2)


def test_is_wanted_single_level_wind(single_level_wind_message):
    wanted = pd.DataFrame([{"name": "wind_speed", "height": [10]}]).set_index("name")
    assert single_level_wind_message.is_wanted(wanted)

    not_wanted = pd.DataFrame([{"name": "wind_speed", "height": [50]}]).set_index(
        "name"
    )
    assert not single_level_wind_message.is_wanted(not_wanted)
