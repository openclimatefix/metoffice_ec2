#!/usr/bin/python
from nwp_subset import message, subset
from nwp_subset.timer import Timer
import s3fs
import xarray as xr
import boto3
import logging
import io

SQS_URL = 'https://sqs.eu-west-2.amazonaws.com/144427043691/mogreps-uk-and-ukv'

REGION = 'eu-west-2'

DEST_BUCKET = 'metoffice-nwp'

PARAMS_TO_COPY = [
    'wind_speed',
    'wind_speed_of_gust',
    'wind_from_direction']

SUBSET_PARAMS = {
    'height_meters': [10, 50, 100, 150],

    # Approximate boundaries of UKV data from JASMIN, projected into
    # MOGREPS-UK's Lambert Azimuthal Equal Area projection.
    'north': 668920.2182797253,
    'south': -742783.9449856092,
    'east': 494613.07597373443,
    'west': -611744.985010537}


def configure_logger():
    log = logging.getLogger('nwp_subset')
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


def main():
    sqs = boto3.client('sqs', region_name=REGION)
    s3 = s3fs.S3FileSystem(default_fill_cache=False, default_cache_type='none')
    while True:
        sqs_reply = sqs.receive_message(
            QueueUrl=SQS_URL, MaxNumberOfMessages=10,
            AttributeNames=['ApproximateReceiveCount', 'SentTimestamp'])

        sqs_messages = sqs_reply['Messages']
        num_messages = len(sqs_messages)
        _LOG.debug('{:d} sqs messages received'.format(num_messages))
        if not sqs_messages:
            _LOG.debug('No more SQS messages!')
            break

        for i, sqs_message in enumerate(sqs_messages):
            mo_message = message.MetOfficeMessage(sqs_message)
            _LOG.info(
                'Loading SQS message %d/%d: %s', i+1, num_messages, mo_message)

            delete_message = True
            if mo_message.is_wanted(PARAMS_TO_COPY):
                _LOG.info('Message is wanted!  Loading NetCDF file...')
                try:
                    load_subset_and_save_data(mo_message, s3)
                except Exception as e:
                    _LOG.exception(e)
                    delete_message = False
            else:
                _LOG.info('Message not wanted.')

            if delete_message:
                receipt_handle = sqs_message['ReceiptHandle']
                _LOG.info(
                    'Deleting message with ReceiptHandle=' + receipt_handle)
                sqs.delete_message(
                    QueueUrl=SQS_URL, ReceiptHandle=receipt_handle)



if __name__ == '__main__':
    main()
