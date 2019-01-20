#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Factor things common to git and svn."""

import abc
import datetime as dt

import pandas as pd

from . import internals
from . import pbar


class LogEntry:
    """Data structure to hold git or svn data entries."""

    __slots__ = ['revision', 'author', 'date', 'textmods', 'kind', 'action',
                 'propmods', 'path', 'message', 'added', 'removed']

    def __init__(self, revision=None, author=None, date=None, textmods=None,
                 kind=None, action=None, propmods=None, path=None, message=None,
                 added=0, removed=0):
        self.revision = revision
        self.author = author
        self.date = date
        self.textmods = textmods
        self.kind = kind
        self.action = action
        self.propmods = propmods
        self.path = path
        self.message = message
        self.added = added
        self.removed = removed

    @property
    def changed(self):
        """Sum of lines added and lines removed."""
        return self.added + self.removed

    def astuple(self):
        """Return the data as tuple."""
        return (getattr(self, slot) for slot in self.__slots__)


def _to_dataframe(log_entries):
    """Convert log entries to a pandas DataFrame.

    :param iter(LogEntry) log_entries: records generated by the SCM log command.
    :rtype pandas.DataFrame:

    """
    columns = LogEntry.__slots__
    tuples = [log_entry.astuple() for log_entry in log_entries]
    result = pd.DataFrame.from_records(tuples, columns=columns)
    result['date'] = pd.to_datetime(result['date'], utc=True)
    # FIXME categorize columns that should be categorized.
    return result


class _ScmLogCollector(abc.ABC):
    """Base class for svn and git.

    def get_log(self) is to be implemented in subclasses.

    """

    def __init__(self, after=None, before=None, path='.', progress_bar=None):
        """Initialize.

        Args:
            after: start date of log entries.
            before: end date of log entries (default to latest).
            path: location of local source repository.
            progress_bar: implements tqdm.tqdm interface.

        """
        self.path = path
        for date in [before, after]:
            if date and date.tzinfo is None:
                raise ValueError('dates are expected to be tzinfo-aware')
        self.after = after or internals.get_now() - dt.timedelta(365)
        self.before = before
        self.progress_bar = progress_bar
        if self.progress_bar is not None and self.after is None:
            raise ValueError("progress_bar requires 'after' parameter")

    def process_output_to_df(self, cmd_output):
        """Factor creation of dataframe from output of command.

        Args:
            cmd_output: generator returning lines of output from the cmd line.

        Returns:
              pandas.DataFrame

        """
        assert not isinstance(cmd_output, str)  # FIXME: better way to check.
        log_entries = []
        with pbar.ProgressBarAdapter(self.progress_bar,
                                     self.after) as progress_bar:
            for entry in self.get_log_entries(cmd_output):
                log_entries.append(entry)
                progress_bar.update(entry.date)
        df = _to_dataframe(log_entries)
        return df

    @abc.abstractmethod
    def get_log(self):
        """Call git log and return the log entries as a DataFrame.

        Returns:
            pandas.DataFrame.

        """
        pass

    @abc.abstractmethod
    def get_log_entries(self, cmd_output):
        """Convert output of git log --xml -v to a csv.

        Args:
            cmd_output: iterable of string (one for each line).

        Yields:
            tuple of :class:`codemetrics.scm.LogEntry`.

        """
        pass
