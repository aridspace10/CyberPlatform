"""grep MiniGames scenarios."""

from dataclasses import dataclass

from ..filenode import FileNode
from ..ShellState import GrepMatch
from .core import BasePack, Challenge, Observation

LOG_WORDS_BY_VARIANT = {
    "operations": ("access", "audit"),
    "delivery": ("build", "deploy"),
    "infrastructure": ("network", "system"),
}

LOG_LEVELS = ("INFO", "WARN", "ERROR")
TRACE_ALPHABET = "2345679ACDEF"
GREP_FLAGS = {
    "ignore_case": "i",
    "files_with_matches": "l",
    "line_regexp": "x",
    "word_regexp": "w",
    "line_number": "n",
    "invert_match": "v",
    "count": "c",
    "only_matching": "o",
    "recursive": "r",
    "with_filename": "H",
    "no_filename": "h",
    "regexp": "e",
    "include": "include=*.log",
    "exclude": "exclude=*.tmp",
    "exclude_dir": "exclude-dir=archive-*",
}


class GrepPack(BasePack):
    command = "grep"
    root = "logs"
    variants = tuple(LOG_WORDS_BY_VARIANT)

    modes = {
        "Case Insensitive": "ignore_case",
        "Find By Filename": "files_with_matches",
        "Match By Line": "line_regexp",
        "Match By Word": "word_regexp",
        "Show Line Number": "line_number",
        "Invert Match": "invert_match",
        "Count Matches": "count",
        "Only Matching Text": "only_matching",
        "Recursive Search": "recursive",
        "Show Filename": "with_filename",
        "Hide Filename": "no_filename",
        "Explicit Pattern": "regexp",
        "Include Files": "include",
        "Exclude Files": "exclude",
        "Exclude Directories": "exclude_dir",
        "Regular Expression": "regex",
    }

    def build(self, index: int, mode: str, variant: str) -> Challenge:
        label = self.rng.choice(LOG_WORDS_BY_VARIANT[variant])
        path = f"/logs/{label}-{index:02d}-{self.token_hex(2)}.log"
        marker = "TRACE_" + "".join(self.rng.choice(TRACE_ALPHABET) for _ in range(8))
        stored_marker = marker.lower() if mode == "ignore_case" else marker
        line = f"{self.rng.choice(LOG_LEVELS)} {stored_marker} {label} event"
        contents = [f"INFO {label} started", line, f"INFO {label} complete"]
        if mode == "word_regexp":
            contents.insert(1, f"INFO before{marker}after decoy")
        if mode == "invert_match":
            contents = [f"INFO {marker} rejected", f"INFO {label} accepted"]
            line = contents[1]
        if mode == "only_matching":
            contents[1] = f"INFO prefix-{marker}-suffix {label} event"
            line = contents[1]
        if mode == "regex":
            contents[1] = f"INFO {marker} {label} event"
            line = contents[1]
        if mode == "recursive":
            directory = f"/logs/active-{index:02d}"
            self.shell.fs.add_directory(directory)
            path = f"{directory}/{label}-{self.token_hex(2)}.log"
        self.shell.fs.add_file(path)
        node = self.shell.fs.resolve(path)
        assert isinstance(node, FileNode)
        node.set_data(contents)

        if mode in {"include", "exclude", "exclude_dir"}:
            if mode == "exclude_dir":
                decoy_dir = f"/logs/archive-{index:02d}"
                self.shell.fs.add_directory(decoy_dir)
                decoy = f"{decoy_dir}/decoy.log"
            else:
                decoy = f"/logs/decoy-{index:02d}-{self.token_hex(2)}.tmp"
            self.shell.fs.add_file(decoy)
            self.shell.fs.resolve(decoy).set_data([f"WARN {marker} decoy"])
        if mode == "no_filename":
            decoy = f"/logs/other-{index:02d}-{self.token_hex(2)}.log"
            self.shell.fs.add_file(decoy)
            self.shell.fs.resolve(decoy).set_data(["INFO unrelated event"])

        prompts = {
            "basic": f"Use grep to print the line containing {marker} from {path}",
            "ignore_case": f"Use grep -i to find {marker} regardless of case in {path}",
            "files_with_matches": (
                f"Use grep to print filenames containing {marker} under /logs"
            ),
            "line_regexp": f'Use grep -x to print exactly "{line}" from {path}',
            "word_regexp": f"Use grep -w to find {marker} as a whole word in {path}",
            "line_number": (
                f"Use grep -n to print {marker} with its line number from {path}"
            ),
        }
        solutions = {
            "basic": f"grep {marker} {path}",
            "ignore_case": f"grep -i {marker} {path}",
            "files_with_matches": f"grep -rl {marker} /logs",
            "line_regexp": f'grep -x "{line}" {path}',
            "word_regexp": f"grep -w {marker} {path}",
            "line_number": f"grep -n {marker} {path}",
            "invert_match": f"grep -v {marker} {path}",
            "count": f"grep -c {marker} {path}",
            "only_matching": f"grep -o {marker} {path}",
            "recursive": f"grep -rH {marker} /logs",
            "with_filename": f"grep -H {marker} {path}",
            "no_filename": (
                f"grep -h {marker} {path} {decoy}" if mode == "no_filename" else ""
            ),
            "regexp": f"grep -e {marker} {path}",
            "include": f"grep -rH --include='*.log' {marker} /logs",
            "exclude": f"grep -rH --exclude='*.tmp' {marker} /logs",
            "exclude_dir": f"grep -rH --exclude-dir='archive-*' {marker} /logs",
            "regex": f"grep 'TRACE_[A-F0-9]{{8}}' {path}",
        }
        examples = {
            "basic": "grep ERROR /logs/sample.log",
            "ignore_case": "grep -i error /logs/sample.log",
            "files_with_matches": "grep -rl ERROR /logs",
            "line_regexp": "grep -x 'ERROR ready' /logs/sample.log",
            "word_regexp": "grep -w ERROR /logs/sample.log",
            "line_number": "grep -n ERROR /logs/sample.log",
            "invert_match": "grep -v ERROR /logs/sample.log",
            "count": "grep -c ERROR /logs/sample.log",
            "only_matching": "grep -o 'ERR_[0-9]+' /logs/sample.log",
            "recursive": "grep -rH ERROR /logs",
            "with_filename": "grep -H ERROR /logs/sample.log",
            "no_filename": "grep -h ERROR /logs/a.log /logs/b.log",
            "regexp": "grep -e ERROR /logs/sample.log",
            "include": "grep -rH --include='*.log' ERROR /logs",
            "exclude": "grep -rH --exclude='*.tmp' ERROR /logs",
            "exclude_dir": "grep -rH --exclude-dir='archive-*' ERROR /logs",
            "regex": "grep 'ERR_[0-9]+' /logs/sample.log",
        }
        directory_prompts = {
            "recursive": f"Use grep to search recursively for {marker} under /logs",
            "include": (f"Use grep to search for {marker} in *.log files under /logs"),
            "exclude": (
                f"Use grep to search for {marker}, excluding *.tmp files, under /logs"
            ),
            "exclude_dir": (
                f"Use grep to search for {marker}, excluding archive-* directories, "
                "under /logs"
            ),
        }
        if mode in directory_prompts:
            prompts[mode] = directory_prompts[mode]
        if mode not in prompts:
            descriptions = {
                "invert_match": "print lines that do not contain",
                "count": "count lines containing",
                "only_matching": "print only the matching text",
                "with_filename": "print the matching line with its filename for",
                "no_filename": "print the matching line without a filename for",
                "regexp": "supply the pattern with -e to find",
                "regex": "use a regular expression to find a TRACE marker in",
            }
            prompts[mode] = f"Use grep to {descriptions[mode]} {marker} in {path}"
        pattern = "TRACE_[A-F0-9]{8}" if mode == "regex" else marker
        if mode == "line_regexp":
            pattern = line
        expected_stdout = None
        if mode in {
            "invert_match",
            "count",
            "only_matching",
            "recursive",
            "with_filename",
            "no_filename",
            "regexp",
            "include",
            "exclude",
            "exclude_dir",
            "regex",
        }:
            output = {
                "invert_match": line,
                "count": "1",
                "only_matching": marker,
                "recursive": f"{path}:{line}",
                "with_filename": f"{path}:{line}",
                "no_filename": line,
                "regexp": line,
                "include": f"{path}:{line}",
                "exclude": f"{path}:{line}",
                "exclude_dir": f"{path}:{line}",
                "regex": line,
            }[mode]
            expected_stdout = [output]
        question_id = f"{self.round_number}-{index}"
        question = {
            "id": question_id,
            "command": "grep",
            "mode": mode,
            "prompt": prompts[mode],
            "example": examples[mode],
        }
        self._answers[question_id] = {
            "command": "grep",
            "inode_id": node.inode.id,
            "pattern": pattern,
            "line": line,
            "required_option": GREP_FLAGS.get(mode),
            "expected_stdout": expected_stdout,
            "solution": solutions[mode],
        }
        return self._challenge_from_answer(question, variant, GrepGoal)


@dataclass(frozen=True)
class GrepGoal:
    answer: dict

    def accepts(self, observation: Observation) -> bool:
        return self.accepts_matches(observation.shell.grep_matches, observation.stdout)

    def accepts_matches(
        self, matches: set[GrepMatch], stdout: list[str] | None = None
    ) -> bool:
        answer = self.answer
        if (
            answer.get("expected_stdout") is not None
            and stdout != answer["expected_stdout"]
        ):
            return False
        return any(
            match.inode_id == answer["inode_id"]
            and match.pattern == answer["pattern"]
            and match.line == answer["line"]
            and (
                answer["required_option"] is None
                or answer["required_option"] in match.options
            )
            and (("l" in match.options) == (answer["required_option"] == "l"))
            and all(
                flag not in match.options or answer["required_option"] == flag
                for flag in ("c", "o", "v")
            )
            and (stdout is None or match.output in stdout)
            for match in matches
        )
