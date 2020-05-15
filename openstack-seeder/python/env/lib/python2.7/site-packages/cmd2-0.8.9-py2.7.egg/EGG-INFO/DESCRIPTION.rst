cmd2 is a tool for building interactive command line applications in Python. Its goal is to make
it quick and easy for developers to build feature-rich and user-friendly interactive command line applications.  It
provides a simple API which is an extension of Python's built-in cmd module.  cmd2 provides a wealth of features on top
of cmd to make your life easier and eliminates much of the boilerplate code which would be necessary when using cmd.

The latest documentation for cmd2 can be read online here:
https://cmd2.readthedocs.io/

Main features:

    - Searchable command history (`history` command and `<Ctrl>+r`)
    - Text file scripting of your application with `load` (`@`) and `_relative_load` (`@@`)
    - Python scripting of your application with ``pyscript``
    - Run shell commands with ``!``
    - Pipe command output to shell commands with `|`
    - Redirect command output to file with `>`, `>>`; input from file with `<`
    - Bare `>`, `>>` with no filename send output to paste buffer (clipboard)
    - `py` enters interactive Python console (opt-in `ipy` for IPython console)
    - Multi-line commands
    - Special-character command shortcuts (beyond cmd's `?` and `!`)
    - Settable environment parameters
    - Parsing commands with arguments using `argparse`, including support for sub-commands
    - Unicode character support (*Python 3 only*)
    - Good tab-completion of commands, sub-commands, file system paths, and shell commands
    - Python 2.7 and 3.4+ support
    - Linux, macOS and Windows support
    - Trivial to provide built-in help for all commands
    - Built-in regression testing framework for your applications (transcript-based testing)
    - Transcripts for use with built-in regression can be automatically generated from `history -t`

Usable without modification anywhere cmd is used; simply import cmd2.Cmd in place of cmd.Cmd.


