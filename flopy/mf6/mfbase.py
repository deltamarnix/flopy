"""Base classes for Modflow 6"""

import inspect
import traceback
from collections.abc import Iterable
from enum import Enum
from typing import Union


# internal handled exceptions
class MFInvalidTransientBlockHeaderException(Exception):
    """
    Exception occurs when parsing a transient block header
    """


class ReadAsArraysException(Exception):
    """
    Exception occurs when loading ReadAsArrays package as non-ReadAsArrays
    package.
    """


# external exceptions for users
class FlopyException(Exception):
    """
    General FloPy exception
    """

    def __init__(self, error, location=""):
        self.message = error
        super().__init__(f"{error} ({location})")


class StructException(Exception):
    """
    Exception with the package file structure
    """

    def __init__(self, error, location):
        self.message = error
        super().__init__(f"{error} ({location})")


class MFDataException(Exception):
    """
    Exception with MODFLOW data.  Exception includes detailed error
    information.
    """

    def __init__(
        self,
        model=None,
        package=None,
        path=None,
        current_process=None,
        data_element=None,
        method_caught_in=None,
        org_type=None,
        org_value=None,
        org_traceback=None,
        message=None,
        debug=None,
        mfdata_except=None,
    ):
        if mfdata_except is not None and isinstance(
            mfdata_except, MFDataException
        ):
            # copy constructor - copying values from original exception
            self.model = mfdata_except.model
            self.package = mfdata_except.package
            self.current_process = mfdata_except.current_process
            self.data_element = mfdata_except.data_element
            self.path = mfdata_except.path
            self.messages = mfdata_except.messages
            self.debug = mfdata_except.debug
            self.method_caught_in = mfdata_except.method_caught_in
            self.org_type = mfdata_except.org_type
            self.org_value = mfdata_except.org_value
            self.org_traceback = mfdata_except.org_traceback
            self.org_tb_string = mfdata_except.org_tb_string
        else:
            self.messages = []
            if mfdata_except is not None and (
                isinstance(mfdata_except, StructException)
                or isinstance(mfdata_except, FlopyException)
            ):
                self.messages.append(mfdata_except.message)
            self.model = None
            self.package = None
            self.current_process = None
            self.data_element = None
            self.path = None
            self.debug = False
            self.method_caught_in = None
            self.org_type = None
            self.org_value = None
            self.org_traceback = None
            self.org_tb_string = None
        # override/assign any values that are not none
        if model is not None:
            self.model = model
        if package is not None:
            self.package = package
        if current_process is not None:
            self.current_process = current_process
        if data_element is not None:
            self.data_element = data_element
        if path is not None:
            self.path = path
        if message is not None:
            self.messages.append(message)
        if debug is not None:
            self.debug = debug
        if method_caught_in is not None:
            self.method_caught_in = method_caught_in
        if org_type is not None:
            self.org_type = org_type
        if org_value is not None:
            self.org_value = org_value
        if org_traceback is not None:
            self.org_traceback = org_traceback
        self.org_tb_string = traceback.format_exception(
            self.org_type, self.org_value, self.org_traceback
        )
        # build error string
        error_message = "An error occurred in "
        if self.data_element is not None and self.data_element != "":
            error_message += f'data element "{self.data_element}" '
        if self.model is not None and self.model != "":
            error_message += f'model "{self.model}" '
        error_message += (
            f'package "{self.package}". The error occurred while '
            f'{self.current_process} in the "{self.method_caught_in}" method.'
        )
        if len(self.messages) > 0:
            error_message += "\nAdditional Information:\n"
            error_message += "\n".join(
                f"({idx}) {msg}" for (idx, msg) in enumerate(self.messages, 1)
            )
        super().__init__(error_message)


class VerbosityLevel(Enum):
    """Determines how much information FloPy writes to the console"""

    quiet = 1
    normal = 2
    verbose = 3


class PackageContainerType(Enum):
    """Determines whether a package container is a simulation, model, or
    package."""

    simulation = 1
    model = 2
    package = 3


class ExtFileAction(Enum):
    """Defines what to do with external files when the simulation or model's
    path change."""

    copy_all = 1
    copy_none = 2
    copy_relative_paths = 3


class PackageContainer:
    """
    Base class for any class containing packages.

    Parameters
    ----------
    simulation_data : SimulationData
        The simulation's SimulationData object
    name : str
        Name of the package container object

    Attributes
    ----------
    package_type_dict : dictionary
        Dictionary of packages by package type
    package_name_dict : dictionary
        Dictionary of packages by package name

    """

    modflow_packages = []
    packages_by_abbr = {}
    modflow_models = []
    models_by_type = {}

    def __init__(self, simulation_data):
        self._simulation_data = simulation_data
        self.packagelist = []
        self.package_type_dict = {}
        self.package_name_dict = {}
        self.package_filename_dict = {}

    @staticmethod
    def package_list():
        """Static method that returns the list of available packages.
        For internal FloPy use only, not intended for end users.

        Returns a list of MFPackage subclasses
        """
        # all packages except "group" classes
        package_list = []
        for abbr, package in sorted(PackageContainer.packages_by_abbr.items()):
            # don't store packages "group" classes
            if not abbr.endswith("packages"):
                package_list.append(package)
        return package_list

    @staticmethod
    def package_factory(package_type: str, model_type: str):
        """Static method that returns the appropriate package type object based
        on the package_type and model_type strings.  For internal FloPy use
        only, not intended for end users.

        Parameters
        ----------
            package_type : str
                Type of package to create
            model_type : str
                Type of model that package is a part of

        Returns
        -------
            package : MFPackage subclass

        """
        package_abbr = f"{model_type}{package_type}"
        factory = PackageContainer.packages_by_abbr.get(package_abbr)
        if factory is None:
            package_utl_abbr = f"utl{package_type}"
            factory = PackageContainer.packages_by_abbr.get(package_utl_abbr)
        return factory

    @staticmethod
    def model_factory(model_type):
        """Static method that returns the appropriate model type object based
        on the model_type string. For internal FloPy use only, not intended
        for end users.

        Parameters
        ----------
            model_type : str
                Type of model that package is a part of

        Returns
        -------
            model : MFModel subclass

        """
        return PackageContainer.models_by_type.get(model_type)

    @staticmethod
    def get_module_val(module, item, attrb):
        """Static method that returns a python class module value.  For
        internal FloPy use only, not intended for end users."""
        value = getattr(module, item)
        # verify this is a class
        if (
            not value
            or not inspect.isclass(value)
            or not hasattr(value, attrb)
        ):
            return None
        return value

    @property
    def package_dict(self):
        """Returns a copy of the package name dictionary."""
        return self.package_name_dict.copy()

    @property
    def package_names(self):
        """Returns a list of package names."""
        return list(self.package_name_dict.keys())

    def add_package(self, package):
        # put in packages list and update lookup dictionaries
        self.packagelist.append(package)
        if package.package_name is not None:
            self.package_name_dict[package.package_name.lower()] = package
        if package.filename is not None:
            self.package_filename_dict[package.filename.lower()] = package
        if package.package_type not in self.package_type_dict:
            self.package_type_dict[package.package_type.lower()] = []
        self.package_type_dict[package.package_type.lower()].append(package)

    def remove_package(self, package):
        if package in self.packagelist:
            self.packagelist.remove(package)
        if (
            package.package_name is not None
            and package.package_name.lower() in self.package_name_dict
        ):
            del self.package_name_dict[package.package_name.lower()]
        if (
            package.filename is not None
            and package.filename.lower() in self.package_filename_dict
        ):
            del self.package_filename_dict[package.filename.lower()]
        if package.package_type.lower() in self.package_type_dict:
            package_list = self.package_type_dict[package.package_type.lower()]
            if package in package_list:
                package_list.remove(package)
            if len(package_list) == 0:
                del self.package_type_dict[package.package_type.lower()]

        # collect keys of items to be removed from main dictionary
        items_to_remove = []
        for key in self._simulation_data.mfdata:
            is_subkey = True
            for pitem, ditem in zip(package.path, key):
                if pitem != ditem:
                    is_subkey = False
                    break
            if is_subkey:
                items_to_remove.append(key)

        # remove items from main dictionary
        for key in items_to_remove:
            del self._simulation_data.mfdata[key]

    def _rename_package(self, package, new_name):
        # fix package_name_dict key
        if (
            package.package_name is not None
            and package.package_name.lower() in self.package_name_dict
        ):
            del self.package_name_dict[package.package_name.lower()]
        self.package_name_dict[new_name.lower()] = package
        # get keys to fix in main dictionary
        main_dict = self._simulation_data.mfdata
        items_to_fix = []
        for key in main_dict:
            is_subkey = True
            for pitem, ditem in zip(package.path, key):
                if pitem != ditem:
                    is_subkey = False
                    break
            if is_subkey:
                items_to_fix.append(key)

        # fix keys in main dictionary
        for key in items_to_fix:
            new_key = (
                package.path[:-1] + (new_name,) + key[len(package.path) - 1 :]
            )
            main_dict[new_key] = main_dict.pop(key)

    def get_package(self, name=None, type_only=False, name_only=False):
        """
        Finds a package by package name, package key, package type, or partial
        package name. returns either a single package, a list of packages,
        or None.

        Parameters
        ----------
        name : str
            Name or type of the package, 'my-riv-1, 'RIV', 'LPF', etc.
        type_only : bool
            Search for package by type only
        name_only : bool
            Search for package by name only

        Returns
        -------
        pp : Package object

        """
        if name is None:
            return self.packagelist[:]

        # search for full package name
        if name.lower() in self.package_name_dict and not type_only:
            return self.package_name_dict[name.lower()]

        # search for package type
        if name.lower() in self.package_type_dict and not name_only:
            if len(self.package_type_dict[name.lower()]) == 0:
                return None
            elif len(self.package_type_dict[name.lower()]) == 1:
                return self.package_type_dict[name.lower()][0]
            else:
                return self.package_type_dict[name.lower()]

        # search for file name
        if name.lower() in self.package_filename_dict and not type_only:
            return self.package_filename_dict[name.lower()]

        # search for partial and case-insensitive package name
        if not type_only:
            for pp in self.packagelist:
                if pp.package_name is not None:
                    # get first package of the type requested
                    package_name = pp.package_name.lower()
                    if len(package_name) > len(name):
                        package_name = package_name[0 : len(name)]
                    if package_name.lower() == name.lower():
                        return pp

        return None

    @staticmethod
    def _load_only_dict(load_only):
        if load_only is None:
            return None
        if isinstance(load_only, dict):
            return load_only
        if not isinstance(load_only, Iterable):
            raise FlopyException(
                "load_only must be iterable or None. "
                'load_only value of "{}" is '
                "invalid".format(load_only)
            )
        load_only_dict = {}
        for item in load_only:
            load_only_dict[item.lower()] = True
        return load_only_dict

    @staticmethod
    def _in_pkg_list(pkg_list, pkg_type, pkg_name):
        if pkg_type is not None:
            pkg_type = pkg_type.lower()
        if pkg_name is not None:
            pkg_name = pkg_name.lower()
        if pkg_type in pkg_list or pkg_name in pkg_list:
            return True

        # split to make cases like "gwf6-gwf6" easier to process
        pkg_type = pkg_type.split("-")
        try:
            # if there is a number on the end of the package try
            # excluding it
            int(pkg_type[0][-1])
            for key in pkg_list.keys():
                key = key.split("-")
                if len(key) == len(pkg_type):
                    matches = True
                    for key_item, pkg_item in zip(key, pkg_type):
                        if pkg_item[0:-1] != key_item and pkg_item != key_item:
                            matches = False
                    if matches:
                        return True
        except ValueError:
            return False
        return False
