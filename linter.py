#
# linter.py
# Linter for SublimeLinter3, a code checking framework for Sublime Text 3
#
# Written by Aparajita Fishman
# Copyright (c) 2015-2016 The SublimeLinter Community
# Copyright (c) 2013-2014 Aparajita Fishman
#
# License: MIT
#

"""This module exports the PYCODESTYLE plugin linter class."""

import os

from SublimeLinter.lint import persist, PythonLinter


class PYCODESTYLE(PythonLinter):
    """Provides an interface to the pep8 python module/script."""

    syntax = 'python'
    cmd = ('pycodestyle@python', '*', '-')
    version_args = '--version'
    version_re = r'(?P<version>\d+\.\d+\.\d+)'
    version_requirement = '>= 1.4.6'
    regex = r'^.+?:(?P<line>\d+):(?P<col>\d+): (?:(?P<error>E\d+)|(?P<warning>W\d+)) (?P<message>.+)'
    multiline = True
    defaults = {
        '--select=,': '',
        '--ignore=,': '',
        '--max-line-length=': None
    }
    inline_settings = 'max-line-length'
    inline_overrides = ('select', 'ignore')
    module = 'pycodestyle'
    check_version = True

    # Internal
    report = None

    def check(self, code, filename):
        """Run pycodestyle on code and return the output."""
        options = {
            'reporter': self.get_report()
        }

        type_map = {
            'select': [],
            'ignore': [],
            'max-line-length': 0,
            'max-complexity': 0
        }

        self.build_options(options, type_map, transform=lambda s: s.replace('-', '_'))

        final_options = options.copy()

        # Try to read options from pycodestyle default configuration files (.pycodestyle, tox.ini).
        # If present, they will override the ones defined by Sublime Linter's config.
        try:
            # `onError` will be called by `process_options` when no pycodestyle configuration file is found.
            # Override needed to supress OptionParser.error() output in the default parser.
            def onError(msg):
                pass

            from pycodestyle import process_options, get_parser
            parser = get_parser()
            parser.error = onError
            pycodestyle_options, _ = process_options([os.curdir], True, True, parser=parser)

            # Merge options only if the pycodestyle config file actually exists;
            # pycodestyle always returns a config filename, even when it doesn't exist!
            if os.path.isfile(pycodestyle_options.config):
                pycodestyle_options = vars(pycodestyle_options)
                pycodestyle_options.pop('reporter', None)
                for opt_n, opt_v in pycodestyle_options.items():
                    if isinstance(final_options.get(opt_n, None), list):
                        final_options[opt_n] += opt_v
                    else:
                        final_options[opt_n] = opt_v
        except SystemExit:
            # Catch and ignore parser.error() when no config files are found.
            pass

        if persist.debug_mode():
            persist.printf('{} ST options: {}'.format(self.name, options))
            persist.printf('{} options: {}'.format(self.name, final_options))

        checker = self.module.StyleGuide(**final_options)

        return checker.input_file(
            filename=os.path.basename(filename),
            lines=code.splitlines(keepends=True)
        )

    def get_report(self):
        """Return the Report class for use by flake8."""
        if self.report is None:
            from pycodestyle import StandardReport

            class Report(StandardReport):
                """Provides a report in the form of a single multiline string, without printing."""

                def get_file_results(self):
                    """Collect and return the results for this file."""
                    self._deferred_print.sort()
                    results = ''

                    for line_number, offset, code, text, _ in self._deferred_print:
                        results += '{path}:{row}:{col}: {code} {text}\n'.format_map({
                            'path': self.filename,
                            'row': self.line_offset + line_number,
                            'col': offset + 1,
                            'code': code,
                            'text': text
                        })

                    return results

            self.__class__.report = Report

        return self.report
