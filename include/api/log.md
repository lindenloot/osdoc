<div class="ClassDoc YAMLDoc" id="log" markdown="1">

# instance __log__

The `log` object provides data logging. A `log` object is created
automatically when the experiment starts.

__Example__:

~~~ .python
# Write one line of text
log.write(u'My custom log message')
# Write all variables
log.write_vars()
~~~

[TOC]

<div class="FunctionDoc YAMLDoc" id="log-close" markdown="1">

## function __log\.close__\(\)

Closes the current log.

__Example:__

~~~ .python
log.close()
~~~

</div>

<div class="FunctionDoc YAMLDoc" id="log-open" markdown="1">

## function __log\.open__\(path\)

Opens the current log. If a log was already open, it is closed automatically, and re-opened.

__Example:__

~~~ .python
# Open a new log
log.open(u'/path/to/new/logfile.csv')
~~~

__Arguments:__

- `path` -- The path to the current logfile. In most cases (unless) a custom log back-end is used, this will be a filename.
	- Type: str, unicode

</div>

<div class="FunctionDoc YAMLDoc" id="log-write" markdown="1">

## function __log\.write__\(msg, newline=True\)

Write one message to the log.

__Example:__

~~~ .python
# Write a single string of text
log.write(u'time = %s' % clock.time())
~~~

__Arguments:__

- `msg` -- A text message. When using Python 2, this should be either `unicode` or a utf-8-encoded `str`. When using Python 3, this should be either `str` or a utf-8-encoded `bytes`.
	- Type: str, unicode

__Keywords:__

- `newline` -- Indicates whether a newline should be written after the message.
	- Type: bool
	- Default: True

</div>

<div class="FunctionDoc YAMLDoc" id="log-write_vars" markdown="1">

## function __log\.write\_vars__\(var\_list=None\)

Writes variables to the log.

__Example:__

~~~ .python
# Write all variables to the logfile
log.write_vars()
~~~

__Keywords:__

- `var_list` -- A list of variable names to write, or None to write all variables that exist in the experiment.
	- Type: list, NoneType
	- Default: None

</div>

</div>

