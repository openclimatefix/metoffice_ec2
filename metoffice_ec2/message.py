import hashlib
import json
import os
from typing import Dict

import boto3
import netCDF4
import numpy as np
import pandas as pd

import xarray as xr


class MetOfficeMessage:
    """Represents the MetOffice-specific portion of the SNS message.


    Attributes:
        message: A Dict of Met Office message details.
        sqs_message: A Dict representing the SQS message.
    """

    def __init__(self, sqs_message: Dict):
        """
        Args:
          sqs_message: An AWS Simple Queue Service message.
        """
        body_json_string = sqs_message["Body"]
        _check_md5(body_json_string, sqs_message["MD5OfBody"])
        body_dict = json.loads(body_json_string)
        self.message = json.loads(body_dict["Message"])
        self.sqs_message = sqs_message

    def sqs_message_sent_timestamp(self) -> pd.Timestamp:
        """Returns the time the message was sent to the queue."""
        attributes = self.sqs_message["Attributes"]
        sent_timestamp = float(attributes["SentTimestamp"]) / 1000
        return pd.Timestamp.utcfromtimestamp(sent_timestamp)

    def sqs_approx_receive_count(self) -> int:
        """Returns the approx number of times a message has been received from
        the queue but not deleted."""
        attributes = self.sqs_message["Attributes"]
        return int(attributes["ApproximateReceiveCount"])

    def height_meters(self) -> np.ndarray:
        try:
            height_str = self.message["height"]
        except KeyError:
            return np.array([])
        height_list = height_str.split(" ")
        height_array = np.array(height_list).astype(float)
        return height_array

    def is_multi_level(self):
        """Return True if this message is about an NWP with multiple
        vertical levels."""
        return len(self.height_meters()) > 1

    def is_wanted(self, nwp_params: pd.DataFrame, max_receive_count: int = 10) -> bool:
        """Returns True if this message describes an NWP we want.

        Args:
          nwp_params: The Numerical Weather Prediction parameters we want.
              A Pandas DataFrame, one row per NWP field we want.  Must have
              index set to 'name' (for the NWP field name).  Can have
              a 'height' column.
          max_receive_count: If this message has been received more than
            `max_receive_count` times, then we don't want this message.
        """
        if self.sqs_approx_receive_count() > max_receive_count:
            return False

        height_meters = set(self.height_meters())
        for var_name, row in nwp_params.iterrows():
            if self.message["name"] != var_name:
                continue
            row = row.dropna()
            if "height" in row:
                if not height_meters.issuperset(row["height"]):
                    continue
            return True
        return False

    def source_url(self) -> str:
        """Return the URL for the NetCDF file described by this message."""
        source_bucket = self.message["bucket"]
        source_key = self.message["key"]
        return os.path.join(source_bucket, source_key)

    def load_netcdf(self) -> xr.Dataset:
        """Opens the NetCDF described by this message."""
        boto_s3 = boto3.client("s3")
        get_obj_response = boto_s3.get_object(
            Bucket=self.message["bucket"], Key=self.message["key"]
        )
        netcdf_bytes = get_obj_response["Body"].read()
        # Adapted from
        # https://github.com/pydata/xarray/issues/1075#issuecomment-373541528
        nc4_ds = netCDF4.Dataset("MetOffice", memory=netcdf_bytes)
        store = xr.backends.NetCDF4DataStore(nc4_ds)
        return xr.open_dataset(store, engine="netcdf4")

    def object_size_mb(self) -> float:
        """Return the object size in megabytes."""
        return self.message["object_size"] / 1e6

    def __repr__(self) -> str:
        string = ""
        string += "var_name={}; ".format(self.message["name"])
        string += "is_multi_level={}; ".format(self.is_multi_level())
        string += "object_size={:,.1f} MB; ".format(self.object_size_mb())
        string += "model={}; ".format(self.message["model"])
        string += "SQS_message_sent_timestamp={}; ".format(
            self.sqs_message_sent_timestamp().isoformat()
        )
        string += "forecast_reference_time={}; ".format(
            self.message["forecast_reference_time"]
        )
        string += "created_time={}; ".format(self.message["created_time"])
        string += "time={}; ".format(self.message["time"])
        string += "source_url={}; ".format(self.source_url())
        string += "SQS_approx_receive_count={}; ".format(
            self.sqs_approx_receive_count()
        )
        string += "SQS_message_ID={}".format(self.sqs_message["MessageId"])
        return string


def _check_md5(text: str, md5_of_body: str):
    text_utf8 = text.encode("utf-8")
    md5 = hashlib.md5(text_utf8)
    if md5.hexdigest() != md5_of_body:
        raise RuntimeError("MD5 checksum does not match!")
