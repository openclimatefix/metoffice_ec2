from datetime import datetime, timezone
import math

import pandas as pd
from geojson import Feature, FeatureCollection, Point
import xarray as xr


def load_model(path: str) -> pd.DataFrame:
    """Load a model produced by the predict_pv_yield_nwp module"""
    model_df = pd.read_csv(path)
    return model_df


def load_irradiance_data(path: str) -> xr.Dataset:
    """Load the NWP irradiance data"""
    if ".zarr" in path:
        return xr.open_zarr(path)
    return xr.open_dataset(path, engine="netcdf4")


def predict(irradiance_dataset: xr.Dataset, model_df: pd.DataFrame) -> pd.DataFrame:
    """Predict PV yield for PV systems with irradiance values in irradiance_dataset"""

    # Get the PV system locations, and interpolate the irradiance data to those locations
    easting = xr.DataArray(
        model_df["easting"].values,
        coords=[model_df["system_id"].values],
        dims="system_id",
    )
    northing = xr.DataArray(
        model_df["northing"].values,
        coords=[model_df["system_id"].values],
        dims="system_id",
    )
    # MOGREPS has multiple realizations (UKV doesn't)
    if "realization" in irradiance_dataset:
        # just get the first realization
        irradiance_dataset = irradiance_dataset.isel(realization=0)
    nwp_interp = irradiance_dataset.interp(
        projection_x_coordinate=easting, projection_y_coordinate=northing
    )

    # Convert to a dataframe
    irradiance_df = nwp_interp[
        "surface_downwelling_shortwave_flux_in_air"
    ].to_dataframe()

    # Merge with the model dataframe and use the linear regression parameters
    # to predict a PV yield for each system
    df = pd.merge(
        irradiance_df, model_df, how="left", left_index=True, right_on="system_id"
    )
    df["pv_yield_predicted"] = (
        df["slope"] * df["surface_downwelling_shortwave_flux_in_air"] + df["intercept"]
    )
    df = df[["system_id", "longitude", "latitude", "time", "pv_yield_predicted"]]
    return df


def predict_as_geojson(
    irradiance_dataset: xr.Dataset, model_df: pd.DataFrame
) -> FeatureCollection:
    """Predict PV yield for PV systems with irradiance values in irradiance_dataset, and return a GeoJSON FeatureCollection"""
    rows = predict(irradiance_dataset, model_df).to_dict("records")
    feature_collection = FeatureCollection([_to_geojson_feature(row) for row in rows], properties={
        "forecastCreationTime": datetime.now(timezone.utc).isoformat()
    })
    return feature_collection


def _to_geojson_feature(row):
    return Feature(
        geometry=Point((row["longitude"], row["latitude"])),
        properties={
            "system_id": row["system_id"],
            "forecastTime": row["time"].isoformat(),
            # TODO(#50): Remove the nan check once issue is fixed
            "pv_yield_predicted": None if math.isnan(row["pv_yield_predicted"]) else row["pv_yield_predicted"],
        },
    )
