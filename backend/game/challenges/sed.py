"""sed MiniGames scenarios."""

from dataclasses import dataclass

from ..filenode import FileNode
from ..ShellState import SedChange, ShellState
from .core import BasePack, Challenge, FileContentGoal, Observation

LOG_WORDS_BY_VARIANT = {
    "operations": ("access", "audit"),
    "delivery": ("build", "deploy"),
    "infrastructure": ("network", "system"),
}


class SedPack(BasePack):
    command = "sed"
    root = "data"
    variants = tuple(LOG_WORDS_BY_VARIANT)

    modes = {
        "Save a backup": "backup",
        "Case Insensitive": "ignore_case",
        "Replace All": "global",
        "Replace Occurrence": "occurrence",
        "Print Changes": "print_substitution",
        "Quiet Output": "quiet",
        "Expression Option": "expression_option",
        "Script File": "script_file",
        "Edit In Place": "in_place",
        "Line Address": "address_line",
        "Pattern Address": "address_regex",
        "Last Line Address": "address_last",
        "Address Range": "range",
        "Negated Address": "negated_address",
        "Delete Lines": "delete",
        "Print Lines": "print",
        "Multiple Expressions": "multiple_expressions",
        "Alternate Delimiter": "custom_delimiter",
        "Regex Substitution": "regex_substitution",
    }

    def build(self, index: int, mode: str, variant: str) -> Challenge:
        if mode not in {"basic", "backup", "ignore_case"}:
            return self._add_extended_sed_question(index, mode, variant)
        label = self.rng.choice(LOG_WORDS_BY_VARIANT[variant])
        path = f"/data/{label}-{index:02d}-{self.token_hex(2)}.txt"
        source = f"old{self.token_hex(3)}"
        replacement = f"new{self.token_hex(3)}"
        stored_source = source.upper() if mode == "ignore_case" else source
        before = (f"INFO {label} started", f"{stored_source} {label} event")
        after = (before[0], f"{replacement} {label} event")
        self.shell.fs.add_file(path)
        node = self.shell.fs.resolve(path)
        assert isinstance(node, FileNode)
        node.set_data(list(before))

        prompts = {
            "basic": (
                f"Use sed to replace {source} with {replacement} in {path} "
                "and print the changed line"
            ),
            "ignore_case": (
                f"Use sed's I flag to replace {source} with {replacement} "
                f"regardless of case in {path} and print the changed line"
            ),
            "backup": (
                f"Use sed -i.bak to replace {source} with {replacement} "
                f"in {path} and keep a backup"
            ),
        }
        question_id = f"{self.round_number}-{index}"
        flag = "I" if mode == "ignore_case" else ""
        solution = (
            f"sed -i.bak 's/{source}/{replacement}/' {path}"
            if mode == "backup"
            else f"sed 's/{source}/{replacement}/{flag}' {path}"
        )
        examples = {
            "basic": "sed 's/foo/bar/' /data/sample.txt",
            "backup": "sed -i.bak 's/foo/bar/' /data/sample.txt",
            "ignore_case": "sed 's/foo/bar/I' /data/sample.txt",
        }
        question = {
            "id": question_id,
            "command": "sed",
            "mode": mode,
            "prompt": prompts[mode],
            "example": examples[mode],
        }
        self._answers[question_id] = {
            "command": "sed",
            "inode_id": node.inode.id,
            "path": path,
            "before": before,
            "after": after,
            "line": after[1],
            "required_option": mode,
            "solution": solution,
        }
        return self._challenge_from_answer(question, variant, SedGoal)

    def _add_extended_sed_question(
        self, index: int, mode: str, variant: str
    ) -> Challenge:
        label = self.rng.choice(LOG_WORDS_BY_VARIANT[variant])
        path = f"/data/{label}-{index:02d}-{self.token_hex(2)}.txt"
        source = f"old{self.token_hex(3)}"
        replacement = f"new{self.token_hex(3)}"
        before = (f"INFO {label} started", f"{source} {label} event")
        after = (before[0], f"{replacement} {label} event")
        script = f"s/{source}/{replacement}/"
        prefix = ""
        script_file = None
        if mode == "global":
            before = (f"{source} {source} event",)
            after = (f"{replacement} {replacement} event",)
            script += "g"
        elif mode == "occurrence":
            before = (f"{source} {source} {source} event",)
            after = (f"{source} {replacement} {source} event",)
            script += "2"
        elif mode == "print_substitution":
            prefix = "-n "
            script += "p"
        elif mode == "quiet":
            prefix = "-n "
            script = "2p"
            after = before
        elif mode == "expression_option":
            prefix = "-e "
        elif mode == "script_file":
            script_file = f"/data/script-{index:02d}-{self.token_hex(2)}.sed"
            self.shell.fs.add_file(script_file)
            self.shell.fs.resolve(script_file).set_data([script])
        elif mode == "in_place":
            prefix = "-i "
        elif mode == "address_line":
            before = (f"{source} decoy", f"{source} target")
            after = (before[0], f"{replacement} target")
            script = "2" + script
        elif mode == "address_regex":
            before = (f"{source} decoy", f"TARGET {source}")
            after = (before[0], f"TARGET {replacement}")
            script = "/TARGET/" + script
        elif mode == "address_last":
            before = (f"{source} first", f"{source} last")
            after = (before[0], f"{replacement} last")
            script = "$" + script
        elif mode == "range":
            before = (f"{source} first", f"{source} second", f"{source} third")
            after = (before[0], f"{replacement} second", f"{replacement} third")
            script = "2,3" + script
        elif mode == "negated_address":
            before = (f"{source} first", f"{source} second")
            after = (before[0], f"{replacement} second")
            script = "1!" + script
        elif mode == "delete":
            before = ("keep first", f"remove {source}", "keep last")
            after = (before[0], before[2])
            script = "2d"
        elif mode == "print":
            script = "2p"
            after = before
        elif mode == "multiple_expressions":
            final = f"done{self.token_hex(3)}"
            after = (before[0], f"{final} {label} event")
            prefix = f"-e '{script}' -e "
            script = f"s/{replacement}/{final}/"
        elif mode == "custom_delimiter":
            script = f"s|{source}|{replacement}|"
        elif mode == "regex_substitution":
            before = (f"old42 {label} event",)
            after = (f"{replacement} {label} event",)
            script = f"s/old[0-9]+/{replacement}/"

        self.shell.fs.add_file(path)
        node = self.shell.fs.resolve(path)
        assert isinstance(node, FileNode)
        node.set_data(list(before))
        solution = (
            f"sed -f {script_file} {path}"
            if script_file
            else f"sed {prefix}'{script}' {path}"
        )
        examples = {
            "global": "sed 's/foo/bar/g' /data/sample.txt",
            "occurrence": "sed 's/foo/bar/2' /data/sample.txt",
            "print_substitution": "sed -n 's/foo/bar/p' /data/sample.txt",
            "quiet": "sed -n '2p' /data/sample.txt",
            "expression_option": "sed -e 's/foo/bar/' /data/sample.txt",
            "script_file": "sed -f /data/example.sed /data/sample.txt",
            "in_place": "sed -i 's/foo/bar/' /data/sample.txt",
            "address_line": "sed '2s/foo/bar/' /data/sample.txt",
            "address_regex": "sed '/READY/s/foo/bar/' /data/sample.txt",
            "address_last": "sed '$s/foo/bar/' /data/sample.txt",
            "range": "sed '2,3s/foo/bar/' /data/sample.txt",
            "negated_address": "sed '1!s/foo/bar/' /data/sample.txt",
            "delete": "sed '2d' /data/sample.txt",
            "print": "sed '2p' /data/sample.txt",
            "multiple_expressions": (
                "sed -e 's/foo/bar/' -e 's/bar/baz/' /data/sample.txt"
            ),
            "custom_delimiter": "sed 's|foo|bar|' /data/sample.txt",
            "regex_substitution": "sed 's/foo[0-9]+/bar/' /data/sample.txt",
        }
        expected_stdout = list(after)
        if mode in {"quiet", "print_substitution"}:
            expected_stdout = [after[1]]
        elif mode == "print":
            expected_stdout = [before[0], before[1], before[1]]
        elif mode == "in_place":
            expected_stdout = []
        target = (
            f"File should contain: {'; '.join(after)}"
            if mode == "in_place"
            else f"Expected output: {'; '.join(expected_stdout)}"
        )
        question_id = f"{self.round_number}-{index}"
        question = {
            "id": question_id,
            "command": "sed",
            "mode": mode,
            "prompt": (
                f"Use sed's {mode.replace('_', ' ')} feature on {path}. {target}"
            ),
            "example": examples[mode],
        }
        self._answers[question_id] = {
            "command": "sed",
            "inode_id": node.inode.id,
            "path": path,
            "before": before,
            "after": after,
            "line": after[-1],
            "required_option": mode,
            "required_features": {mode},
            "expected_stdout": expected_stdout,
            "in_place": mode == "in_place",
            "solution": solution,
        }
        return self._challenge_from_answer(question, variant, SedGoal)


@dataclass(frozen=True)
class SedGoal:
    answer: dict

    def accepts(self, observation: Observation) -> bool:
        return self.accepts_changes(
            observation.shell.sed_changes,
            observation.stdout,
            observation.shell,
        )

    def accepts_changes(
        self, changes: list[SedChange], stdout: list[str], shell: ShellState
    ) -> bool:
        answer = self.answer
        for edit in changes:
            if (
                edit.inode_id != answer["inode_id"]
                or edit.before != answer["before"]
                or edit.after != answer["after"]
            ):
                continue
            mode = answer["required_option"]
            if "required_features" in answer:
                if not answer["required_features"].issubset(edit.features):
                    continue
                if edit.in_place != answer["in_place"]:
                    continue
                if edit.in_place:
                    if not FileContentGoal(
                        answer["path"], answer["inode_id"], answer["after"]
                    ).matches(shell):
                        continue
                if stdout != answer["expected_stdout"]:
                    continue
                if (
                    edit.output != tuple(answer["expected_stdout"])
                    and not edit.in_place
                ):
                    continue
                return True
            if mode == "backup":
                if not edit.in_place or not edit.backup_suffix:
                    continue
                backup = shell.fs.resolve(answer["path"] + edit.backup_suffix)
                if not isinstance(backup, FileNode):
                    continue
                if tuple(backup.get_data()) != answer["before"]:
                    continue
            elif (
                edit.in_place
                or answer["line"] not in edit.output
                or answer["line"] not in stdout
                or (mode == "ignore_case" and not edit.ignore_case)
            ):
                continue
            return True
        return False
