iCalendar Aggregator
--------------------

This is a trivial iCalendar aggregator. It will pull in multiple iCalendar
feeds, and turn them into one. It will also generate a HTML format schedule
based on these iCalendar feeds.

This was developed to deal with the fact that some conferences publish their
schedule as a set of google calendars only, which becomes very much unreadable.
A few minutes worth of copy/paste of python from different places solved that
problem...

Configuration
=============
Configuration is simple. Create an INI-style file, and pass it on the commandline.
The file should have the following contents::
 
 [core]
 timezone=US/Eastern
 timezone_adjust_hours=-3
 
 [files]
 ical=testout.ics
 html=testout.html
 htmlheader=input.head
 htmlfooter=input.foot
 
 [rooms]
 room1=http://somewhere.com/schedule1.ics
 room number 2=http://elsehwere.com/schedule2.ics

The **timezone** parameter controls which timezone the generated HTML will be in. Any
timezone valid in the pytz library should work, which should mean all the normal Unix
timezone names.

The **timezone_adjust_hours** parameter lets you add or subtract a fixed number from
the *incoming* iCalendar feeds, to compensate for cases when the published calendar is
in the wrong timezone. The example -3 adjusts for a calendar that is published in PST
when it should have been published in EST. This parameter will affect **both** the HTML
and the iCalendar output files

For each **room**, just add the room name as parameter name, and the URL to the
iCalendar feed as the value.

The section **files** controls input and output files. The parameter **ical** sets the
output iCalendar feed, and the parameter **html** sets the output HTML file. The files
listed in **htmlheader** and **htmlfooter** will be prepended and appended, respectively,
to the HTML file before and after the actual contents.
