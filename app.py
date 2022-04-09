import asyncio
import functools
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, List

import pandas
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

import data_utils

st.set_page_config(layout="wide")

st.session_state.setdefault("counter", 0)
st.session_state.setdefault("run", False)


@st.experimental_singleton
def _word():
    words = Path("words.csv").read_text().splitlines()
    return words[datetime.utcnow().date().toordinal() % len(words)]


def _buster(busted_function: Callable[[], Any]) -> Callable[[Callable[[], Any]], Any]:
    @functools.wraps(busted_function)
    def wrapper(*args, **kwargs):
        value = busted_function(*args, **kwargs)
        st.session_state.update(cache_key=uuid.uuid4().hex)
        return value

    return wrapper


def _cache_key():
    return st.session_state.get("cache_key", "start")


@st.experimental_memo
def fetch(cache_key: str) -> List[data_utils.ReidleRecord]:
    """Return all records."""
    return data_utils.get()


data = fetch(_cache_key())

f"""
[Go to Wordle](https://www.nytimes.com/games/wordle/index.html) Starter: **{_word()}**
"""
c = st.container()
df = pandas.DataFrame.from_records(
    [
        {
            "Name": row["name"],
            "Date": datetime.fromisoformat(row["date"]).date().isoformat(),
            "Time": (datetime.min + timedelta(seconds=row["seconds"]))
            .time()
            .strftime("%H:%M:%S"),
            "Failure": row["failure"],
            "Wordle": row["wordle_paste"],
        }
        for row in data
    ]
)
b = GridOptionsBuilder.from_dataframe(df)
b.configure_selection(selection_mode="multiple")
selected_rows = AgGrid(
    df,
    gridOptions=b.build(),
    fit_columns_on_grid_load=True,
    theme="streamlit",
    update_mode=GridUpdateMode.SELECTION_CHANGED,
)["selected_rows"]

with c:

    a, b, c, cc, f, w, d, e, _ = st.columns([1.2, 0.5, 3, 5, 5, 8, 2, 2, 0.1])
    with a:

        def _on_click():
            st.session_state.run = not st.session_state.run

        start_timer = st.button(
            "⏹" if st.session_state.run else "▶️", on_click=_on_click
        )
        x = st.empty()
        x.text(st.session_state.counter)
    if selected_rows:
        with e:

            @_buster
            def _onclick():
                for row in selected_rows:
                    for i, record in enumerate(df.to_dict("records")):
                        if record == row:
                            data_utils.delete(data[i]["key"])

            st.button("🗑", on_click=_onclick)
    if st.session_state.counter and not st.session_state.run:
        with c:
            name = st.text_input("Name")
        with cc:
            seconds = st.number_input(
                "Seconds", value=st.session_state.counter, min_value=0, step=1
            )
        with f:
            failure = st.selectbox(
                "Failure",
                ["No", "Not a word", "Infeasible Guess", "Ran out of Guesses"],
            )
        with w:
            wordle = st.text_area(
                "Wordle Paste", "", help="Copy and paste from Wordle Share"
            )
        with d:

            @_buster
            def _add_on_click():
                st.session_state.counter = 0
                st.session_state.run = False
                data_utils.add(
                    name=name,
                    date=datetime.utcnow().isoformat(),
                    seconds=seconds,
                    failure=failure,
                    wordle_paste=wordle or "",
                )

            st.button("➕", on_click=_add_on_click, disabled=not name or not seconds)
if st.session_state.run:

    async def runner():
        if not st.session_state.run:
            return
        st.session_state.counter = 0
        st.session_state.run = True
        while st.session_state.run:
            st.session_state.counter += 1
            x.text(st.session_state.counter)
            _ = await asyncio.sleep(1)

    asyncio.run(runner())
