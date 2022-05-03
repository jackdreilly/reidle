"""Data utils for reidle."""
from datetime import datetime
from typing import List, TypedDict

import streamlit as st
from deta import Deta


class ReidleRecord(TypedDict):
    """A record of a reidle."""

    name: str
    date: datetime
    seconds: int
    failure: str
    wordle_paste: str


def _get_data():
    return Deta(st.secrets.deta.password)


def _db():
    return _get_data().Base(st.secrets.deta.get("db", "reidle"))


def get() -> List[ReidleRecord]:
    """Return all records."""
    return sorted(_db().fetch().items, key=lambda x: x["date"], reverse=True)


def add(**record: ReidleRecord):
    """Add record"""
    return _db().insert(record)


def delete(key: str):
    """Delete key"""
    return _db().delete(key)
