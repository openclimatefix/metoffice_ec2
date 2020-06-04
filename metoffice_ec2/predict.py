import pandas as pd


def load_model(path: str) -> pd.DataFrame:
    """Load a model produced by the predict_pv_yield_nwp module"""
    model_df = pd.read_csv(path)
    return model_df


def predict(irradiance_df: pd.DataFrame, model_df: pd.DataFrame) -> pd.DataFrame:
    """Predict PV yield for PV systems with irradiance values in irradiance_df"""
    df = pd.merge(irradiance_df, model_df, how="left")
    df["pv_yield_predicted"] = df["slope"] * df["dswrf"] + df["intercept"]
    df = df[["system_id", "pv_yield_predicted"]]
    return df


def predict_as_json(irradiance_df: pd.DataFrame, model_df: pd.DataFrame) -> str:
    """Predict PV yield for PV systems with irradiance values in irradiance_df, and return a JSON string"""
    return predict(irradiance_df, model_df).to_json(orient="records", double_precision=1, indent=4)
