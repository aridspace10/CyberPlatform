import re
from dataclasses import dataclass
from __future__ import annotations
from typing import Literal

@dataclass
class Token:
    type: str
    value: str

TOKEN_SPEC = [
    ("AND",      r"&&"),
    ("OR",       r"\|\|"),
    ("PIPE",     r"\|"),
    ("SEMI",     r";"),
    ("LPAREN",   r"\("),
    ("RPAREN",   r"\)"),
    ("WORD",     r"[^\s|&;()]+"),
    ("SKIP",     r"[ \t]+"),
]

master = re.compile("|".join(f"(?P<{name}>{regex})" for name, regex in TOKEN_SPEC))

Identifier = str

@dataclass
class Redirection:
    op: Literal[">", ">>", "<", "<<"]
    target: Identifier

@dataclass
class VarUse:
    name: Identifier

@dataclass
class VarDeclaration:
    name: Identifier
    value: Identifier

@dataclass
class SimpleCommand:
    args: list[str]

@dataclass
class Pipe:
    parts: list[AndOr]

@dataclass
class Command:
    atom: Atom
    pre_redirs: list[Redirection]
    post_redirs: list[Redirection]

@dataclass
class AndOr:
    first: Command
    rest: list[tuple[Literal["&&", "||"], Command]]

@dataclass
class Sequence:
    pipes: list[Pipe]

@dataclass
class Subshell:
    sequence: Sequence

Atom = SimpleCommand | Subshell | VarDeclaration

def lex(text):
    tokens = []
    for match in master.finditer(text):
        kind = match.lastgroup
        value = match.group()
        if kind != "SKIP":
            tokens.append(Token(kind, value))
    return tokens

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self, expected_type=None):
        tok = self.peek()
        if expected_type and tok.type != expected_type:
            raise SyntaxError(f"Expected {expected_type}, got {tok.type}")
        self.pos += 1
        return tok

    # entry point
    def parse(self):
        return self.parse_sequence()
    
    def parse_sequence(self):
        node = self.parse_pipeline()

    def parse_pipeline(self):
        node = self.parse_andor()

    def parse_andor(self):
        node = self.parse_command()

    def parse_command(self):
        pass

    def parse_subshell(self):
        self.consume("LPAREN")
        node = self.parse_sequence()
        self.consume("RPAREN")
        return Subshell(node)

    def parse_atom(self):
        if (self.peek() and self.peek().type == "LPAREN"):
            node = self.parse_subshell()


print (lex("echo hello > text.txt | grep hi && pwd"))