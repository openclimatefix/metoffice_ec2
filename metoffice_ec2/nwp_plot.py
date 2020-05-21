import cartopy.crs as ccrs
import fsspec
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Any, IO, List, Union
import xarray as xr


def find_zarr(fs: fsspec.spec.AbstractFileSystem, directory: str, suffix: str = ".zarr") -> List[str]:
    """Find all the zarr files in a filesystem directory"""
    return [dir for dir in fs.listdir(directory, detail=False) if dir.endswith(suffix)]


def filename_for_plot(directory, zarr_path: str, qualifier: str = "") -> str:
    """Get a suitable output filename for a plot produced from a Zarr path"""
    basename = Path(zarr_path).stem.replace(".zarr", "") # handle ".zarr" and ".zarr.zip"
    path = Path(directory, f"{basename}{qualifier}.png")
    return str(path)


def extract_wind_from_direction(dataset: xr.Dataset, height) -> Union[xr.DataArray, xr.Dataset]:
    """Get the wind from direction data array for a given height"""
    return dataset.isel(realization=0).sel(height=height)["wind_from_direction"]


def plot_xarray_data_array(dataset: xr.Dataset, da: xr.DataArray, file: IO[Any]) -> None:
    """Create an image plot for a data array"""
    central_latitude = dataset.lambert_azimuthal_equal_area.latitude_of_projection_origin[0]
    central_longitude = dataset.lambert_azimuthal_equal_area.longitude_of_projection_origin[0]
    mogreps_crs = ccrs.LambertAzimuthalEqualArea(
        central_latitude=central_latitude,
        central_longitude=central_longitude)

    plt.figure()
    ax = plt.axes(projection=ccrs.OSGB(approx=True))
    ax.coastlines(resolution="10m")
    da.plot(ax=ax, add_colorbar=False, transform=mogreps_crs, cmap='viridis')
    ax.gridlines(draw_labels=True)

    plt.savefig(file, format="png")
