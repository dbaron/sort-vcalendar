#!/usr/bin/python
# vim: set shiftwidth=4 expandtab tabstop=4:

# Sort a vCalendar file by the UID of the events.

# Copyright (c) 2014, L. David Baron <dbaron@dbaron.org>

# This script takes a vCalendar file and sorts any sequence of VEVENT
# sections within it by their UID, with the secondary sort key being
# their SEQUENCE.  The sort should be stable if there are any events
# that have duplicate UID and SEQUENCE, but I haven't tested this
# thoroughly.
#
# I find this script useful for storing backups of a calendar in a
# version control repository, when the calendar is generated in random
# order (as Google Calendar vCalendar files are).
#
# Sorting the events by their UID makes the diffs much smaller, and
# makes them usefully readable.

#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

from optparse import OptionParser
from operator import itemgetter
import sys

op = OptionParser()
(options, args) = op.parse_args()

if len(args) == 0:
    input = sys.stdin
elif len(args) == 1:
    input = open(args[0])
else:
    op.error("expected a single argument (filename) or none (stdin)")

# A vCalendar file contains sections of different names (foo) delimited
# by BEGIN:foo and END:foo.  Read them all in, preserving order, and
# checking only that the BEGIN/END pairs match.  Store everything as
# arrays of either strings or lines.
vcalfile = []
section_stack = [ vcalfile ]

def read_line(line, lineno):
    current_section = section_stack[-1]
    if line.startswith("BEGIN:"):
        new_section = [ line ]
        current_section.append(new_section)
        section_stack.append(new_section)
    elif line.startswith("END:"):
        # check the BEGIN: and the END: match
        if current_section[0][6:].rstrip("\r\n") != line[4:].rstrip("\r\n"):
            raise StandardError("section name mismatch at line " + lineno)

        current_section.append(line)
        section_stack.pop()
    else:
        current_section.append(line)

lineno = 1
for line in input:
    read_line(line, lineno)
    lineno += 1

if section_stack != [ vcalfile ]:
    raise StandardError("incomplete file")

def is_section(item):
    return type(item) == list

def is_event(item):
    return type(item) == list and item[0].rstrip("\r\n") == "BEGIN:VEVENT"

def find_key(event):
    uid = None
    sequence = None
    for item in event:
        if not is_section(item):
            if item.startswith("UID:"):
                itemuid = item[4:].rstrip("\r\n")
                if uid is not None:
                    raise StandardError("duplicate UIDs " + uid + " and " + itemuid)
                uid = itemuid
            elif item.startswith("SEQUENCE:"):
                itemsequence = item[9:].rstrip("\r\n")
                if sequence is not None:
                    raise StandardError("duplicate SEQUENCEs " + sequence + " and " + itemsequence)
                sequence = itemsequence
    if uid is None:
        raise StandardError("event without UID")
    if sequence is None:
        raise StandardError("event without SEQUENCE")
    return (uid, int(sequence))

def flush_event_stack(stack):
    if len(stack) == 0:
        return
    keys_and_events = [ (find_key(event), event) for event in stack ]
    for [key, event] in sorted(keys_and_events, key=itemgetter(0)):
        emit(event)

def emit(section):
    event_stack = []
    for item in section:
        if is_event(item):
            event_stack.append(item)
        else:
            flush_event_stack(event_stack)
            event_stack = []
            if is_section(item):
                emit(item)
            else:
                sys.stdout.write(item)

emit(vcalfile)
