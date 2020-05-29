#!/usr/bin/env python
from metoffice_ec2 import message, subset
from metoffice_ec2.timer import Timer
import s3fs
import boto3
import logging
import os
import time

SQS_URL_DEFAULT = 'https://sqs.eu-west-1.amazonaws.com/741607616921/uk-metoffice-nwp'
SQS_URL = os.getenv('SQS_URL', SQS_URL_DEFAULT)

DEST_BUCKET_DEFAULT = 'uk-metoffice-nwp'
DEST_BUCKET = os.getenv('DEST_BUCKET', SQS_URL_DEFAULT)

REGION = 'eu-west-1'

# Remember to update infrastructure/inputs.tf as well, when modifying this
PARAMS_TO_COPY = [
    'wind_speed',
    'wind_speed_of_gust',
    'wind_from_direction',
    'air_temperature',
    'surface_diffusive_downwelling_shortwave_flux_in_air',
    'surface_direct_downwelling_shortwave_flux_in_air',
    'surface_downwelling_shortwave_flux_in_air',
    'surface_temperature']

SUBSET_PARAMS = {
    'height_meters': [10, 50, 100, 150],

    # Approximate boundaries of UKV data from JASMIN, projected into
    # MOGREPS-UK's Lambert Azimuthal Equal Area projection.
    'north': 668920.2182797253,
    'south': -742783.9449856092,
    'east': 494613.07597373443,
    'west': -611744.985010537}


def configure_logger():
    log = logging.getLogger('metoffice_ec2')
    log.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    log.addHandler(stream_handler)

    # Attach our dependencies' loggers to our logger.
    logger_to_attach = logging.getLogger('s3fs')
    logger_to_attach.handlers = []
    logger_to_attach.parent = log
    logger_to_attach.setLevel(logging.INFO)

    return log


_LOG = configure_logger()


def load_subset_and_save_data(mo_message, s3):
    timer = Timer()
    dataset = mo_message.load_netcdf()
    timer.tick('Opening xarray Dataset')
    dataset = subset.subset(dataset, **SUBSET_PARAMS)
    timer.tick('Subsetting')
    full_zarr_filename = subset.get_zarr_filename(dataset, DEST_BUCKET)
    try:
        subset.write_zarr_to_s3(dataset, full_zarr_filename, s3)
    except subset.FileExistsError as e:
        _LOG.warning(e)
    else:
        timer.tick('Compressing & writing Zarr file to S3')
        _LOG.info('SUCCESS! dest_url=%s', full_zarr_filename)


def delete_message(sqs, sqs_message):
    receipt_handle = sqs_message['ReceiptHandle']
    _LOG.info('Deleting message with ReceiptHandle=' + receipt_handle)
    sqs.delete_message(QueueUrl=SQS_URL, ReceiptHandle=receipt_handle)


def loop():
    # Re-create `sqs` and `s3` objects on every loop iteration
    # to prevent the script from using ever-increasing amounts of RAM!
    sqs = boto3.client('sqs', region_name=REGION)
    sqs_reply = sqs.receive_message(
        WaitTimeSeconds=20,
        QueueUrl=SQS_URL, MaxNumberOfMessages=10,
        AttributeNames=['ApproximateReceiveCount', 'SentTimestamp'])

    if 'Messages' not in sqs_reply:
        _LOG.info('No more SQS messages!')
        return

    sqs_messages = sqs_reply['Messages']
    num_messages = len(sqs_messages)
    _LOG.debug('{:d} sqs messages received'.format(num_messages))
    if not sqs_messages:
        _LOG.info('No more SQS messages!')
        return

    s3 = s3fs.S3FileSystem(default_fill_cache=False, default_cache_type='none')
    for i, sqs_message in enumerate(sqs_messages):
        mo_message = message.MetOfficeMessage(sqs_message)
        _LOG.info(
            'Loading SQS message %d/%d: %s', i+1, num_messages, mo_message)

        if mo_message.is_wanted(PARAMS_TO_COPY):
            _LOG.info('Message is wanted!  Loading NetCDF file...')
            time_start = time.time()
            try:
                load_subset_and_save_data(mo_message, s3)
            except Exception as e:
                _LOG.exception(e)
            else:
                delete_message(sqs, sqs_message)

            time_end = time.time()
            _LOG.info('Took %d seconds', time_end-time_start)
        else:
            _LOG.info('Message not wanted.')
            delete_message(sqs, sqs_message)


if __name__ == '__main__':
    _LOG.info('Starting scripts/ec2.py loop...')
    while True:
        loop()
