"""Offline evaluation support kept outside the production API surface."""

from .cases import EvaluationCase, load_cases

__all__ = ["EvaluationCase", "load_cases"]
