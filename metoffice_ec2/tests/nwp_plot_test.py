from metoffice_ec2.nwp_plot import find_zarr, filename_for_plot, extract_wind_from_direction, plot_xarray_data_array
import imghdr
from fsspec.implementations.local import LocalFileSystem
from pathlib import Path
import xarray as xr
from zarr.storage import DirectoryStore


def test_local_plot_pipeline(tmp_path):
    height = 100.0
    fs = LocalFileSystem()

    # Find the first Zarr input file in the "data/mogreps" directory
    listing = find_zarr(fs, "data/mogreps")
    assert len(listing) == 1
    input_file = listing[0]
    assert input_file.endswith("MOGREPS-UK__wind_from_direction__2020-03-15T15__2020-03-16T07.zarr")

    # Create a suitable filename for the output plot png file
    output_file = filename_for_plot(str(tmp_path), input_file, qualifier=f"_height{height}")
    assert output_file.endswith("MOGREPS-UK__wind_from_direction__2020-03-15T15__2020-03-16T07_height100.0.png")

    # Extract wind from direction array
    store = DirectoryStore(input_file)
    ds = xr.open_zarr(store)
    da = extract_wind_from_direction(ds, height)
    assert da.values.shape == (706, 553)

    # Plot the data and check the output file is a png
    with open(output_file, "wb") as file:
        plot_xarray_data_array(ds, da, file)
    assert Path(output_file).is_file()
    assert imghdr.what(output_file) == "png"
