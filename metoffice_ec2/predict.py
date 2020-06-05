import pandas as pd
import xarray as xr


def load_model(path: str) -> pd.DataFrame:
    """Load a model produced by the predict_pv_yield_nwp module"""
    model_df = pd.read_csv(path)
    return model_df


def load_irradiance_data(path: str) -> xr.Dataset:
    """Load the NWP irradiance data"""
    return xr.open_dataset(path, engine="netcdf4")


def predict(irradiance_dataset: xr.Dataset, model_df: pd.DataFrame) -> pd.DataFrame:
    """Predict PV yield for PV systems with irradiance values in irradiance_dataset"""

    # Get the PV system locations, and interpolate the irradiance data to those locations
    easting = xr.DataArray(model_df["easting"].values, coords=[model_df["system_id"].values], dims="system_id")
    northing = xr.DataArray(model_df["northing"].values, coords=[model_df["system_id"].values], dims="system_id")
    nwp_interp = irradiance_dataset.interp(projection_x_coordinate=easting, projection_y_coordinate=northing)

    # Convert to a dataframe
    irradiance_df = nwp_interp["surface_downwelling_shortwave_flux_in_air"].to_dataframe()

    # Merge with the model datadrame and use the linear regression parameters
    # to predict a PV yield for each system
    df = pd.merge(irradiance_df, model_df, how="left", left_index=True, right_on="system_id")
    df["pv_yield_predicted"] = df["slope"] * df["surface_downwelling_shortwave_flux_in_air"] + df["intercept"]
    df = df[["system_id", "easting", "northing", "time", "pv_yield_predicted"]]
    return df


def predict_as_json_str(irradiance_dataset: xr.Dataset, model_df: pd.DataFrame) -> str:
    """Predict PV yield for PV systems with irradiance values in irradiance_dataset, and return a JSON string"""
    return predict(irradiance_dataset, model_df).to_json(orient="records", double_precision=1, indent=4)
