import os

import boto3
import pytest
from moto import mock_s3, mock_sqs

from scripts.ec2 import loop


def load_sns_message_from_file(path):
    with open(path, "r") as f:
        return f.read().replace("\n", "")


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture(scope="function")
def queue(aws_credentials):
    with mock_sqs():
        sqs = boto3.resource("sqs", region_name="eu-west-1")
        queue = sqs.create_queue(QueueName="uk-metoffice-nwp")
        os.environ["SQS_URL"] = queue.url

        yield queue


@pytest.fixture(scope="function")
def s3(aws_credentials):
    with mock_s3():
        yield boto3.resource("s3", region_name="eu-west-1")


def test_handles_no_new_sqs_messages(queue, caplog):
    loop()
    assert "No more SQS messages!" in caplog.text


test_input = [
    # ("var_name", "sns_message_filename", "netcdf_path", "netcdf_name", "dest_filename", "is_UKV"),
    (
        "air_temperature",
        "mogreps_uk_air_temperature_1-5m.json",
        "data/mogreps/MOGREPS-UK__air_temperature_2020-07-16T14:00:00Z.nc",
        "9a9d4d6889c99285ae4efa76802ccb0ccb96e3c4.nc",
        "MOGREPS-UK/air_temperature/2020/m07/d16/h14/MOGREPS-UK__air_temperature__2020-07-16T14__2020-07-17T00.zarr",
        False,
    ),
    (
        "surface_temperature",
        "mogreps_uk_surface_temperature.json",
        "data/mogreps/MOGREPS-UK__surface_temperature_2020-07-19T14:00:00Z.nc",
        "e9ba61dd6230adfb26353400a2128cd05ce98598.nc",
        "MOGREPS-UK/surface_temperature/2020/m07/d19/h14/MOGREPS-UK__surface_temperature__2020-07-19T14__2020-07-22T19.zarr",
        False,
    ),
    (
        "surface_downwelling_shortwave_flux_in_air",
        "mogreps_uk_surface_downwelling_shortwave_flux_in_air.json",
        "data/mogreps/MOGREPS-UK__surface_downwelling_shortwave_flux_in_air_2020-07-26T13:00:00Z.nc",
        "f69b4ba950e208f6c27894fc4276fac75d9bdd4d.nc",
        "MOGREPS-UK/surface_downwelling_shortwave_flux_in_air/2020/m07/d26/h13/MOGREPS-UK__surface_downwelling_shortwave_flux_in_air__2020-07-26T13__2020-07-27T17.zarr",
        False,
    ),
    (
        "surface_direct_downwelling_shortwave_flux_in_air",
        "mogreps_uk_surface_direct_downwelling_shortwave_flux_in_air.json",
        "data/mogreps/MOGREPS-UK__surface_direct_downwelling_shortwave_flux_in_air_2020-07-26T13:00:00Z.nc",
        "be0152287083bf7a49811d14e3f9844088c12933.nc",
        "MOGREPS-UK/surface_direct_downwelling_shortwave_flux_in_air/2020/m07/d26/h13/MOGREPS-UK__surface_direct_downwelling_shortwave_flux_in_air__2020-07-26T13__2020-07-28T01.zarr",
        False,
    ),
    (
        "surface_diffusive_downwelling_shortwave_flux_in_air",
        "mogreps_uk_surface_diffusive_downwelling_shortwave_flux_in_air.json",
        "data/ukv/MOGREPS-UK__surface_diffusive_downwelling_shortwave_flux_in_air_2020-07-26T15:00:00Z.nc",
        "9da5655d53f065b57f930abfe807039d25c38ac2.nc",
        "UKV/surface_diffusive_downwelling_shortwave_flux_in_air/2020/m07/d26/h15/UKV__surface_diffusive_downwelling_shortwave_flux_in_air__2020-07-26T15__2020-07-27T10.zarr",
        True,
    ),
]


@pytest.mark.parametrize(
    "var_name,sns_message_filename,netcdf_path,netcdf_name,dest_filename,is_UKV",
    test_input,
)
def test_handles_some_message_types(
    queue,
    s3,
    caplog,
    var_name,
    sns_message_filename,
    netcdf_path,
    netcdf_name,
    dest_filename,
    is_UKV,
):
    # MOCKING
    sns_message = load_sns_message_from_file(
        f"data/sns_messages/{sns_message_filename}"
    )
    queue.send_message(MessageBody=sns_message)

    BUCKET_NAME = (
        "aws-earth-mo-atmospheric-ukv-prd"
        if is_UKV
        else "aws-earth-mo-atmospheric-mogreps-uk-prd"
    )
    s3.Bucket(BUCKET_NAME).create()
    s3.Bucket(BUCKET_NAME).upload_file(netcdf_path, netcdf_name)

    output_bucket = s3.Bucket("uk-metoffice-nwp")
    output_bucket.create()

    # CODE TO BE TESTED
    loop()

    # ASSERTIONS
    assert "1 sqs messages received" in caplog.text
    assert f"Loading SQS message 1/1: var_name={var_name};" in caplog.text
    assert "Message is wanted!  Loading NetCDF file..." in caplog.text

    assert "Opening xarray Dataset" in caplog.text

    # Ensure no errors are logged
    for record in caplog.records:
        assert record.levelname != "ERROR"

    # Ensure Zarr got uploaded
    assert len(list(output_bucket.objects.filter(Prefix=dest_filename))) > 0

    assert "Message finished." in caplog.text
    assert "Deleting message" in caplog.text


not_wanted_messages = [
    # ("var_name", "sns_message_filename", "netcdf_path", "netcdf_name"),
    (
        "wind_speed_of_gust",
        "mogreps_uk_wind_speed_of_gust_10m.json",
        "data/mogreps/MOGREPS-UK__wind_speed_of_gust_2020-07-26T13:00:00Z.nc",
        "4ed0d74c22d80932711becbebf221dd769941a3b.nc",
    ),
    (
        "wind_from_direction",
        "mogreps_uk_wind_from_direction_10m.json",
        "data/mogreps/MOGREPS-UK__wind_from_direction_2020-07-26T13:00:00Z.nc",
        "10137efab23001a1ca5dbe7706c0cdce5373d4ba.nc",
    ),
    (
        "wind_speed",
        "mogreps_uk_wind_speed_10m.json",
        "data/mogreps/MOGREPS-UK__wind_speed_2020-07-26T13:00:00Z.nc",
        "322e3e40b90b05604152dfa5ad9698d618b61c19.nc",
    ),
]


@pytest.mark.parametrize(
    "var_name,sns_message_filename,netcdf_path,netcdf_name", not_wanted_messages
)
def test_handles_unwanted_messages(
    queue, s3, caplog, var_name, sns_message_filename, netcdf_path, netcdf_name,
):
    # MOCKING
    sns_message = load_sns_message_from_file(
        f"data/sns_messages/{sns_message_filename}"
    )
    queue.send_message(MessageBody=sns_message)

    # CODE TO BE TESTED
    loop()

    # ASSERTIONS
    assert "1 sqs messages received" in caplog.text
    assert f"Loading SQS message 1/1: var_name={var_name};" in caplog.text
    assert "Message not wanted." in caplog.text
    assert "Deleting message" in caplog.text

    # Ensure no errors are logged
    for record in caplog.records:
        assert record.levelname != "ERROR"
