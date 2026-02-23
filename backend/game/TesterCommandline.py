from .filesystem import FileSystem
from .commandline import CommandLine
from .ShellState import ShellState

s = ShellState()
f = FileSystem()
f.add_file("f1.txt")
f.add_directory("d2")
s.fs = f
cmd = CommandLine()
print (cmd.enter_command('chmod 000 f1.txt', s))
print (cmd.enter_command("ls -l", s))