# Copyright (c) 2016 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
import ast

from distutils.spawn import spawn

from build_ext.utils import Utils, BaseCommand
import os
import subprocess
from shutil import which

# These dependencies aren't available in build environments.  We won't need any
# linting functionality there though, so just create a dummy class so we can proceed.
try:
    import pycodestyle
except ImportError:
    pycodestyle = None


class Lint(BaseCommand):
    description = "examine code for errors"

    def has_spec_file(self):
        try:
            next(Utils.find_files_of_type(".", "*.spec"))
            return True
        except StopIteration:
            return False

    def has_flake8(self):
        return which("flake8") is not None

    def run(self):
        for cmd_name in self.get_sub_commands():
            self.run_command(cmd_name)

    # Defined at the end since it references unbound methods
    sub_commands = [
        ("lint_rpm", has_spec_file),
        ("flake8", has_flake8),
    ]


class RpmLint(BaseCommand):
    description = "run rpmlint on spec files"

    def run(self):
        files = subprocess.run(["git", "ls-files", "--full-name"], capture_output=True).stdout
        files = files.decode().splitlines()
        files = [x for x in files if x.endswith(".spec")]
        for f in files:
            spawn(["rpmlint", os.path.realpath(f)])


class Flake8(BaseCommand):
    description = "run flake8"

    def run(self):
        spawn(["flake8"])


class AstVisitor(object):
    """Visitor pattern for looking at specific nodes in an AST.  Basically a copy of
    ast.NodeVisitor, but with the additional feature of appending return values onto a result
    list that is ultimately returned.

    I recommend reading http://greentreesnakes.readthedocs.io/en/latest/index.html for a good
    overview of the various Python AST node types.
    """

    def __init__(self):
        self.results = []

    def visit(self, node):
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        r = visitor(node)
        if r is not None:
            self.results.append(r)
        return self.results

    def generic_visit(self, node):
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)
            elif isinstance(value, ast.AST):
                self.visit(value)


class DebugImportVisitor(AstVisitor):
    """Look for imports of various debug modules"""

    DEBUG_MODULES = ["pdb", "pudb", "ipdb", "pydevd"]
    codes = ["X200"]

    def visit_Import(self, node):
        # Likely not necessary but prudent
        self.generic_visit(node)

        for alias in node.names:
            module_name = alias.name
            if module_name in self.DEBUG_MODULES:
                return (node, "X200 imports of debug module '%s' should be removed" % module_name)

    def visit_ImportFrom(self, node):
        # Likely not necessary but prudent
        self.generic_visit(node)
        module_name = node.module
        if module_name in self.DEBUG_MODULES:
            return (node, "X200 imports of debug module '%s' should be removed" % module_name)


class GettextVisitor(AstVisitor):
    """Looks for Python string formats that are known to break xgettext.
    Specifically, constructs of the forms:
        _("a" + "b")
        _("a" + \
        "b")
    Also look for _(a) usages
    """

    codes = ["X300", "X301", "X302"]

    def visit_Call(self, node):
        # Descend first
        self.generic_visit(node)

        func = node.func
        if not isinstance(func, ast.Name):
            return

        if func.id != "_":
            return

        for arg in node.args:
            # ProTip: use print(ast.dump(node)) to figure out what the node looks like

            # Things like _("a" + "b") (including such constructs across line continuations
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                return (node, "X300 string concatenation that will break xgettext")

            # Things like _(some_variable)
            if isinstance(arg, ast.Name):
                return (node, "X301 variable reference that will break xgettext")

            # _("%s is great" % some_variable) should be _("%s is great") % some_variable
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod):
                return (
                    node,
                    "X302 string formatting within gettext function: _('%s' % foo) should be _('%s') % foo",
                )


class AstChecker(object):
    name = "SubscriptionManagerAstChecker"
    version = "1.0"

    def __init__(self, tree, filename):
        self.tree = tree
        self.filename = filename

        self.visitors = [
            (GettextVisitor, {}),
            (DebugImportVisitor, {}),
        ]

    def run(self):
        if self.tree:
            for visitor, kwargs in self.visitors:
                result = visitor(**kwargs).visit(self.tree)
                if result:
                    for node, msg in result:
                        yield self.err(node, msg)

    def err(self, node, msg=None):
        if not msg:
            msg = self._error_tmpl

        lineno = getattr(node, "lineno", 1)
        col_offset = getattr(node, "col_offset", 0)

        # Adjust line number and offset if a decorator is applied
        if isinstance(node, ast.ClassDef):
            lineno += len(node.decorator_list)
            col_offset += 6
        elif isinstance(node, ast.FunctionDef):
            lineno += len(node.decorator_list)
            col_offset += 4

        ret = (lineno, col_offset, msg, self)
        return ret
