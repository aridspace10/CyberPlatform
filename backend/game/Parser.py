from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


############ COMMAND LINE CLASSES ############
@dataclass
class Token:
    type: str
    value: str
    parts: list[Segment] | None = None


Identifier = str


@dataclass
class Redirection:
    op: Literal[">", ">>", "<", "<<"]
    target: Identifier


@dataclass
class VarUse:
    name: Identifier


@dataclass
class Word:
    parts: list["Segment"]


Segment = str | VarUse


@dataclass
class VarDeclaration:
    name: Identifier
    value: Word


@dataclass
class SimpleCommand:
    args: list[Word]


@dataclass
class Pipe:
    parts: list[Command]


@dataclass
class Command:
    atom: Atom
    pre_redirs: list[Redirection]
    post_redirs: list[Redirection]
    assignments: list[VarDeclaration]


@dataclass
class AndOr:
    first: Pipe
    rest: list[tuple[Literal["&&", "||"], Pipe]]


@dataclass
class Job:
    pipeline: AndOr
    background: bool


@dataclass
class Sequence:
    parts: list[Job]


@dataclass
class Subshell:
    sequence: Sequence


Atom = SimpleCommand | Subshell


############ FIND CLASSES ############
class Node:
    def eval(self, f) -> bool:
        raise NotImplementedError


@dataclass
class OrNode(Node):
    left: Node
    right: Node


@dataclass
class AndNode(Node):
    left: Node
    right: Node


@dataclass
class NotNode(Node):
    node: Node


@dataclass
class FilterNode(Node):
    type: str
    value: str


@dataclass
class ExecNode(Node):
    command: list[str]
    mode: Literal[";", "+"]


@dataclass
class DeleteNode(Node):
    pass


OPERATORS = {
    "&": "AMP",
    "&&": "AND",
    "||": "OR",
    "|": "PIPE",
    "<<": "HEREDOC",
    ">>": "APPEND",
    "<": "REDIR_IN",
    ">": "REDIR_OUT",
    ";": "SEMI",
    "(": "LPAREN",
    ")": "RPAREN",
    "=": "EQUAL",
    "$": "DOLLAR",
}


def lex(text: str) -> list[Token]:
    """Tokenize shell words with quote-aware `$NAME` and `$?` expansion.

    Braced parameter expansion, command substitution, globbing, and word splitting
    are intentionally unsupported.
    """
    tokens: list[Token] = []
    i = 0
    n = len(text)
    operators = {
        key: value for key, value in OPERATORS.items() if key not in ("$", "=")
    }

    def read_variable(index: int) -> tuple[VarUse | None, int]:
        index += 1
        if index < n and text[index] == "?":
            return VarUse("?"), index + 1
        start = index
        if index < n and (text[index].isalpha() or text[index] == "_"):
            index += 1
            while index < n and (text[index].isalnum() or text[index] == "_"):
                index += 1
            return VarUse(text[start:index]), index
        return None, start - 1

    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
            continue

        if i + 1 < n:
            two = text[i : i + 2]
            if two in operators:
                tokens.append(Token(operators[two], two))
                i += 2
                continue
        if c in operators:
            tokens.append(Token(operators[c], c))
            i += 1
            continue

        parts: list[Segment] = []
        buffer = ""

        def flush() -> None:
            nonlocal buffer
            if buffer:
                parts.append(buffer)
                buffer = ""

        while i < n:
            c = text[i]
            if c.isspace() or c in "|&;()<>":
                break
            if c in ("'", '"'):
                quote = c
                i += 1
                quoted = ""
                quote_parts: list[Segment] = []
                while i < n and text[i] != quote:
                    if quote == '"' and text[i] == "\\" and i + 1 < n:
                        i += 1
                        quoted += text[i]
                        i += 1
                        continue
                    if quote == '"' and text[i] == "$":
                        if quoted:
                            quote_parts.append(quoted)
                            quoted = ""
                        variable, next_index = read_variable(i)
                        if variable is None:
                            quoted += "$"
                            i += 1
                        else:
                            quote_parts.append(variable)
                            i = next_index
                        continue
                    quoted += text[i]
                    i += 1
                if i >= n:
                    raise SyntaxError("Unterminated quote")
                i += 1
                if quote == "'":
                    buffer += quoted
                else:
                    if quote_parts:
                        flush()
                        if quoted:
                            quote_parts.append(quoted)
                        parts.extend(quote_parts)
                    else:
                        buffer += quoted
                continue
            if c == "\\":
                if i + 1 >= n:
                    raise SyntaxError("Trailing escape")
                buffer += text[i + 1]
                i += 2
                continue
            if c == "$":
                flush()
                variable, next_index = read_variable(i)
                if variable is None:
                    buffer += "$"
                    i += 1
                else:
                    parts.append(variable)
                    i = next_index
                continue
            buffer += c
            i += 1

        flush()
        value = "".join(
            part if isinstance(part, str) else f"${part.name}" for part in parts
        )
        tokens.append(Token("WORD", value, parts or [""]))
    return tokens


class CommandParser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self, expected_type=None):
        tok = self.peek()
        if expected_type and (tok is None or tok.type != expected_type):
            actual = "end of input" if tok is None else tok.type
            raise SyntaxError(f"Expected {expected_type}, got {actual}")
        self.pos += 1
        return tok

    # entry point
    def parse(self):
        sequence = self.parse_sequence()
        if self.peek() is not None:
            raise SyntaxError(f"unexpected token '{self.peek().value}'")
        return sequence

    def parse_sequence(self) -> Sequence:
        if self.peek() is None:
            return Sequence([])
        result = []
        while self.peek() is not None:
            andor = self.parse_andor()
            separator = self.peek()
            background = separator is not None and separator.type == "AMP"
            result.append(Job(andor, background))
            if separator is None:
                break
            if separator.type not in ("SEMI", "AMP"):
                break
            self.consume(separator.type)
            if self.peek() is None:
                break
        return Sequence(result)

    def parse_pipeline(self) -> Pipe:
        result = [self.parse_command()]
        while (p := self.peek()) and p.type == "PIPE":
            self.consume("PIPE")
            result.append(self.parse_command())
        return Pipe(result)

    def parse_andor(self) -> AndOr:
        first = self.parse_pipeline()
        rest = []
        while (p := self.peek()) and p.type in ("AND", "OR"):
            tmp = self.consume()
            rest.append((tmp.value, self.parse_pipeline()))
        return AndOr(first, rest)

    def parse_redirections(self) -> list[Redirection]:
        result = []
        while (p := self.peek()) and (
            p.type in ("REDIR_OUT", "APPEND", "HEREDOC", "REDIR_IN")
        ):
            self.consume()
            target = self.peek()
            if target is None or target.type != "WORD":
                raise SyntaxError(f"expected target after {p.value}")
            self.consume("WORD")
            result.append(Redirection(p.value, target.value))
        return result

    def split_assignment(self, word: str):
        if "=" not in word:
            return None

        name, value = word.split("=", 1)

        if not name:
            return None

        if not (name[0].isalpha() or name[0] == "_"):
            return None

        if not all(c.isalnum() or c == "_" for c in name):
            return None
        return name, value

    def parse_command(self) -> Command:
        pre_redirs = self.parse_redirections()

        assignments = []

        while True:
            p = self.peek()

            if p is None or p.type != "WORD":
                break

            res = self.split_assignment(p.value)

            if not res:
                break

            name, value = res
            self.consume()

            assignments.append(VarDeclaration(name, Word([value])))

        if (p := self.peek()) is None or p.type not in ("WORD", "LPAREN"):
            if not assignments:
                raise SyntaxError("expected command")
            atom = SimpleCommand([])
            post_redirs = self.parse_redirections()
            return Command(atom, pre_redirs, post_redirs, assignments)

        if p.type == "LPAREN":
            atom = self.parse_atom()
            if self.peek() is not None and self.peek().type == "WORD":
                raise SyntaxError("unexpected word after subshell")
        else:
            args = []
            while self.peek() is not None:
                if self.peek().type in ("REDIR_OUT", "APPEND", "HEREDOC", "REDIR_IN"):
                    pre_redirs.extend(self.parse_redirections())
                elif self.peek().type in ("WORD", "DOLLAR"):
                    args.append(self.parse_word())
                else:
                    break
            atom = SimpleCommand(args)
        post_redirs = self.parse_redirections()
        return Command(atom, pre_redirs, post_redirs, assignments)

    def parse_word(self):
        p = self.peek()
        if p is None:
            return None

        if p.type == "WORD":
            word = self.consume()
            if word is None:
                raise SyntaxError("Admin Error: AAAB")
            return Word(word.parts or [word.value])

        if p.type == "DOLLAR":
            self.consume()
            name = self.consume("WORD")
            if name is None:
                raise SyntaxError("expected something after $")
            return Word([VarUse(name.value)])

        return None

    def parse_atom(self):
        if (p := self.peek()) and p.type == "LPAREN":
            return self.parse_subshell()

        args = []

        while True:
            word = self.parse_word()
            if word is None:
                break
            args.append(word)

        if not args:
            raise SyntaxError("expected command name")

        return SimpleCommand(args)

    def parse_subshell(self):
        self.consume("LPAREN")
        node = self.parse_sequence()
        self.consume("RPAREN")
        return Subshell(node)


class FindParser:
    def __init__(self, tokens) -> None:
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self, expected_type=None) -> str | None:
        tok = self.peek()
        self.pos += 1
        return tok

    # entry point
    def parse(self):
        node = self.parse_or()
        if self.peek() is not None:
            raise SyntaxError(f"Unexpected token: {self.peek()}")
        return node

    def parse_or(self):
        node = self.parse_and()

        while self.peek() and self.peek() == "-o":
            self.consume()
            right = self.parse_and()
            node = OrNode(node, right)

        return node

    def parse_and(self):
        node = self.parse_factor()

        while True:
            tok = self.peek()
            if not tok or tok in [")", "-o"]:
                break

            right = self.parse_factor()
            node = AndNode(node, right)

        return node

    def parse_factor(self) -> Node:
        tok = self.peek()
        if tok is None or tok == ")":
            raise SyntaxError("Expected find expression")

        if tok == "!":
            self.consume()
            return NotNode(self.parse_factor())

        if tok == "(":
            self.consume()
            node = self.parse_or()
            if self.consume() != ")":
                raise SyntaxError("Missing )")
            return node

        filt = self.consume()
        if filt is None:
            return FilterNode("", "")
        if filt in ["-true", "-false", "-empty", "-delete"]:
            return FilterNode(filt, "")
        if filt == "-exec":
            cmd = []
            while (tok := self.peek()) is not None and tok not in (";", "+"):
                cmd.append(self.consume())
            mode = self.consume()
            if mode not in (";", "+"):
                raise SyntaxError("Expected ; or +")
            if not cmd:
                raise SyntaxError("Expected command after -exec")
            return ExecNode(cmd, mode)
        if filt not in ("-type", "-name"):
            raise SyntaxError(f"Unsupported predicate: {filt}")
        val = self.consume()
        if val is None:
            raise SyntaxError(f"No value for given for: {filt}")
        return FilterNode(filt, val)


if __name__ == "__main__":
    text = ["(", "-name", "*.txt", "-o", "-true", ")", "-exec", "cat", "{}", ";"]
    parser = FindParser(text)
    ast = parser.parse()
    print(ast)
