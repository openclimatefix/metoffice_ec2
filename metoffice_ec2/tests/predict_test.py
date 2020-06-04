import math
import pandas as pd

from metoffice_ec2.predict import load_model, predict, predict_as_json


def test_predict():
    irradiance_df = pd.DataFrame(data={
        "system_id": [2, 973, 2829],
        "dswrf": [10.0, 250.0, 100.0]
    })
    model_df = load_model("model/predict_pv_yield_nwp.csv")

    predictions = predict(irradiance_df, model_df)
    
    system_2_yield = predictions.at[0, "pv_yield_predicted"]
    assert math.isnan(system_2_yield)

    system_973_yield = predictions.at[1, "pv_yield_predicted"]
    assert system_973_yield > 0

    system_2829_yield = predictions.at[2, "pv_yield_predicted"]
    assert system_2829_yield > 0

    predictions_json = predict_as_json(irradiance_df, model_df)

    assert predictions_json == """[
    {
        "system_id":2,
        "pv_yield_predicted":null
    },
    {
        "system_id":973,
        "pv_yield_predicted":1187.0
    },
    {
        "system_id":2829,
        "pv_yield_predicted":518.7
    }
]"""
