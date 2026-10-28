"""Device defaults independent of dataset and rendering dependencies."""

import sys

import torch


def runtime_settings(accelerator="auto", precision=None, num_workers=None, configured_workers=0):
    """Choose a supported default precision and avoid macOS worker copies."""
    if accelerator == "auto":
        if torch.cuda.is_available():
            accelerator = "cuda"
        elif torch.backends.mps.is_available():
            accelerator = "mps"
        else:
            accelerator = "cpu"
    if precision is None:
        precision = "16-mixed" if accelerator in ("cuda", "gpu") else "32-true"
    if num_workers is None:
        num_workers = 0 if sys.platform == "darwin" else configured_workers
    if num_workers < 0:
        raise ValueError("num_workers must be non-negative")
    return accelerator, precision, num_workers
