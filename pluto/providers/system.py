
import os
from pluto.base import Fail
from pluto.providers import Provider

class FileProvider(Provider):
    def action_create(self):
        path = self.resource.path
        write = False
        content = self._get_content()
        if not os.path.exists(path):
            write = True
        else:
            with open(path, "rb") as fp:
                if content != fp.read():
                    write = True

        if write:
            with open(path, "wb") as fp:
                if content:
                    fp.write(content)
            self.resource.updated()

        if self.resource.mode:
            stat = os.stat(self.resource.path)
            if stat.st_mode & 0777 != self.resource.mode:
                os.chmod(path, self.resource.mode)
                self.resource.updated()

    def action_delete(self):
        path = self.resource.path
        if os.path.exists(path):
            os.unlink(path)
            self.changed()

    def action_touch(self):
        path = self.resource.path
        with open(path, "a") as fp:
            pass

    def _get_content(self):
        content = self.resource.content
        if isinstance(content, basestring):
            return content
        elif hasattr(content, "__call__"):
            return content()
        raise Fail("Unknown source type for %s: %r" % (self, content))


class DirectoryProvider(Provider):
    def action_create(self):
        path = self.resource.path
        if not os.path.exists(path):
            if self.recursive:
                os.makedir(path, self.mode)
            else:
                os.mkdir(path, self.mode)
            self.resource.updated()

        st = os.stat(path)
        if (st.st_mode & 0777) != self.mode:
            os.chmod(path, self.mode)
            self.resource.updated()

    def action_delete(self):
        path = self.resource.path
        if os.path.exists(path):
            os.rmdir(path)
            # TODO: recursive
            self.resource.updated()

class ExecuteProvider(Provider):
    def action_run(self):
        if self.resource.creates:
            if os.path.exists(self.resource.creates):
                return

        ret = subprocess.call(self.resource.command, cwd=self.resource.cwd, env=self.resource.environment)
        if ret != self.resource.returns:
            raise Fail("%s failed, returned %d instead of %s" % (self, ret, self.resource.returns))
        self.resource.updated()