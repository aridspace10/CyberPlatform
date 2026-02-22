from .filesystem import FileSystem
from .commandline import CommandLine
from .ShellState import ShellState

s = ShellState()
f = FileSystem()
f.add_file("f1.txt")
f.add_directory("d2")
s.fs = f
cmd = CommandLine()
print (cmd.enter_command('echo hi > out.txt', s))
print (cmd.enter_command('echo hi > out2.txt', s))
print (cmd.enter_command('mkdir d1', s))
print (cmd.enter_command('echo hi > d2/out3.txt', s))
print (cmd.enter_command('ls', s))
print (cmd.enter_command('cd d2 && ls', s))