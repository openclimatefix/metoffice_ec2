#!/usr/bin/env python
import logging
import os
import time
from datetime import datetime, timezone

import boto3
import pandas as pd
import s3fs
import sentry_sdk
import geojson

from metoffice_ec2 import message, subset
from metoffice_ec2.timer import Timer
from metoffice_ec2.predict import (
    load_model,
    predict_as_geojson,
)

sentry_sdk.init(
    "https://4e4ddd1fa2aa4353bd904fa74852913e@o400768.ingest.sentry.io/5259484",
    release=f'metoffice_ec2@{os.getenv("RELEASE_VERSION", "UNSET")}',
    environment=os.getenv("SENTRY_ENV", "development"),
)

SQS_URL_DEFAULT = "https://sqs.eu-west-1.amazonaws.com/741607616921/uk-metoffice-nwp"
SQS_URL = os.getenv("SQS_URL", SQS_URL_DEFAULT)

DEST_BUCKET_DEFAULT = "uk-metoffice-nwp"
DEST_BUCKET = os.getenv("DEST_BUCKET", DEST_BUCKET_DEFAULT)

PREDICTIONS_BUCKET = "ocf-forecasting-data"

REGION = "eu-west-1"

WIND_HEIGHTS_METERS = [10, 50, 100, 150]  # Heights for wind power forecasting.

# DataFrame with index 'name' column 'height' (vertical levels in meters).
# 'height' should be a list of numbers.
# Remember to update infrastructure/inputs.tf as well, when modifying this.
PARAMS_TO_COPY = pd.DataFrame(
    [
        # For wind power forecasting:
        # Select wind_speed at 5 meters to help with PV forecasting.
        {"name": "wind_speed", "height": [5] + WIND_HEIGHTS_METERS},
        {"name": "wind_speed_of_gust", "height": WIND_HEIGHTS_METERS},
        {"name": "wind_from_direction", "height": WIND_HEIGHTS_METERS},
        # For solar PV power forecasting:
        {"name": "air_temperature", "height": [1.5]},
        # The following have no height parameter.
        {"name": "surface_temperature"},
        {"name": "surface_diffusive_downwelling_shortwave_flux_in_air"},
        {"name": "surface_direct_downwelling_shortwave_flux_in_air"},
        {"name": "surface_downwelling_shortwave_flux_in_air"},
    ]
).set_index("name")

# Approximate boundaries of UKV data from JASMIN, projected into
# MOGREPS-UK's Lambert Azimuthal Equal Area projection.
DEFAULT_GEO_BOUNDARY = {
    "north": 668920.2182797253,
    "south": -742783.9449856092,
    "east": 494613.07597373443,
    "west": -611744.985010537,
}


def configure_logger():
    log = logging.getLogger("metoffice_ec2")
    log.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    stream_handler.setFormatter(formatter)
    log.addHandler(stream_handler)

    # Attach our dependencies' loggers to our logger.
    logger_to_attach = logging.getLogger("s3fs")
    logger_to_attach.handlers = []
    logger_to_attach.parent = log
    logger_to_attach.setLevel(logging.INFO)

    return log


_LOG = configure_logger()


def load_subset_and_save_data(mo_message, height_meters, s3):
    timer = Timer()
    dataset = mo_message.load_netcdf()
    timer.tick("Opening xarray Dataset")
    dataset = subset.subset(dataset, height_meters, **DEFAULT_GEO_BOUNDARY)
    timer.tick("Subsetting")
    full_zarr_filename = subset.get_zarr_filename(dataset, DEST_BUCKET)
    try:
        subset.write_zarr_to_s3(dataset, full_zarr_filename, s3)
    except subset.FileExistsError as e:
        _LOG.warning(e)
    else:
        timer.tick("Compressing & writing Zarr file to S3")
        _LOG.info("SUCCESS! dest_url=%s", full_zarr_filename)
        run_inference(dataset)


def delete_message(sqs, sqs_message):
    receipt_handle = sqs_message["ReceiptHandle"]
    _LOG.info("Deleting message with ReceiptHandle=" + receipt_handle)
    sqs.delete_message(QueueUrl=SQS_URL, ReceiptHandle=receipt_handle)


def run_inference(dataset):
    variable_name = subset.get_variable_name(dataset)
    if variable_name != 'surface_downwelling_shortwave_flux_in_air':
        _LOG.info("Not running inference for variable %s", variable_name)
        return
    
    _LOG.info("Starting inference for variable %s", variable_name)
    
    # Load model
    model_df = load_model("model/predict_pv_yield_nwp.csv")

    # predict_as_geojson
    feature_collection = predict_as_geojson(dataset, model_df)

    # Save
    timestamp_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    s3 = boto3.client('s3')
    s3.put_object(
        Bucket=PREDICTIONS_BUCKET,
        Key=f'nwp/predictions_{timestamp_now}.geojson',
        Body=geojson.dumps(feature_collection, indent=4)
    )
    _LOG.info("SUCCESS! Saved predictions to bucket %s", PREDICTIONS_BUCKET)


def loop():
    # Re-create `sqs` and `s3` objects on every loop iteration
    # to prevent the script from using ever-increasing amounts of RAM!
    sqs = boto3.client("sqs", region_name=REGION)
    sqs_reply = sqs.receive_message(
        WaitTimeSeconds=20,
        QueueUrl=SQS_URL,
        MaxNumberOfMessages=10,
        AttributeNames=["ApproximateReceiveCount", "SentTimestamp"],
    )

    if "Messages" not in sqs_reply:
        _LOG.info("No more SQS messages!")
        return

    sqs_messages = sqs_reply["Messages"]
    num_messages = len(sqs_messages)
    _LOG.debug("{:d} sqs messages received".format(num_messages))
    if not sqs_messages:
        _LOG.info("No more SQS messages!")
        return

    s3 = s3fs.S3FileSystem(default_fill_cache=False, default_cache_type="none")
    for i, sqs_message in enumerate(sqs_messages):
        mo_message = message.MetOfficeMessage(sqs_message)
        _LOG.info("Loading SQS message %d/%d: %s", i + 1, num_messages, mo_message)

        if mo_message.is_wanted(PARAMS_TO_COPY):
            _LOG.info("Message is wanted!  Loading NetCDF file...")
            time_start = time.time()
            var_name = mo_message.message["name"]
            height_meters = PARAMS_TO_COPY["height"][var_name]
            try:
                load_subset_and_save_data(mo_message, height_meters, s3)
            except Exception as e:
                _LOG.exception(e)
            else:
                delete_message(sqs, sqs_message)

            time_end = time.time()
            _LOG.info("Message finished. Took %d seconds", time_end - time_start)
        else:
            _LOG.info("Message not wanted.")
            delete_message(sqs, sqs_message)


if __name__ == "__main__":
    _LOG.info("Starting scripts/ec2.py loop...")
    while True:
        loop()
