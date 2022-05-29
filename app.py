import asyncio
import functools
import uuid
import zlib
from datetime import date, datetime, timedelta
from pathlib import Path
from streamlit_javascript import st_javascript
from typing import Any, Callable, List

import pandas
import streamlit as st
import yaml
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

import data_utils
from wordle import analyze, description, wordle_header_regex

st.set_page_config(layout="wide")

st.session_state.setdefault("counter", 0)
st.session_state.setdefault("run", False)
st.session_state.setdefault("cache_key", uuid.uuid4().hex)


def send_sms(*args, **kwargs):
    """Sendgrid email"""
    if not st.secrets.get("sendgrid", {}).get("api_key"):
        return
    yaml_string = yaml.safe_dump({**kwargs, "args": args})
    SendGridAPIClient(st.secrets.sendgrid.api_key).send(
        Mail(
            from_email="jackdreilly@gmail.com",
            to_emails="reidle@googlegroups.com",
            subject="Update",
            html_content=f"<pre>{yaml_string}</pre>",
        )
    )


@st.experimental_memo
def _word(today: date):
    words = Path("words.csv").read_text().splitlines()
    return words[zlib.crc32(today.isoformat().encode()) % len(words)]


def _buster(busted_function: Callable[[], Any]) -> Callable[[Callable[[], Any]], Any]:
    @functools.wraps(busted_function)
    def wrapper(*args, **kwargs):
        value = busted_function(*args, **kwargs)
        st.session_state.update(cache_key=uuid.uuid4().hex)
        return value

    return wrapper


@st.experimental_memo
def fetch(cache_key: str) -> List[data_utils.ReidleRecord]:
    """Return all records."""
    return data_utils.get()


data = fetch(st.session_state.cache_key)

local_date = datetime.now() - timedelta(
    minutes=st_javascript("new Date().getTimezoneOffset()")
)

"""
# [✨✨✨Try Reidle Beta!!!✨✨✨](https://reidle-d39c2.web.app/#/)
"""

f"""
**TODAY'S WORD:** **`{_word(local_date.date())}`** [Go to Wordle](https://www.nytimes.com/games/wordle/index.html)
"""
c = st.container()
df = pandas.DataFrame.from_records(
    [
        {
            "Name": row["name"],
            "Date": datetime.fromisoformat(row["date"]).date().strftime("%m/%d"),
            "Time": (datetime.min + timedelta(seconds=row["seconds"]))
            .time()
            .strftime("%M:%S"),
            "Rds": (
                (m := wordle_header_regex.match(row["wordle_paste"]))
                and m.group(2)
                or ""
            ),
            "Fail": row["failure"],
            "Paste": wordle_header_regex.sub("", row["wordle_paste"]).strip(),
        }
        for row in data
    ]
)
if df.empty:
    df["winner"] = False
else:
    no_failures = df[df["Fail"] == "No"]
    df["winner"] = (
        no_failures.groupby(["Date"])["Time"].transform(min) == no_failures["Time"]
    ).transform(lambda x: "NY"[x])
b = GridOptionsBuilder.from_dataframe(df)
b.configure_selection(selection_mode="multiple")
b.configure_grid_options(rowClassRules=dict(winner="data.winner == 'Y'"))
b.configure_column("winner", hide=True)
b.configure_column(
    "Paste",
    autoHeight=True,
    suppressSizeToFit=True,
    wrapText=True,
    cellStyle={
        "white-space": "break-spaces",
        "line-height": "2vh",
        "font-size": "2vh",
        "min-height": "8vh",
    },
)
selected_rows = AgGrid(
    df,
    gridOptions=b.build(),
    # fit_columns_on_grid_load=True,
    allow_unsafe_jscode=True,
    theme="streamlit",
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    custom_css={".winner": {"font-weight": "bold", "color": "#016943 !important"}},
)["selected_rows"]

with c:

    a, b, c, cc, w, f, d, e, _ = st.columns([1.2, 0.5, 3, 5, 5, 8, 2, 2, 0.1])
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
                            if datetime.utcnow() - datetime.fromisoformat(
                                data[i]["date"]
                            ) > timedelta(hours=1):
                                st.warning("Record too old to delete (max 1 hour)")
                                continue
                            send_sms(action="deleted", **data[i])
                            data_utils.delete(data[i]["key"])

            st.button("🗑", on_click=_onclick)
    if st.session_state.counter and not st.session_state.run:
        with c:
            name = st.text_input("Name")
        with cc:
            seconds = st.number_input(
                "Seconds", value=st.session_state.counter, min_value=0, step=1
            )
        with w:
            wordle = st.text_area(
                "Wordle Paste", "", help="Copy and paste from Wordle Share"
            )
            output = None
            try:
                output = analyze(wordle)
            except:
                pass
        with f:
            if output and not output["win"]:
                failure = description(output)
                st.info(f"Failure: {failure}")
            else:
                failure = st.selectbox(
                    "Failure",
                    ["No", "Not a word", "Infeasible Guess", "Ran out of Guesses"],
                )
        with d:

            @_buster
            def _add_on_click():
                st.session_state.counter = 0
                st.session_state.run = False
                send_sms(
                    action="posted",
                    name=name,
                    date=local_date.isoformat(),
                    seconds=seconds,
                    failure=failure,
                    wordle_paste=wordle,
                )
                data_utils.add(
                    name=name,
                    date=local_date.isoformat(),
                    seconds=seconds,
                    failure=failure,
                    wordle_paste=wordle or "",
                )

            st.button("➕", on_click=_add_on_click, disabled=not name or not seconds)
if st.session_state.run:

    async def _runner():
        if not st.session_state.run:
            return
        st.session_state.counter = 0
        st.session_state.run = True
        while st.session_state.run:
            st.session_state.counter += 1
            x.text(st.session_state.counter)
            _ = await asyncio.sleep(1)

    asyncio.run(_runner())
df["lower"] = df["Name"].str.lower()

"""
### Leaderboard (last 30 days)
"""
AgGrid(
    df[df["winner"] == "Y"][
        df["Date"].apply(
            lambda x: datetime.strptime(x, "%m/%d").replace(year=datetime.now().year)
        )
        >= (datetime.now() - timedelta(days=30))
    ][["winner", "lower"]]
    .groupby("lower", as_index=False)
    .count()
    .rename(columns={"lower": "Name", "winner": "Count"})
    .sort_values(by=["Count"], ascending=False)
)
