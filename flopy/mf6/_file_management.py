import copy
import inspect
import os
import sys
import traceback
import warnings
from pathlib import Path
from shutil import copyfile
from typing import Union

from flopy.mf6.mfbase import MFDataException


class MFFilePath:
    """Class that stores a single file path along with the associated model
    name."""

    def __init__(self, file_path, model_name):
        self.file_path = file_path
        self.model_name = {model_name: 0}

    def isabs(self):
        return os.path.isabs(self.file_path)


class MFFileMgmt:
    """
    Class containing MODFLOW path data

    Parameters
    ----------

    path : str or PathLike
        Path on disk to the simulation

    Attributes
    ----------

    model_relative_path : dict
        Dictionary of relative paths to each model folder

    """

    def __init__(self, path: Union[str, os.PathLike]):
        self._sim_path: Union[str, os.PathLike] = ""
        self.set_sim_path(path)

        # keys:fully pathed filenames, vals:FilePath instances
        self.existing_file_dict = {}
        # keys:filenames,vals:instance name

        self.model_relative_path = {}

        self._last_loaded_sim_path = None
        self._last_loaded_model_relative_path = {}

    def copy_files(self, copy_relative_only=True):
        """Copy files external to updated path.

        Parameters
        ----------
            copy_relative_only : bool
                Only copy files with relative paths.
        """
        num_files_copied = 0
        if self._last_loaded_sim_path is not None:
            for mffile_path in self.existing_file_dict.values():
                path_old = self.resolve_path(
                    mffile_path, last_loaded_path=True
                )
                if os.path.isfile(path_old) and (
                    not mffile_path.isabs() or not copy_relative_only
                ):
                    path_new = self.resolve_path(mffile_path)
                    if path_old != path_new:
                        new_folders = os.path.split(path_new)[0]
                        if not os.path.exists(new_folders):
                            os.makedirs(new_folders)
                        try:
                            copyfile(path_old, path_new)
                        except:
                            type_, value_, traceback_ = sys.exc_info()
                            raise MFDataException(
                                self.structure.get_model(),
                                self.structure.get_package(),
                                self._path,
                                "appending data",
                                self.structure.name,
                                inspect.stack()[0][3],
                                type_,
                                value_,
                                traceback_,
                                None,
                                self._simulation_data.debug,
                            )

                        num_files_copied += 1
        return num_files_copied

    def strip_model_relative_path(self, model_name: str, path: str) -> str:
        """Strip out the model relative path part of `path`."""
        if model_name not in self.model_relative_path:
            return path

        model_rel_path = Path(self.model_relative_path[model_name])
        if (
            model_rel_path is None
            or model_rel_path.is_absolute()
            or not any(str(model_rel_path))
            or str(model_rel_path) == os.curdir
        ):
            return path

        try:
            ret_path = Path(path).relative_to(model_rel_path)
        except ValueError:
            warnings.warn(
                f"Could not strip model relative path from {path}: {traceback.format_exc()}"
            )
            ret_path = Path(path)

        return str(ret_path.as_posix())

    @staticmethod
    def unique_file_name(file_name, lookup):
        """Generate a unique file name."""
        num = 0
        while MFFileMgmt._build_file(file_name, num) in lookup:
            num += 1
        return MFFileMgmt._build_file(file_name, num)

    @staticmethod
    def _build_file(file_name, num) -> str:
        file, ext = os.path.splitext(file_name)
        if ext:
            return f"{file}_{num}{ext}"
        else:
            return f"{file}_{num}"

    def set_last_accessed_path(self):
        """Set the last accessed simulation path to the current simulation
        path."""
        self._last_loaded_sim_path = self._sim_path
        self.set_last_accessed_model_path()

    def set_last_accessed_model_path(self) -> None:
        """Set the last accessed model path to the current model path."""
        for key, item in self.model_relative_path.items():
            self._last_loaded_model_relative_path[key] = copy.deepcopy(item)

    def get_model_path(self, key: str, last_loaded_path: bool = False) -> str:
        """Returns the model working path for the model `key`.

        Parameters
        ----------
        key : str
            Model name whose path flopy will retrieve
        last_loaded_path : bool
            Get the last path loaded by FloPy which may not be the most
            recent path.

        Returns
        -------
            model path : str

        """
        if last_loaded_path:
            return os.path.join(
                self._last_loaded_sim_path,
                self._last_loaded_model_relative_path[key],
            )
        elif key in self.model_relative_path:
            return os.path.join(self._sim_path, self.model_relative_path[key])
        else:
            return self._sim_path

    def get_sim_path(
        self, last_loaded_path: bool = False
    ) -> Union[str, os.PathLike, None]:
        """Get the simulation path."""
        if last_loaded_path:
            return self._last_loaded_sim_path
        else:
            return self._sim_path

    def add_ext_file(self, file_path, model_name: str) -> None:
        """Add an external file to the path list."""
        if file_path in self.existing_file_dict:
            if model_name not in self.existing_file_dict[file_path].model_name:
                self.existing_file_dict[file_path].model_name[model_name] = 0
        else:
            new_file_path = MFFilePath(file_path, model_name)
            self.existing_file_dict[file_path] = new_file_path

    def set_sim_path(self, path: Union[str, os.PathLike]) -> None:
        """
        Set the file path to the simulation files.

        Parameters
        ----------
        path : str or PathLike
            Path to simulation folder

        Returns
        -------
        None

        Examples
        --------
        self.simulation_data.mfdata.set_sim_path('path/to/workspace')
        """
        # expand tildes and ensure _sim_path is absolute
        self._sim_path = Path(path).expanduser().absolute()

    def resolve_path(
        self,
        path,
        *,
        last_loaded_path: bool = False,
        move_abs_paths: bool = False,
    ) -> str:
        """Resolve a simulation or model path."""
        if isinstance(path, MFFilePath):
            file_path = str(path.file_path)
        else:
            file_path = str(path)

        # remove quote characters from file path
        file_path = file_path.replace("'", "")
        file_path = file_path.replace('"', "")

        if os.path.isabs(file_path):
            # path is an absolute path
            if move_abs_paths:
                return self.get_sim_path(last_loaded_path)
            else:
                return file_path
        else:
            # path is a relative path
            return os.path.join(self.get_sim_path(last_loaded_path), file_path)
