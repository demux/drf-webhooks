"""
This type stub file was generated by pyright.
"""

'''
timeparse.py
(c) Will Roberts <wildwilhelm@gmail.com>  1 February, 2014

Implements a single function, `timeparse`, which can parse various
kinds of time expressions.
'''
SIGN = ...
WEEKS = ...
DAYS = ...
HOURS = ...
MINS = ...
SECS = ...
SEPARATORS = ...
SECCLOCK = ...
MINCLOCK = ...
HOURCLOCK = ...
DAYCLOCK = ...
OPT = ...
OPTSEP = ...
TIMEFORMATS = ...
COMPILED_SIGN = ...
COMPILED_TIMEFORMATS = ...
MULTIPLIERS = ...
def timeparse(sval, granularity=...): # -> int | float | None:
    '''
    Parse a time expression, returning it as a number of seconds.  If
    possible, the return value will be an `int`; if this is not
    possible, the return will be a `float`.  Returns `None` if a time
    expression cannot be parsed from the given string.

    Arguments:
    - `sval`: the string value to parse

    >>> timeparse('1:24')
    84
    >>> timeparse(':22')
    22
    >>> timeparse('1 minute, 24 secs')
    84
    >>> timeparse('1m24s')
    84
    >>> timeparse('1.2 minutes')
    72
    >>> timeparse('1.2 seconds')
    1.2

    Time expressions can be signed.

    >>> timeparse('- 1 minute')
    -60
    >>> timeparse('+ 1 minute')
    60
    
    If granularity is specified as ``minutes``, then ambiguous digits following
    a colon will be interpreted as minutes; otherwise they are considered seconds.
    
    >>> timeparse('1:30')
    90
    >>> timeparse('1:30', granularity='minutes')
    5400
    '''
    ...
