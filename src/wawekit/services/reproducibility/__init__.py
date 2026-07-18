"""Standardization-reproducibility auditing (the research flagship).

Structure standardization is mandatory but under-specified: different protocols —
and different settings within one toolkit — produce different "standard"
structures for the same input, so a molecule's identity can silently depend on
the pipeline. This package treats that *divergence* as a first-class, quantified
diagnostic.

R1 (this stage) provides the **protocol engine**: a named, composable
:class:`~wawekit.services.reproducibility.protocol.StandardizationProtocol`, a set
of presets, and the primitives to apply a protocol and take a molecule's standard
identity (InChIKey). Later stages build the divergence analysis, metrics, GUI and
benchmark on top.
"""

from wawekit.services.reproducibility.protocol import (
    DEFAULT_PROTOCOLS,
    OPERATION_ORDER,
    PRESET_AGGRESSIVE,
    PRESET_CHEMBL_LIKE,
    PRESET_MINIMAL,
    StandardForm,
    StandardizationProtocol,
    StandardOp,
    apply_protocol,
    standard_identity,
    standardize,
)

__all__ = [
    "DEFAULT_PROTOCOLS",
    "OPERATION_ORDER",
    "PRESET_AGGRESSIVE",
    "PRESET_CHEMBL_LIKE",
    "PRESET_MINIMAL",
    "StandardForm",
    "StandardOp",
    "StandardizationProtocol",
    "apply_protocol",
    "standard_identity",
    "standardize",
]
