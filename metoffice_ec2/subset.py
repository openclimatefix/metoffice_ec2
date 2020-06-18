import xarray as xr
import numcodecs
import pandas as pd
import os
import lzma
from typing import Optional, List, Union, MutableMapping
import pathlib
import s3fs


def subset(
    dataset: xr.Dataset,
    height_meters: Optional[List[int]] = None,
    north: Optional[float] = None,
    east: Optional[float] = None,
    south: Optional[float] = None,
    west: Optional[float] = None,
) -> xr.Dataset:

    if height_meters is not None:
        dataset = dataset.sel(height=height_meters)

    return dataset.loc[
        dict(
            projection_x_coordinate=slice(west, east),
            projection_y_coordinate=slice(south, north),
        )
    ]


def get_variable_name(dataset: xr.Dataset) -> str:
    var_name = list(dataset.data_vars.keys())[0]
    return str(var_name)


def get_zarr_filename(dataset: xr.Dataset, dest_path: str) -> str:
    forecast_ref_time = dataset.forecast_reference_time.values
    forecast_ref_time = pd.Timestamp(forecast_ref_time)
    valid_time = dataset.time.values
    valid_time = pd.Timestamp(valid_time)
    var_name = get_variable_name(dataset)
    model_name = dataset.attrs["title"].split()[0]

    path = os.path.join(
        dest_path, model_name, var_name, forecast_ref_time.strftime("%Y/m%m/d%d/h%H")
    )

    basename = "{model_name}__{var_name}__{ref_time}__{valid_time}.zarr".format(
        model_name=model_name,
        var_name=var_name,
        ref_time=forecast_ref_time.strftime("%Y-%m-%dT%H"),
        valid_time=valid_time.strftime("%Y-%m-%dT%H"),
    )

    return os.path.join(path, basename)


class FileExistsError(Exception):
    pass


def prep_and_check_s3(full_zarr_filename: str, s3: s3fs.S3FileSystem):
    if s3.exists(full_zarr_filename):
        raise FileExistsError(
            "Destination already exists: {}".format(full_zarr_filename)
        )

    zarr_path, _ = os.path.split(full_zarr_filename)
    s3.makedirs(path=zarr_path)


def write_zarr(
    dataset: xr.Dataset,
    store: Union[MutableMapping, str, pathlib.Path],
    preset: int = 9,
    dist: int = 4,
    mode: str = "w",
    consolidated: bool = True,
) -> xr.backends.ZarrStore:
    lzma_filters = [
        dict(id=lzma.FILTER_DELTA, dist=dist),
        dict(id=lzma.FILTER_LZMA2, preset=preset),
    ]
    compressor = numcodecs.LZMA(filters=lzma_filters, format=lzma.FORMAT_RAW)
    var_name = get_variable_name(dataset)
    encoding = {var_name: {"compressor": compressor}}
    return dataset.to_zarr(
        store, mode=mode, consolidated=consolidated, encoding=encoding
    )


def write_zarr_to_s3(
    dataset: xr.Dataset,
    full_zarr_filename: str,
    s3: s3fs.S3FileSystem,
    **write_zarr_kwargs
) -> xr.backends.ZarrStore:

    prep_and_check_s3(full_zarr_filename, s3)
    store = s3fs.S3Map(root=full_zarr_filename, s3=s3, check=False, create=True)
    return write_zarr(dataset, store, **write_zarr_kwargs)
