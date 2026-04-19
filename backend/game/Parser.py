from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Literal

@dataclass
class Token:
    type: str
    value: str

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
    parts: list[AndOr]

@dataclass
class Command:
    atom: Atom
    pre_redirs: list[Redirection]
    post_redirs: list[Redirection]
    assignments: list[VarDeclaration]

@dataclass
class AndOr:
    first: Command
    rest: list[tuple[Literal["&&", "||"], Command]]

@dataclass
class Sequence:
    parts: list[Pipe]

@dataclass
class Subshell:
    sequence: Sequence

Atom = SimpleCommand | Subshell | VarDeclaration

OPERATORS = {
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
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        # skip whitespace
        if c.isspace():
            i += 1
            continue
        # check 2-char operators
        if i + 1 < n:
            two = text[i:i+2]
            if two in OPERATORS:
                tokens.append(Token(OPERATORS[two], two))
                i += 2
                continue
        # check 1-char operators
        if c in OPERATORS:
            tokens.append(Token(OPERATORS[c], c))
            i += 1
            continue
        # quoted strings
        if c == '"' or c == "'":
            quote = c
            i += 1
            start = i
            buf = ""
            while i < n:
                if text[i] == quote:
                    break
                if quote == '"' and text[i] == "\\" and i + 1 < n:
                    i += 1
                    buf += text[i]
                else:
                    buf += text[i]
                i += 1
            if i >= n:
                raise SyntaxError("Unterminated quote")
            tokens.append(Token("WORD", buf))
            i += 1
            continue
        # normal word
        start = i
        while (
            i < n
            and not text[i].isspace()
            and text[i] not in "|&;()<>$\"'"
        ):
            i += 1
        tokens.append(Token("WORD", text[start:i]))
    return tokens

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self, expected_type=None):
        tok = self.peek()
        if expected_type and tok is not None and tok.type != expected_type:
            raise SyntaxError(f"Expected {expected_type}, got {tok.type}")
        self.pos += 1
        return tok

    # entry point
    def parse(self):
        return self.parse_sequence()
    
    def parse_sequence(self) -> Sequence:
        node = self.parse_pipeline()
        result = [node]
        while ((p := self.peek()) and p.type == "SEMI"):
            self.consume("SEMI")
            result.append(self.parse_pipeline())
        return Sequence(result)

    def parse_pipeline(self) -> Pipe:
        node = self.parse_andor()
        result = [node]
        while ((p := self.peek()) and p.type == "PIPE"):
            self.consume("PIPE")
            result.append(self.parse_andor())
        return Pipe(result)

    def parse_andor(self):
        first = self.parse_command()
        rest = []
        while ((p := self.peek()) and (p.type == "AND" or p.type == "OR")):
            tmp = self.consume()
            if tmp is None:
                raise Exception()
            rest.append((tmp.value, self.parse_command()))
        return AndOr(first, rest)
    
    def parse_redirections(self) -> list[Redirection]:
        result = []
        while ((p := self.peek()) and (p.value == ">" or p.value == ">>" or p.value == "<<" or p.value == "<")):
            self.consume()
            target = self.consume()
            if (p is not None and target is not None):
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

            assignments.append(
                VarDeclaration(name, Word([value]))
            )

        if ((p := self.peek()) is None or p.type not in ("WORD", "LPAREN")):
            if not assignments:
                raise SyntaxError("expected command")
            atom = SimpleCommand([])
            post_redirs = self.parse_redirections()
            return Command(atom, pre_redirs, post_redirs, assignments)

        atom = self.parse_atom()
        post_redirs = self.parse_redirections()
        return Command(atom, pre_redirs, post_redirs, assignments)

    def parse_word(self):
        p = self.peek()
        if p is None:
            return None

        if p.type == "WORD":
            return Word([self.consume().value])

        if p.type == "DOLLAR":
            self.consume()
            name = self.consume("WORD")
            return Word([VarUse(name.value)])

        return None

    def parse_atom(self):
        if ((p := self.peek()) and p.type == "LPAREN"):
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

text = "echo $x"
tokens = lex(text)
parser = Parser(tokens)
ast = parser.parse()
print (tokens)
print(ast)
