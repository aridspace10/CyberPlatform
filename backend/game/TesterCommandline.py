from .filesystem import FileSystem
from .commandline import CommandLine
from .ShellState import ShellState

s = ShellState()
f = FileSystem()
s.fs = f
cmd = CommandLine()
print (cmd.enter_command('echo hi > out.txt', s))
print (cmd.filesystem.filehead)