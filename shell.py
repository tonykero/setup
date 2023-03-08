from __future__ import annotations
import subprocess as sb

class BaseShell:
    dryrun = False

    def __init__(self):
        pass
    
    def raise_run(self, stdin: sb._FILE = None, stdout: sb._FILE = None) -> sb.Popen:
        o = self.run(stdin, stdout, stderr=sb.PIPE)
        if o.returncode == 0:
            return o
        
        args_str = " ".join(o.args)
        err_str = o.stderr.read().decode("utf-8")
        raise Exception(f"Command \"{args_str}\" with return code {o.returncode} and error: {err_str}")

    def run(self, stdin: sb._FILE = None, stdout: sb._FILE = None, stderr: sb._FILE = None) -> sb.Popen:
        pass

    def redirect(self, file: str):
        return RedirectShell(self, file)

    def pipe(self, shell: BaseShell) -> PipeShell:
        return PipeShell(self, shell)

class PipeShell(BaseShell):
    def __init__(self, shell1: BaseShell, shell2: BaseShell):
        self.shell1 = shell1
        self.shell2 = shell2

    def run(self, stdin: sb._FILE = None, stdout: sb._FILE = None, stderr: sb._FILE = None):
        p1 = self.shell1.run(stdin=stdin, stdout=sb.PIPE)
        p2 = self.shell2.run(stdin=p1.stdout, stdout=stdout, stderr=stderr)
        return p2

class RedirectShell(BaseShell):
    def __init__(self, shell: BaseShell, file:str):
        self.shell = shell
        self.file = file
    
    def run(self, stdin: sb._FILE = None, stdout: sb._FILE = None, stderr: sb._FILE = None):
        if self.dryrun:
            return self.shell.run(stdin=stdin, stdout=stdout, stderr=stderr)
        
        with open(self.file, "w") as fd:
            return self.shell.run(stdin=stdin, stdout=fd, stderr=stderr)

class Shell(BaseShell):
    def __init__(self, cmd: str, args: list[str] = []):
        self.cmd    = cmd
        self.args   = args

    def run(self, stdin: sb._FILE = None, stdout: sb._FILE = None, stderr: sb._FILE = None):
        full_cmd = [self.cmd] + self.args
        if self.dryrun:
            full_cmd_str = " ".join(full_cmd)
            print(f"DRYRUN: {full_cmd_str}")
            out = noop(stdin, stdout, stderr)
        else:
            out = sb.Popen(full_cmd, stdin=stdin, stdout=stdout, stderr=stderr)
        out.wait()
        return out


def noop(stdin, stdout, stderr):
    if stdout == sb.PIPE:
        return sb.Popen(["echo", "{}"], stdin=stdin, stdout=stdout, stderr=stderr)

    return sb.Popen(["/usr/bin/bash", "-c", ":"], stdin=stdin, stdout=stdout, stderr=stderr)