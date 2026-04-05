from filesystem import FileSystem
from commandline import CommandLine
from ShellState import ShellState

s = ShellState()
f = FileSystem()
s.fs = f
cmd = CommandLine()
print (str(f.to_dict()))