# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""Target data structure."""
import json
import os
import re
import warnings

import tvm._ffi
from tvm._ffi import register_func as _register_func
from tvm.runtime import Object, convert
from tvm.runtime.container import String
from tvm.ir.container import Map

from . import _ffi_api


@tvm._ffi.register_object
class TargetKind(Object):
    """Kind of a compilation target"""

    @property
    def options(self):
        """Returns the dict of available option names and types"""
        return dict(_ffi_api.ListTargetKindOptions(self))

    @staticmethod
    def options_from_name(kind_name: str):
        """Returns the dict of available option names and types from a name of TargetKind"""
        return dict(_ffi_api.ListTargetKindOptionsFromName(kind_name))


@tvm._ffi.register_object
class Target(Object):
    """Target device information, use through TVM API.

    Note
    ----
    You can create target using the constructor or the following functions

    - :py:func:`tvm.target.arm_cpu` create arm_cpu target
    - :py:func:`tvm.target.cuda` create CUDA target
    - :py:func:`tvm.target.rocm` create ROCM target
    - :py:func:`tvm.target.mali` create Mali target
    - :py:func:`tvm.target.intel_graphics` create Intel Graphics target
    """

    def __init__(self, target, host=None):
        """Construct a TVM target object from
        1) Raw target string
        2) Target config dict
        3) Target tag

        Parameters
        ----------
        target : Union[str, Dict[str, Any]]
            Can be one of a literal target string, a json string describing
            a configuration, or a dictionary of configuration options.
            When using a dictionary or json string to configure target, the
            possible values are:

            kind :  str (required)
                Which codegen path to use, for example 'llvm' or 'cuda'.
            keys : List of str (optional)
                A set of strategies that can be dispatched to. When using
                "kind=opencl" for example, one could set keys to ["mali", "opencl", "gpu"].
            device : str (optional)
                A single key that corresponds to the actual device being run on.
                This will be effectively appended to the keys.
            libs : List of str (optional)
                The set of external libraries to use. For example ['cblas', 'mkl'].
            system-lib : bool (optional)
                If True, build a module that contains self registered functions.
                Useful for environments where dynamic loading like dlopen is banned.
            mcpu : str (optional)
                The specific cpu being run on. Serves only as an annotation.
            model : str (optional)
                An annotation indicating what model a workload came from.
            runtime : str (optional)
                An annotation indicating which runtime to use with a workload.
            mtriple : str (optional)
                The llvm triplet describing the target, for example "arm64-linux-android".
            mattr : List of str (optional)
                The llvm features to compile with, for example ["+avx512f", "+mmx"].
            mfloat-abi : str (optional)
                An llvm setting that is one of 'hard' or 'soft' indicating whether to use
                hardware or software floating-point operations.
            mabi : str (optional)
                An llvm setting. Generate code for the specified ABI, for example "lp64d".
            host : Union[str, Dict[str, Any]] (optional)
                Description for target host. Can be recursive. Similar to target.
        host : Optional[Union[str, Dict[str, Any]]]
            Similar to target but for target host. Can be one of a literal target host string,
            a json string describing a configuration, or a dictionary of configuration options.
            When using a dictionary or json string to configure target, the possible values are
            same as target.
        """
        if isinstance(target, (dict, str)):
            target = convert(target)
        if isinstance(host, (dict, str)):
            host = convert(host)
        if target is None or not isinstance(target, (Map, String, Target)):
            raise ValueError("target has to be a string or dictionary.")
        if host is not None:
            if not isinstance(host, (Map, String, Target)):
                raise ValueError("target host has to be a string or dictionary.")
            self.__init_handle_by_constructor__(_ffi_api.Target, Target(target), Target(host))
        else:
            self.__init_handle_by_constructor__(_ffi_api.Target, target)

    def __enter__(self):
        _ffi_api.TargetEnterScope(self)
        return self

    def __exit__(self, ptype, value, trace):
        _ffi_api.TargetExitScope(self)

    def export(self):
        return _ffi_api.TargetExport(self)

    def with_host(self, host=None):
        return _ffi_api.WithHost(self, Target(host))

    @staticmethod
    def current(allow_none=True):
        """Returns the current target.

        Parameters
        ----------
        allow_none : bool
            Whether allow the current target to be none

        Raises
        ------
        ValueError if current target is not set.
        """
        return _ffi_api.TargetCurrent(allow_none)

    @property
    def arch(self):
        """Returns the cuda arch from the target if it exists."""
        return str(self.attrs.get("arch", ""))

    @property
    def max_num_threads(self):
        """Returns the max_num_threads from the target if it exists."""
        return int(self.attrs["max_num_threads"])

    @property
    def thread_warp_size(self):
        """Returns the thread_warp_size from the target if it exists."""
        return int(self.attrs["thread_warp_size"])

    @property
    def max_function_args(self):
        return int(self.attrs.get("max_function_args", -1))

    @property
    def device_name(self):
        return str(self.attrs.get("device", ""))

    @property
    def model(self):
        """Returns model from the target if it exists."""
        return str(self.attrs.get("model", "unknown"))

    @property
    def mcpu(self):
        """Returns the mcpu from the target if it exists."""
        return str(self.attrs.get("mcpu", ""))

    @property
    def mattr(self):
        """Returns the mattr from the target if it exists."""
        return list(self.attrs.get("mattr", []))

    @property
    def supports_integer_dot_product(self):
        if self.attrs.get("supports_integer_dot_product", []):
            return bool(self.attrs["supports_integer_dot_product"])
        return False

    @property
    def libs(self):
        return list(self.attrs.get("libs", []))

    def get_kind_attr(self, attr_name):
        """Get additional attribute about the target kind.

        Parameters
        ----------
        attr_name : str
            The attribute name.

        Returns
        -------
        value : object
            The attribute value
        """
        return _ffi_api.TargetKindGetAttr(self.kind, attr_name)

    @staticmethod
    def list_kinds():
        """Returns the list of available target names."""
        return list(_ffi_api.ListTargetKinds())

    @staticmethod
    def check_and_update_host_consist(target, host=None, target_is_dict_key=True):
        """A helper function that merges a legacy "target, target_host" pair, then returns
        the merged target and its host field. The function is for legacy target and target
        host pair only, and should not be used in the new target system.

        Parameters
        ----------
        target : Union[str, Dict[str, Any], Target]
            The target or heterogeneous target
        host : Union[str, Dict[str, Any], Target, None]
            The target host
        target_is_dict_key : Bool
            When the type of target is dict, whether Target is the key (Otherwise the value)
        """
        if isinstance(target, (dict, str)):
            target = convert(target)
        if isinstance(host, (dict, str)):
            host = convert(host)
        if target is None:
            assert host is None, "Target host is not empty when target is empty."
            return target, host
        if isinstance(target, Map) and "kind" not in target:
            new_target = {}
            for tgt, mod in target.items():
                if not target_is_dict_key:
                    tgt, mod = mod, tgt
                if isinstance(tgt, (Map, String, Target)):
                    tgt, host = Target.check_and_update_host_consist(tgt, host)
                if not target_is_dict_key:
                    tgt, mod = mod, tgt
                new_target[tgt] = mod
            target = new_target
        else:
            target = Target(target, host)
            host = target.host
        return target, host


# TODO(@tvm-team): Deprecate the helper functions below. Encourage the usage of config dict instead.
def _merge_opts(opts, new_opts):
    """Helper function to merge options"""
    if isinstance(new_opts, str):
        new_opts = new_opts.split()
    if new_opts:
        opt_set = set(opts)
        new_opts = [opt for opt in new_opts if opt not in opt_set]
        return opts + new_opts
    return opts


def cuda(model="unknown", arch=None, options=None):
    """Returns a cuda target.

    Parameters
    ----------
    model: str
        The model of cuda device (e.g. 1080ti)
    arch: str
        The cuda architecture (e.g. sm_61)
    options : str or list of str
        Additional options
    """
    opts = _merge_opts(["-model=%s" % model], options)
    if arch:
        opts = _merge_opts(["-arch=%s" % arch], opts)
    if not any(["-arch" in opt for opt in opts]):
        warnings.warn("Try specifying cuda arch by adding 'arch=sm_xx' to your target.")
    return Target(" ".join(["cuda"] + opts))


def rocm(model="unknown", options=None):
    """Returns a ROCM target.

    Parameters
    ----------
    model: str
        The model of this device
    options : str or list of str
        Additional options
    """
    opts = _merge_opts(["-model=%s" % model], options)
    return Target(" ".join(["rocm"] + opts))


def mali(model="unknown", options=None):
    """Returns a ARM Mali GPU target.

    Parameters
    ----------
    model: str
        The model of this device
    options : str or list of str
        Additional options
    """
    opts = ["-device=mali", "-model=%s" % model]
    opts = _merge_opts(opts, options)
    return Target(" ".join(["opencl"] + opts))


def intel_graphics(model="unknown", options=None):
    """Returns an Intel Graphics target.

    Parameters
    ----------
    model: str
        The model of this device
    options : str or list of str
        Additional options
    """
    opts = ["-device=intel_graphics", "-model=%s" % model, "-thread_warp_size=16"]
    opts = _merge_opts(opts, options)
    return Target(" ".join(["opencl"] + opts))


MICRO_SUPPORTED_MODELS = {
    "host": [],
    "atsamd51": ["-mcpu=cortex-m4"],
    "cxd5602gg": ["-mcpu=cortex-m4"],
    "esp32": [],
    "imxrt10xx": ["-mcpu=cortex-m7"],
    "mps2_an521": ["-mcpu=cortex-m33"],
    "mps3_an547": ["-mcpu=cortex-m55"],
    "nrf52840": ["-mcpu=cortex-m4"],
    "nrf5340dk": ["-mcpu=cortex-m33"],
    "sam3x8e": ["-mcpu=cortex-m3"],
    "stm32f746xx": ["-mcpu=cortex-m7", "-march=armv7e-m"],
    "stm32l4r5zi": ["-mcpu=cortex-m4"],
    "stm32u5xx": ["-mcpu=cortex-m33"],
    "zynq_mp_r5": ["-mcpu=cortex-r5"],
}


def micro(model="unknown", options=None):
    """Returns a microTVM target.

    Parameters
    ----------
    model : str
        Canonically identifies the target device. This is typically a device board level name.
        The allowed values are MICRO_SUPPORTED_MODELS.keys().
    options : str or list of str
        Additional options
    """
    if model not in MICRO_SUPPORTED_MODELS:
        raise ValueError(f"Model {model} not supported by tvm.target.micro.")
    opts = _merge_opts(
        MICRO_SUPPORTED_MODELS[model] + [f"-model={model}"],
        options,
    )

    # NOTE: in the future, the default micro target will be LLVM except when
    # external dependencies are present.
    return Target(" ".join(["c"] + opts))


def arm_cpu(model="unknown", options=None):
    """Returns a ARM CPU target.
    This function will also download pre-tuned op parameters when there is none.

    Parameters
    ----------
    model: str
        SoC name or phone name of the arm board.
    options : str or list of str
        Additional options
    """
    trans_table = {
        "pixel2": ["-model=snapdragon835", "-mtriple=arm64-linux-android", "-mattr=+neon"],
        "mate10": ["-model=kirin970", "-mtriple=arm64-linux-android", "-mattr=+neon"],
        "mate10pro": ["-model=kirin970", "-mtriple=arm64-linux-android", "-mattr=+neon"],
        "p20": ["-model=kirin970", "-mtriple=arm64-linux-android", "-mattr=+neon"],
        "p20pro": ["-model=kirin970", "-mtriple=arm64-linux-android", "-mattr=+neon"],
        "rasp3b": ["-model=bcm2837", "-mtriple=armv7l-linux-gnueabihf", "-mattr=+neon"],
        "rasp4b": [
            "-model=bcm2711",
            "-mtriple=armv8l-linux-gnueabihf",
            "-mattr=+neon",
            "-mcpu=cortex-a72",
        ],
        "rasp4b64": [
            "-model=bcm2711",
            "-mtriple=aarch64-linux-gnu",
            "-mattr=+neon",
            "-mcpu=cortex-a72",
        ],
        "rk3399": ["-model=rk3399", "-mtriple=aarch64-linux-gnu", "-mattr=+neon"],
        "pynq": ["-model=pynq", "-mtriple=armv7a-linux-eabi", "-mattr=+neon"],
        "ultra96": ["-model=ultra96", "-mtriple=aarch64-linux-gnu", "-mattr=+neon"],
        "beagleai": [
            "-model=beagleai",
            "-mtriple=armv7a-linux-gnueabihf",
            "-mattr=+neon,+vfp4,+thumb2",
            "-mcpu=cortex-a15",
        ],
        "stm32mp1": [
            "-model=stm32mp1",
            "-mtriple=armv7a-linux-gnueabihf",
            "-mattr=+neon,+vfp4,+thumb2",
            "-mcpu=cortex-a7",
        ],
        "thunderx": [
            "-model=thunderx",
            "-mtriple=aarch64-linux-gnu",
            "-mattr=+neon,+crc,+lse",
            "-mcpu=thunderxt88",
        ],
    }
    pre_defined_opt = trans_table.get(model, ["-model=%s" % model])

    opts = ["-device=arm_cpu"] + pre_defined_opt
    opts = _merge_opts(opts, options)
    return Target(" ".join(["llvm"] + opts))


def rasp(options=None):
    """Return a Raspberry 3b target.

    Parameters
    ----------
    options : str or list of str
        Additional options
    """
    warnings.warn(
        "tvm.target.rasp() is going to be deprecated. " 'Please use tvm.target.arm_cpu("rasp3b")'
    )
    return arm_cpu("rasp3b", options)


def vta(model="unknown", options=None):
    opts = ["-device=vta", "-keys=vta,cpu", "-model=%s" % model]
    opts = _merge_opts(opts, options)
    return Target(" ".join(["ext_dev"] + opts))


def bifrost(model="unknown", options=None):
    """Return an ARM Mali GPU target (Bifrost architecture).

    Parameters
    ----------
    options : str or list of str
        Additional options
    """
    opts = ["-device=bifrost", "-model=%s" % model]
    opts = _merge_opts(opts, options)
    return Target(" ".join(["opencl"] + opts))


def riscv_cpu(model="sifive-u54", options=None):
    """Returns a RISC-V CPU target.
    Default: sifive-u54 rv64gc

    Parameters
    ----------
    model: str
        CPU name.
    options : str or list of str
        Additional options
    """
    trans_table = {
        "sifive-e31": [
            "-model=sifive-e31",
            "-mtriple=riscv32-unknown-linux-gnu",
            "-mcpu=sifive-e31",
            "-mabi=ilp32",
            # cc: riscv64-unknown-linux-gnu-g++ -march=rv32imac -mabi=ilp32 -mcpu=sifive-e31
        ],
        "sifive-e76": [
            "-model=sifive-e76",
            "-mtriple=riscv32-unknown-linux-gnu",
            "-mcpu=sifive-e76",
            "-mabi=ilp32",
            # cc: riscv64-unknown-linux-gnu-g++ -march=rv32imafc -mabi=ilp32 -mcpu=sifive-e76
        ],
        "sifive-u54": [
            "-model=sifive-u54",
            "-mtriple=riscv64-unknown-linux-gnu",
            "-mcpu=sifive-u54",
            "-mabi=lp64d",
            # cc: riscv64-unknown-linux-gnu-g++ -march=rv64gc -mabi=lp64d -mcpu=sifive-u54
        ],
        "sifive-u74": [
            "-model=sifive-u74",
            "-mtriple=riscv64-unknown-linux-gnu",
            "-mcpu=sifive-u74",
            "-mabi=lp64d",
            # cc: riscv64-unknown-linux-gnu-g++ -march=rv64gc -mabi=lp64d -mcpu=sifive-u74
        ],
    }
    pre_defined_opt = trans_table.get(model, ["-model=%s" % model])

    opts = ["-device=arm_cpu"] + pre_defined_opt
    opts = _merge_opts(opts, options)
    return Target(" ".join(["llvm"] + opts))


def hexagon(cpu_ver="v66", **kwargs):
    """Returns a Hexagon target.

    Parameters
    ----------
    cpu_ver : str (default: "v66")
        CPU version used for code generation. Not all allowed cpu str
        will be valid, LLVM will throw an error.

    Recognized keyword parameters
    -----------------------------
    hvx : int (default: 128)
        Size of HVX vector in bytes. Value of 0 disables HVX codegen.
    sim_options : str or list of str (default: None)
        User defined sim arguments. CPU version defaults to cpu_ver.
        Otherwise, separate versions are used for codegen and sim. Not
        all allowed cpu strings will be valid, simulator will throw an
        error if invalid. Does not affect codegen.
    llvm_options : str or list of str (default: None)
        User defined compiler arguments.
    use_qfloat : bool (default: True for cpu_ver >= v68, False otherwise)
        Whether to use QFloat HVX instructions.
    use_ieee_fp : bool (default: False)
        Whether to use IEEE HVX instructions
    link_params : bool (default: False)
        Whether to link graph parameters into the LLVM module.

    Note: Floating point support in HVX requires LLVM 14+.
    """

    # Some of the target parameters correspond to target kind attributes
    # listed in src/target/target_kind.cc. For those parameters, their
    # names follow the attribute names with the exception of '_' being used
    # in place of '-'.

    # Example compiler arguments
    # llvm -mtriple=hexagon -mcpu=hexagonv66 -mattr=+hvxv66,+hvx-length128b

    def get_arch_version(cpu_ver):
        m = re.match(r"v([0-9]+).*", cpu_ver)
        assert m
        return int(m.group(1))

    # Check for valid codegen cpu
    valid_hex = ["v65", "v66", "v67", "v67t", "v68", "v69"]
    try:
        cpu_ver = cpu_ver[cpu_ver.index("v") :].lower()
        assert cpu_ver in valid_hex
    except:
        msg = "{} is not a valid Hexagon version\nvalid versions include {}"
        raise ValueError(msg.format(cpu_ver, valid_hex)) from None

    # Target configuration:
    arch_version = get_arch_version(cpu_ver)
    config = {
        "hvx": 128,
        "sim_options": None,
        "llvm_options": None,
        "use_qfloat": arch_version >= 68,
        "use_ieee_fp": False,
        "link_params": False,
    }
    config.update(kwargs)

    # Warn about obsolete parameter names.
    if config.get("sim_args"):
        msg = "The keyword parameter 'sim_args' is deprecated, use 'sim_options' instead"
        warnings.warn(msg, stacklevel=2)
        config.update({"sim_options": config["sim_args"]})
    if config.get("llvm_args"):
        msg = "The keyword parameter 'llvm_args' is deprecated, use 'llvm_options' instead"
        warnings.warn(msg, stacklevel=2)
        config.update({"llvm_options": config["llvm_args"]})

    # LLVM target string
    def create_llvm_target(cpu_ver, config):
        """Create LLVM target string."""

        target = " -mtriple=hexagon"
        mcpu = " -mcpu=hexagon" + cpu_ver

        # Process the options that affect target features and return the
        # target feature string.
        def create_target_features(config):
            features = {
                "use_qfloat": "hvx-qfloat",
                "use_ieee_fp": "hvx-ieee-fp",
            }
            tfs = []
            if config["hvx"] > 0:
                valid_hvx = [0, 64, 128]
                if not config["hvx"] in valid_hvx:
                    raise ValueError("Invalid hvx value, should be one of " + str(valid_hvx))
                tfs += ["+hvx" + cpu_ver, "+hvx-length" + str(config["hvx"]) + "b"]
            else:
                tfs += ["-hvx"]
            # All the additional features happen to only apply to v68+.
            # Don't bother applying them (even with '-') to lower versions.
            if arch_version >= 68:
                tfs += ["-+"[config[f]] + features[f] for f in features]

            return "-mattr=" + ",".join(tfs) if tfs else ""

        return target + mcpu + " " + create_target_features(config)

    # Simulator options string
    def create_sim_options(cpu_ver, config):
        """Create simulator option string."""

        def validate_hvx_length(codegen_hvx, sim_options):
            if sim_options and "--hvx_length" in sim_options:
                # If --hvx_length was specified, check HVX length of sim
                # vs codegen
                i = sim_options.index("hvx_length") + len("hvx_length") + 1
                sim_hvx = sim_options[i : i + 3]
                if sim_hvx != str(codegen_hvx):
                    msg = "sim hvx {} and codegen hvx {} mismatch!".format(sim_hvx, codegen_hvx)
                    # Set the stacklevel to the tvm.target.hexagon() call.
                    warnings.warn(msg, stacklevel=4)
            elif codegen_hvx != 0:
                # If --hvx_length was not given, add it if HVX is enabled
                sim_options = sim_options + " " if isinstance(sim_options, str) else ""
                sim_options += "--hvx_length " + str(codegen_hvx)
            return sim_options or ""

        hvx = config["hvx"]
        sim_options = config["sim_options"]
        if not sim_options:
            return cpu_ver + " " + validate_hvx_length(hvx, sim_options)

        sim_cpu = cpu_ver + " "

        # Add user defined args
        if isinstance(sim_options, list):
            sim_options = " ".join(sim_options)

        # Check for supplied sim cpu version
        if "v6" in sim_options:
            sim_cpu = ""

            # Regex match for allowed cpus
            valid_cpu_str_regex = (
                r"(?P<pre>--.*\s)?(--m)?"
                + r"(?P<base_version>v6[25678])(?P<sub_version>[a-z])?"
                + r"(?P<l2_size>_[0-9]+)?(?P<rev>_rev[0-9])?\s?(?P<post>--.*)?"
            )
            m = re.match(valid_cpu_str_regex, sim_options.lower())
            if not m:
                raise ValueError('Invalid simulator argument string "{}"'.format(sim_options))

            # Parse options into correct order
            cpu_attr = {x: str(m.groupdict()[x] or "") for x in m.groupdict()}
            sim_options = (
                cpu_attr["base_version"]
                + cpu_attr["sub_version"]
                + cpu_attr["l2_size"]
                + cpu_attr["rev"]
                + " "
                + cpu_attr["pre"]
                + cpu_attr["post"]
            )

        return sim_cpu + " " + validate_hvx_length(hvx, sim_options)

    # LLVM options string
    def create_llvm_options(cpu_ver, config):  # pylint: disable=unused-argument
        """Create LLVM options string."""

        llvm_options = config["llvm_options"]

        # TVM's option parser doesn't allow '=' in values, but '=' can
        # appear in LLVM flags. Replace it with '@', since it's unlikely
        # that '@' will be used in another context.
        if llvm_options is None or len(llvm_options.strip()) == 0:
            return ""
        args = [s.replace("=", "@") for s in llvm_options.split()]
        return "--llvm-options=" + ",".join(args)

    # TVM target attributes string
    def create_tvm_options(cpu_ver, config):  # pylint: disable=unused-argument
        """Create TVM target features string."""

        features = {
            "link_params": "link-params",
        }
        opts = ""
        for k in config:
            if k in features:
                opts += " --" + features[k] + "=" + str(config[k])
        return opts

    # Sim args
    os.environ["HEXAGON_SIM_ARGS"] = create_sim_options(cpu_ver, config)

    target_str = create_llvm_target(cpu_ver, config)
    llvm_str = create_llvm_options(cpu_ver, config)
    tvm_str = create_tvm_options(cpu_ver, config)

    args_list = target_str.split() + llvm_str.split() + tvm_str.split()

    return Target(" ".join(["hexagon"] + args_list))


def create(target):
    """Deprecated. Use the constructor of :py:mod:`tvm.target.Target` directly."""
    warnings.warn("tvm.target.create() is being deprecated. Please use tvm.target.Target() instead")
    return Target(target)


@_register_func("target._load_config_dict")
def _load_config_dict(config_dict_str):
    try:
        config = json.loads(config_dict_str)
    except json.decoder.JSONDecodeError:
        return None
    if not isinstance(config, dict):
        return None
    for key in config.keys():
        if not isinstance(key, str):
            return None
    return config
