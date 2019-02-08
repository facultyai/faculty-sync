Faculty Platform incremental synchronization
============================================

[![Build Status](https://travis-ci.org/facultyai/faculty-sync.svg?branch=master)](https://travis-ci.org/facultyai/faculty-sync)

You like writing code on your computer, but want to run the code on
[Faculty Platform](https://faculty.ai). This makes that easier.

*faculty-sync* is a terminal application that helps automate synchronizing a local
directory with a directory on Faculty Platform. It will automatically monitor a local
directory for changes and replicate those changes in a directory on Faculty Platform.

![Screencast demo](demo.gif)

Installation
------------

You need a version of `rsync`. I have tested this with `rsync 2.6.9` and
`3.1.1`. This has only really been tested on macOS and Ubuntu 16.04. It will
almost certainly not work on Windows.

You will need Python 3.5 or later. I recommend installing *faculty-sync* in a
virtual environment.

To install, just type this in a terminal on your laptop:

```
pip install faculty-sync
```

Getting started
---------------

Let's say you are developing a Jupyter extension for visualizing geographical
data on Google maps. You have the code on your laptop at `~/oss/gmaps`, and you
want to replicate this directory in the project *jupyter-gmaps* on Faculty Platform.

First, make sure that:

1. you have a server in the *jupyter-gmaps* project,
2. the directory `/project/gmaps` exists on Faculty Platform, and that it's empty.

Then, in a terminal on  *your laptop*, head to `~/oss/gmaps` and run:

```
$ cd ~/oss/gmaps
$ faculty-sync --project jupyter-gmaps
```

You will be prompted for a remote directory. Choose `/project/gmaps`. *faculty-sync*
will then compute the difference between the directory on Faculty Platform and
`~/oss/gmaps` and list the differences. Press `u` to push all your files up to
Faculty Platform. Depending on the number and size of files and your network
bandwidth, the push may take a few seconds (or longer).

Then, push `w` to start a continuous watch-sync cycle. *faculty-sync* will watch the
local directory for changes and replicate them on Faculty Platform.

To get help on command-line options, run:

```
$ faculty-sync --help
```

When the application is running, you can often type `?` to get help on a
particular screen.

Working with git repositories
-----------------------------

*faculty-sync* ignores certain paths by default. In particular, it ignores paths in
`.git/`. If your code is under version control locally or on Faculty Platform, the git
state will not be pushed to Faculty Platform (but all the source files will).

Ignoring certain paths
----------------------

If you want to ignore file patterns, pass the `--ignore` argument to *faculty-sync*
with a list of path patterns. For instance, to ignore anything under `dist/`
and `/docs/build`, run `faculty-sync` with:

```
$ faculty-sync --project jupyter-gmaps --ignore dist/ docs/build/
```

You can pass shell glob-like patterns to `--ignore`. Some common patterns are
ignored automatically (`.ipybnb_checkpoints`, `node_modules`, `__pycache__`
among others; for a full list, look at the [cli module](faculty_sync/cli.py)).

Using configuration files
-------------------------

If you find yourself providing the same arguments every time you call
`faculty-sync`, you may want to take advantage of configuration files.

A configuration file can look like this:

```
[default]
ignore = *pkl, *csv, **/*.ipynb

[/path/to/local/directory]
project = projectname
remote = /project/remote_dir
ignore = *pkl, *csv, **/*.ipynb, *hdf, .cache/

[/some/other/path]
project = other_projectname
remote = /project/remote_dir
ignore = *pkl, *csv, *hdf, *xlsx
```

Configuration files need to be located either in your home directory at
`~/.config/faculty-sync/faculty-sync.conf`, or in the top-level directory of the
local directory at `~/projects/project/.faculty-sync.conf`.

`faculty-sync` checks for a configuration file first in your local directory, so
either as provided with `--local`, or the current working directory. If no file
is located there, it will check in the user directory (`~/.config/faculty-sync/faculty-sync.conf`).
This means you can keep a file outside of your local directory, if you want to
keep it tidied away, or inside it, if you want to have it in version control.

How to release
--------------

*faculty-sync* uses Bitbucket to host its artifacts, for now.

By convention, we normally create a release candidate before doing a full release. Release candidates have version numbers like `0.2.1-rc1`, where `0.2.1` is an as-yet unreleased full release. We start incrementing release candidates from `rc1`.

To run a pre-release:

 - Bump the version in `version.py` and in the install script.
 - Commit the changes.
 - Tag the release with an annotated tag: `git tag -a 0.3.0-rc1`.
 - Push the tag to GitHub (`git push --tags`).
 - Test that the prerelease installs correctly by running `pip install https://github.com/facultyai/faculty-sync/archive/0.3.0-rc1.zip` in a new virtual environment.

To run a full release:

 - Bump the version in `version.py` and in the installation instructions in the README.
 - Commit the changes.
 - Tag the release with an annotated tag: `git tag -a 0.3.0`. Include some brief release notes.
 - Push the tag to GitHub.
 - Create and push a source distribution to PyPI with `python setup.py sdist upload`.
 - Test that the release installs correctly by installing in a new virtual environment.

Acknowledgements
----------------

Many people in the Faculty Platform team and in Faculty have contributed to
the vision for *faculty-sync*, both technical and at the product level. Without
their help and encouragement, *faculty-sync* would not exist.

*faculty-sync* is maintained by Pascal. Until such day as we see fit to bring
it under the remit of the Faculty Platform team proper, support questions, bug reports
etc. should be directed to him personally, rather than to the team.
