"""Choose varied, reproducible challenges for each round."""

import random
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class PlanItem:
    command: str
    mode: str
    variant: str


class RoundPlanner:
    def __init__(self):
        self.command_counts: Counter[str] = Counter()
        self.mode_counts: Counter[tuple[str, str]] = Counter()
        self.variant_counts: Counter[tuple[str, str]] = Counter()

    def plan(
        self,
        commands: list[str],
        command_config: dict,
        question_count: int,
        question_modes: dict,
        packs: dict,
        rng: random.Random,
    ) -> list[PlanItem]:
        if question_count >= len(commands):
            offset = sum(self.command_counts.values()) % len(commands)
            slots = [
                commands[(offset + index) % len(commands)]
                for index in range(question_count)
            ]
            self.command_counts.update(slots)
        else:
            slots = []
            for _ in range(question_count):
                minimum = min(self.command_counts[command] for command in commands)
                command = rng.choice(
                    [
                        candidate
                        for candidate in commands
                        if self.command_counts[candidate] == minimum
                        and candidate not in slots
                    ]
                )
                slots.append(command)
                self.command_counts[command] += 1
        rng.shuffle(slots)
        counts = Counter(slots)
        candidates: dict[str, list[str]] = {}
        for command in commands:
            selected = [
                question_modes[command][option]
                for option in command_config[command].get("options", [])
                if option in question_modes[command]
            ]
            choices = list(dict.fromkeys(selected))
            if not choices or counts[command] > len(choices):
                choices.append("basic")
            candidates[command] = choices

        planned = []
        round_mode_counts: Counter[tuple[str, str]] = Counter()
        for command in slots:
            modes = candidates[command]
            minimum = min(round_mode_counts[command, mode] for mode in modes)
            least_used = [
                mode for mode in modes if round_mode_counts[command, mode] == minimum
            ]
            historical_minimum = min(
                self.mode_counts[command, mode] for mode in least_used
            )
            mode = rng.choice(
                [
                    candidate
                    for candidate in least_used
                    if self.mode_counts[command, candidate] == historical_minimum
                ]
            )
            round_mode_counts[command, mode] += 1
            self.mode_counts[command, mode] += 1
            variants = packs[command].variants
            minimum = min(self.variant_counts[command, variant] for variant in variants)
            variant = rng.choice(
                [
                    candidate
                    for candidate in variants
                    if self.variant_counts[command, candidate] == minimum
                ]
            )
            self.variant_counts[command, variant] += 1
            planned.append(PlanItem(command, mode, variant))
        return planned
