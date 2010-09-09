
__all__ = ["Kitchen", "Cookbook"]

import os
from kokki.environment import Environment
from kokki.utils import AttributeDictionary

class Cookbook(object):
    def __init__(self, name, path, config=None):
        self.name = name
        self.path = path
        self._config = config
        self._library = {}

    @property
    def config(self):
        if self._config is None:
            metapath = os.path.join(self.path, "metadata.py")
            with open(metapath, "rb") as fp:
                source = fp.read()
                meta = {}
                exec compile(source, metapath, "exec") in meta
                self._config = meta.get('__config__', {})

        return self._config

    @classmethod
    def load_from_path(cls, name, path):
        return cls(name, path)

    def __getattr__(self, name):
        if name in self._library:
            return self._library[name]

        libpath = os.path.join(self.path, "libraries", name) + ".py"
        with open(libpath, "rb") as fp:
            source = fp.read()
            globs = {}
            exec compile(source, libpath, "exec") in globs
            self._library[name] = AttributeDictionary(globs)

        return self._library[name]

class Kitchen(Environment):
    def __init__(self):
        super(Kitchen, self).__init__()
        self.included_recipes = set()
        self.cookbooks = AttributeDictionary()
        self.cookbook_paths = []

    def add_cookbook_path(self, path):
        # Check if it's a Python import path
        if "." in path and not os.path.exists(path):
            pkg = __import__(path, {}, {}, path)
            path = os.path.dirname(os.path.abspath(pkg.__file__))
        self.cookbook_paths.append(path)

    def register_cookbook(self, cb):
        self.update_config(dict((k, v.get('default')) for k, v in cb.config.items()), False)
        self.cookbooks[cb.name] = cb

    def load_cookbook(self, *args, **kwargs):
        for name in args:
            cb = None
            for path in self.cookbook_paths:
                fullpath = os.path.join(path, name)
                if not os.path.exists(fullpath):
                    continue
                cb = Cookbook.load_from_path(name, fullpath)

            if not cb:
                raise ImportError("Cookbook %s not found" % name)

            self.register_cookbook(cb)

    def include_recipe(self, *args):
        for name in args:
            if name in self.included_recipes:
                continue

            self.included_recipes.add(name)

            try:
                cookbook, recipe = name.split('.')
            except ValueError:
                cookbook, recipe = name, "default"

            try:
                cb = self.cookbooks[cookbook]
            except KeyError:
                self.load_cookbook(cookbook)
                cb = self.cookbooks[cookbook]
                # raise Fail("Trying to include a recipe from an unknown cookbook %s" % name)

            globs = {'env': self}

            path = os.path.join(cb.path, "recipes", recipe + ".py")
            if not os.path.exists(path):
                raise Fail("Recipe %s in cookbook %s not found" % (recipe, cookbook))

            with open(path, "rb") as fp:
                rc = fp.read()

            with self:
                exec compile(rc, name, 'exec') in globs