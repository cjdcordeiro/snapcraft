# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2016,2020 Canonical Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""This plugin just dumps the content from a specified source.

This plugin uses the common plugin keywords as well as those for 'sources'.
For more information check the 'plugins' topic for the former and the
'sources' topic for the latter.

In the cases where dumping the content needs some mangling or organizing
one would take advantage of the core functionalities available to plugins
such as: `filesets`, `stage`, `snap` and `organize`.
"""

import os

import snapcraft_legacy
from snapcraft_legacy.internal import errors
from snapcraft_legacy.plugins.v1 import PluginV1


class DumpInvalidSymlinkError(errors.SnapcraftError):
    fmt = (
        "Failed to copy {path!r}: it's a symlink pointing outside the snap.\n"
        "Fix it to be valid when snapped and try again."
    )

    def __init__(self, path):
        super().__init__(path=path)


class DumpPlugin(PluginV1):
    @classmethod
    def schema(cls):
        schema = super().schema()
        schema["required"] = ["source"]
        return schema

    def enable_cross_compilation(self):
        pass

    def build(self):
        super().build()
        snapcraft_legacy.file_utils.link_or_copy_tree(
            self.builddir,
            self.installdir,
            copy_function=lambda src, dst: _link_or_copy(src, dst, self.installdir),
        )


def _link_or_copy(source, destination, boundary):
    """Attempt to copy symlinks as symlinks unless pointing out of boundary."""

    follow_symlinks = False

    # If this is a symlink, analyze where it's pointing and make sure it will
    # still be valid when snapped. If it won't, follow the symlink when
    # copying (i.e. copy the file to which the symlink is pointing instead).
    if os.path.islink(source):
        link = os.readlink(source)
        destination_dirname = os.path.dirname(destination)
        normalized = os.path.normpath(os.path.join(destination_dirname, link))
        if os.path.isabs(link) or not normalized.startswith(boundary):
            # Only follow symlinks that are NOT pointing at libc (LP: #1658774)
            if link not in snapcraft_legacy.repo.Repo.get_package_libraries("libc6"):
                follow_symlinks = True

    try:
        snapcraft_legacy.file_utils.link_or_copy(
            source, destination, follow_symlinks=follow_symlinks
        )
    except errors.SnapcraftCopyFileNotFoundError:
        raise DumpInvalidSymlinkError(source)
