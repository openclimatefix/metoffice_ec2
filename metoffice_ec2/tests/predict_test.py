import json
import math
import pandas as pd

from metoffice_ec2.predict import load_irradiance_data, load_model, predict, predict_as_geojson


def test_predict():
    irradiance_dataset = load_irradiance_data("data/ukv/2020-06-04T090000Z-2020-06-04T170000Z-a45a52ba68fde0503738548205742728477e9db7.nc")
    model_df = load_model("model/predict_pv_yield_nwp.csv")
    predictions = predict(irradiance_dataset, model_df)
    assert predictions.at[0, "pv_yield_predicted"] > 0

    feature_collection = predict_as_geojson(irradiance_dataset, model_df)
    feature0 = feature_collection["features"][0]
    assert feature0["geometry"]["coordinates"] == [-1.299834, 54.3686]
    assert feature0["properties"]["system_id"] == 973
    assert feature0["properties"]["time"] == "2020-06-04T17:00:00"
    assert feature0["properties"]["pv_yield_predicted"] > 0

    # Dump to file
    # import geojson
    # with open("predictions_2020-06-04T17.geojson", 'w') as f:
    #     geojson.dump(feature_collection, f, indent=4)
