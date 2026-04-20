from game.filesystem import FileSystem
from game.commandline import CommandLine
from game.ShellState import ShellState

s = ShellState()
f = FileSystem()
f.add_directory("d1")
f.add_file("d1/f2.txt")
f.add_file("f1.txt")
s.fs = f
cmd = CommandLine()
print (cmd.enter_command('find . \( -name "*.txt" \)', s))