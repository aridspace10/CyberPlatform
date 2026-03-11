from .filesystem import FileSystem
from .commandline import CommandLine
from .ShellState import ShellState

s = ShellState()
f = FileSystem()
f.add_file("f1.txt")
f.add_directory("d2")
f.add_directory("d2/f3.txt")
s.fs = f
cmd = CommandLine()
print (cmd.enter_command('echo h1 > d2/f3.txt', s))
print (cmd.enter_command("cat d2/f3.txt", s))