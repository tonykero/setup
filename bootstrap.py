import urllib.request
import urllib.parse
import os.path
import zipimport
import importlib
import importlib.util
import sys

class GithubModule:
    def __init__(self, url, module_name):
        self.url         = url
        self.module_name = module_name
        
    def get_url_basename(self, url):
        basename = urllib.parse.urlsplit(url).path
        return os.path.basename(basename)

    def download_repo(self, url, filename=None):
        if filename==None:
            filename=self.get_url_basename(url)
        _loc, _ = urllib.request.urlretrieve(url, filename=filename)
        return _loc

    def module_from_archive(self, file, module_name):
        importer = zipimport.zipimporter(file)
        module_spec = importer.find_spec(self.module_name)
        if module_spec:
            module = importlib.util.module_from_spec(module_spec)
            if module:
                module_spec.loader.exec_module(module)
                return module
        return None

    def add_to_sys(self):
        mod_name = os.path.basename(self.module.__name__)
        sys.modules[mod_name] = self.module
    
    def remove_from_sys(self):
        mod_name = os.path.basename(self.module.__name__)
        sys.modules.pop(mod_name, None)


    def load(self):
        self.file       = self.download_repo(self.url)
        self.module     = self.module_from_archive(self.file, self.module_name)
        self.add_to_sys()
        return self.module

    def __enter__(self):
        return self.load()

    def __exit__(self, type, value, tb):
        self.remove_from_sys()


url = "https://github.com/tonykero/setup/archive/refs/heads/master.zip"
with GithubModule(url, "setup-master\\shell") as mod:
    print(mod)
    from shell import *
    Shell('echo', ['oui']).run()