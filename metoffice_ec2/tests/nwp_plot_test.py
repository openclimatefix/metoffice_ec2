import imghdr
from pathlib import Path

import pytest
from zarr.storage import ZipStore

import xarray as xr
from metoffice_ec2.nwp_plot import (
    extract_wind_from_direction,
    filename_for_plot,
    plot_xarray_data_array,
)


@pytest.mark.skip(reason="Coastline data download often times out")
def test_local_plot_pipeline(tmp_path):
    height = 100.0

    input_file = "data/mogreps/MOGREPS-UK__wind_from_direction__2020-03-15T15__2020-03-16T07.zarr.zip"

    # Create a suitable filename for the output plot png file
    output_file = filename_for_plot(
        str(tmp_path), input_file, qualifier=f"_height{height}"
    )
    assert output_file.endswith(
        "MOGREPS-UK__wind_from_direction__2020-03-15T15__2020-03-16T07_height100.0.png"
    )

    # Extract wind from direction array
    store = ZipStore(input_file)
    ds = xr.open_zarr(store)
    da = extract_wind_from_direction(ds, height)
    assert da.values.shape == (706, 553)

    # Plot the data and check the output file is a png
    with open(output_file, "wb") as file:
        plot_xarray_data_array(ds, da, file)
    assert Path(output_file).is_file()
    assert imghdr.what(output_file) == "png"
