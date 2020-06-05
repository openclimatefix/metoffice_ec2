import json
import math
import pandas as pd

from metoffice_ec2.predict import load_irradiance_data, load_model, predict, predict_as_json_str


def test_predict():
    irradiance_dataset = load_irradiance_data("data/ukv/2020-06-04T090000Z-2020-06-04T170000Z-a45a52ba68fde0503738548205742728477e9db7.nc")
    model_df = load_model("model/predict_pv_yield_nwp.csv")
    predictions = predict(irradiance_dataset, model_df)
    assert predictions.at[0, "pv_yield_predicted"] > 0

    predictions_json_str = predict_as_json_str(irradiance_dataset, model_df)
    predictions_json = json.loads(predictions_json_str)
    prediction0 = predictions_json[0]
    assert prediction0["system_id"] == 973
    assert prediction0["easting"] == 445587
    assert prediction0["northing"] == 497235
    assert prediction0["time"] == 1591290000000
    assert prediction0["pv_yield_predicted"] > 0
