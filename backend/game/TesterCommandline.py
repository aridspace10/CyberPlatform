from game.filesystem import FileSystem
from game.commandline import CommandLine
from game.ShellState import ShellState

s = ShellState()
f = FileSystem()
f.add_file("f1.txt")
s.fs = f
cmd = CommandLine()
print (cmd.enter_command('cp f1.txt f2.txt', s))