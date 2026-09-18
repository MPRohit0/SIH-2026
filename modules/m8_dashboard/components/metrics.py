"""Metric card helper for the dashboard shell."""

from __future__ import annotations

from typing import Mapping

import streamlit as st


def render_metric_cards(metrics: Mapping[str, str]) -> None:
    """Display a row of simple metric cards."""
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics.items()):
        col.metric(label=label, value=value)
