from __future__ import annotations

import enum
import re
from typing import TypedDict

wordle_header_regex = re.compile(r"Wordle (\d+) (\w+)\/\d+")


class LossType(enum.Enum):
    infeasible = "Infeasible Guess"
    out_of_rounds = "Ran out of Guesses"


class Output(TypedDict):
    win: bool
    loss_type: LossType
    round: int
    column: int
    description: str


def analyze(puzzle: str):
    lines = wordle_header_regex.sub("", puzzle).strip().splitlines()
    if lines[0] == "🟩🟩🟩🟩🟩":
        return Output(win=True, round=1)
    for line_index, (line_1, line_2) in enumerate(zip(lines, lines[1:])):
        round_number = line_index + 2
        if line_2 == "🟩🟩🟩🟩🟩":
            return Output(win=True, round=round_number)
        for column_index, (col_1, col_2) in enumerate(zip(line_1, line_2)):
            if col_1 == "🟩" and col_2 != "🟩":
                return Output(
                    win=False,
                    round=round_number,
                    column=column_index + 1,
                    loss_type=LossType.infeasible,
                    description="Dropped a 🟩",
                )
        sa, sb = (sum(1 for c in line if c in "🟩🟨") for line in (line_1, line_2))
        if sa > sb:
            return Output(
                win=False,
                round=round_number,
                column=column_index + 1,
                loss_type=LossType.infeasible,
                description=f"Total 🟩🟨 count went from {sa} to {sb}",
            )
        if line_1.count("🟨") == 1 and line_1 == line_2:
            return Output(
                win=False,
                round=round_number,
                loss_type=LossType.infeasible,
                description="No new information revealed, exactly 1 🟨 and same as previous round",
            )
        if (
            line_1.count("🟨") == 2
            and line_1 == line_2
            and line_index
            and lines[line_index - 1] == line_1
        ):
            return Output(
                win=False,
                round=round_number,
                loss_type=LossType.infeasible,
                description="No new information revealed, exactly 2 🟨 and same as previous 2 rounds",
            )

    return Output(
        win=False,
        round=6,
        loss_type=LossType.out_of_rounds,
    )


def description(output: Output) -> str:
    return f"""
{'Win' if output['win'] else 'Loss'}{' ({})'.format(output['loss_type'].value) if output.get('loss_type') else ''}: Round {output['round']}{' Column {}'.format(output['column']) if output.get('column') else ''} {output.get('description') or ''}
""".strip()
