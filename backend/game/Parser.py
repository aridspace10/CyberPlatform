from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Literal

@dataclass
class Token:
    type: str
    value: str

TOKEN_SPEC = [
    ("AND",      r"&&"),
    ("DOLLAR",   r"\$"),
    ("OR",       r"\|\|"),
    ("PIPE",     r"\|"),
    ("HEREDOC",  r"<<"),
    ("APPEND",   r">>"),
    ("REDIR_IN", r"<"),
    ("REDIR_OUT",r">"),
    ("SEMI",     r";"),
    ("LPAREN",   r"\("),
    ("RPAREN",   r"\)"),
    ("EQUAL",    r"="),
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
    args: list[str | VarUse]

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
    parts: list[Pipe]

@dataclass
class Subshell:
    sequence: Sequence

Atom = SimpleCommand | Subshell | VarDeclaration

def lex(text):
    tokens = []
    for match in master.finditer(text):
        kind = match.lastgroup
        value = match.group()
        if kind != "SKIP" and kind is not None:
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
        while ((p := self.peek()) and (p.value in ["<", ">", ">>", "<<"])):
            val = self.consume().value
            result.append(Redirection(val, self.consume()))
        return result

    def parse_command(self) -> Command:
        pre = self.parse_redirections()
        atom = self.parse_atom()
        post = self.parse_redirections()
        return Command(atom, pre, post)

    def parse_atom(self):
        if ((p := self.peek()) and p.type == "LPAREN"):
            return self.parse_subshell()
        args = []
        while ((p := self.peek())):
            if (p.type == "DOLLAR"):
                self.consume()
                tmp = self.consume("WORD")
                if tmp is None:
                    raise Exception()
                args.append(VarUse(tmp.value))
            elif (p.type == "WORD"):
                tmp = self.consume()
                if tmp is None:
                    raise Exception()
                args.append(tmp.value)
            else:
                break
        if ((p := self.peek()) and p.type == "EQUAL"):
            self.consume()
            val = self.consume("WORD")
            if val is None:
                raise Exception()
            return VarDeclaration(args[0], val.value)
        else:
            return SimpleCommand(args)

    def parse_subshell(self):
        self.consume("LPAREN")
        node = self.parse_sequence()
        self.consume("RPAREN")
        return Subshell(node)

# text = "echo hello | grep hi && pwd"
# tokens = lex(text)
# parser = Parser(tokens)
# ast = parser.parse()

# print(ast)
