import os
# import logging
# import json

import pytest
import boto3
from moto import mock_s3, mock_sqs

from scripts.ec2 import loop


def load_sqs_message_from_file(path):
    with open(path, 'r') as f:
        return f.read().replace('\n', '')


# @pytest.fixture(scope='function', params=)
# def sqs_message():


@pytest.fixture(scope='function')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'


@pytest.fixture(scope='function')
def queue(aws_credentials):
    with mock_sqs():
        sqs = boto3.resource("sqs", region_name="eu-west-1")
        queue = sqs.create_queue(QueueName='uk-metoffice-nwp')
        os.environ['SQS_URL'] = queue.url

        yield queue


@pytest.fixture(scope='function')
def s3(aws_credentials):
    with mock_s3():
        yield boto3.resource('s3', region_name='eu-west-1')


def test_handles_no_new_sqs_messages(queue, caplog):
    loop()
    assert "No more SQS messages!" in caplog.text


test_input = [
    ("var_name", "sns_message_filename", "netcdf_path", "netcdf_name", "dest_filename"),
    ("air_temperature", "mogreps_uk_air_temperature_1-5m.json", "data/mogreps/MOGREPS-UK__air_temperature_2020-07-16T14:00:00Z.nc", "9a9d4d6889c99285ae4efa76802ccb0ccb96e3c4.nc", "MOGREPS-UK/air_temperature/2020/m07/d16/h14/MOGREPS-UK__air_temperature__2020-07-16T14__2020-07-17T00.zarr"),
    ("wind_speed", "mogreps_uk_wind_speed_multilevel.json", "data/mogreps/MOGREPS-UK__wind_speed_2020-07-19T14:00:00Z.nc", "0afc5a13dc1d9bbcd3a56103a93cea076375db56", "MOGREPS-UK/wind_speed/2020/m07/d19/h14/MOGREPS-UK__wind_speed__2020-07-19T14__2020-07-23T01.zarr")
]


def test_handles_air_temperature_message(queue, s3, caplog):
    # MOCKING
    mogreps_uk_air_temperature_1_5m = load_sqs_message_from_file("data/sns_messages/mogreps_uk_air_temperature_1-5m.json")
    queue.send_message(MessageBody=mogreps_uk_air_temperature_1_5m)

    BUCKET_NAME = 'aws-earth-mo-atmospheric-mogreps-uk-prd'
    s3.Bucket(BUCKET_NAME).create()
    s3.Bucket(BUCKET_NAME).upload_file('data/mogreps/MOGREPS-UK__air_temperature_2020-07-16T14:00:00Z.nc', '9a9d4d6889c99285ae4efa76802ccb0ccb96e3c4.nc')

    output_bucket = s3.Bucket("uk-metoffice-nwp")
    output_bucket.create()

    # CODE TO BE TESTED
    loop()

    # ASSERTIONS
    assert "1 sqs messages received" in caplog.text
    assert "Loading SQS message 1/1: var_name=air_temperature;" in caplog.text
    assert "Message is wanted!  Loading NetCDF file..." in caplog.text

    assert "Opening xarray Dataset" in caplog.text

    # Ensure no errors are logged
    # for record in caplog.records:
    #     assert record.levelname != "ERROR"

    for my_bucket_object in output_bucket.objects.all():
        print(my_bucket_object)

    # Ensure Zarr got uploaded
    key = 'MOGREPS-UK/air_temperature/2020/m07/d16/h14/MOGREPS-UK__air_temperature__2020-07-16T14__2020-07-17T00.zarr'
    assert len(list(output_bucket.objects.filter(Prefix=key))) > 0

    assert "Message finished." in caplog.text
