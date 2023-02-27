from __future__ import annotations
import subprocess as sb

class BaseShell:
    def __init__(self):
        pass

    def run(self, stdin: sb._FILE = None, stdout: sb._FILE = None, stderr: sb._FILE = None):
        pass

    def pipe(self, shell: BaseShell):
        pass

class PipeShell(BaseShell):
    def __init__(self, shell1: BaseShell, shell2: BaseShell):
        self.shell1 = shell1
        self.shell2 = shell2

    def run(self, stdin: sb._FILE = None, stdout: sb._FILE = None, stderr: sb._FILE = None):
        p1 = self.shell1.run(stdin=stdin, stdout=sb.PIPE)
        p2 = self.shell2.run(stdin=p1.stdout, stdout=stdout, stderr=stderr)
        return p2
    
    def pipe(self, shell: BaseShell):
        return PipeShell(self, shell)

class Shell(BaseShell):
    def __init__(self, cmd: str, args: list[str] = []):
        self.cmd    = cmd
        self.args   = args
    
    def run(self, stdin: sb._FILE = None, stdout: sb._FILE = None, stderr: sb._FILE = None):
        self.args = " ".join( [self.cmd] + self.args)
        self.args = ["-Command", self.args]
        self.cmd = "powershell"

        out = sb.Popen([self.cmd] + self.args, stdin=stdin, stdout=stdout, stderr=stderr)
        out.wait()
        return out

    def pipe(self, shell: BaseShell):
        return PipeShell(self, shell)

sh1 = Shell("echo", ['\'print(\"print(\\\"oui\\\")\")\''])
sh2 = Shell("python")
sh3 = Shell("python")
sh1.pipe(sh2).pipe(sh3).run()