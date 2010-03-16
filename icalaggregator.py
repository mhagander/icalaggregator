#!/usr/bin/env python

import sys
import urllib2
from ConfigParser import ConfigParser
from StringIO import StringIO
from datetime import datetime, timedelta
from pytz import timezone, utc
from string import capwords

class Event(object):
	"""
	Represents a single event in the schedule.
	"""
	def __init__(self, timezone, timezone_adjust):
		"""
		timezone and timezone_adjust are the same parameters as in the Aggregator.
		"""
		self.timezone = timezone
		self.timezone_adjust = timezone_adjust
		self.summary = None
		self.start = None
		self.end = None
		self.location = None

	def validate(self):
		"""
		Validate that we have all the required fields for this event.
		Also validate taht we don't have any events going across multiple days,
		since the schedule generator can't deal with that.
		"""
		if not self.summary: raise Exception('Summary not set')
		if not self.start: raise Exception('Start not set')
		if not self.end: raise Exception('End not set')
		if self.start.astimezone(self.timezone).date() != self.end.astimezone(self.timezone).date():
			raise Exception('Can\'t deal with cross-day events')

	def setstart(self, v):
		"""Set the start time for the event, by parsing an iCalendar style date"""
		self.start = self._parse_time(v)

	def getstart(self):
		"""Return the start time for the event, in iCalendar format"""
		return self._print_time(self.start)

	def setend(self, v):
		"""Set the end time for the event, by parsing an iCalendar style date"""
		self.end = self._parse_time(v)
	def getend(self):
		"""Return the end time for the event, in iCalendar format"""
		return self._print_time(self.end)

	def _parse_time(self, v):
		"""
		Parse any iCalendar style datetime, and return it in a python object.
		The time is always returned in UTC, but will be adjusted using the
		timezone_adjust parameter if required.
		"""
		return utc.localize(datetime.strptime(v, "%Y%m%dT%H%M%SZ")) + timedelta(hours=self.timezone_adjust)

	def _print_time(self, v):
		"""
		Convert a date to iCalendar format.
		"""
		return v.strftime("%Y%m%dT%H%M%SZ")

	def __str__(self):
		return "%s - %s: %s" % (self.start, self.end, self.summary)

def compare_events(a,b):
	"""
	Compare two Events, used as parameter when sorting a list of Events.

	Comparison is done only on the start time.
	"""
	return cmp(a.start, b.start)

class IcalReader(object):
	"""
	Wrap simple reading of iCalendar data. The only thing it adds
	on top of a regular reader is at this point dealing with continued
	lines, where if a line starts with a space the contents are merged
	with the previous line.
	"""
	def __init__(self, f):
		self.lines = [l.rstrip() for l in f.readlines()]

	def readline(self):
		if not len(self.lines): return None

		s = StringIO()
		while True:
			s.write(self.lines.pop(0).lstrip())
			if not len(self.lines):
				break
			if not self.lines[0].startswith(" "):
				break

		return s.getvalue()

class Aggregator(object):
	"""
	Represents one set of iCalendar feeds being aggregated together to
	form one schedule.
	"""
	def __init__(self, timezone, timezone_adjust):
		"""
		Initialize the Aggregator object.

		timezone indicates which timezone to generate the output HTML
		using (iCalendar feeds are always generated in UTC).

		timezone_adjust allows for adjusting all *incoming* timestamps
		in the parsed iCalendar feeds with a fixed number of hours, to
		correct for incorrectly published feeds.
		"""
		self.feeds = []
		self.events = []
		self.timezone = timezone
		self.timezone_adjust = timezone_adjust

	def add_feed(self, name, url):
		"""
		Add a feed with room name "name" with an iCalendar feed at
		url. Does not actually fetch the URL at this time.
		"""
		self.feeds.append((name, url))

	def pull_all(self):
		"""
		Fetch all the iCalendar feeds specified, and parse them
		to event objects store in the local list.
		"""
		for feed, url in self.feeds:
			f = urllib2.urlopen(url)
			for event in self._parse_ical(f):
				event.location = feed
				self.events.append(event)
		self.events.sort(compare_events)

	def generate_ical(self):
		"""
		Generate an iCalendar format file with all the events
		in this aggregator.

		Returns the iCalendar data as a string.
		"""
		f = StringIO()
		f.write("""BEGIN:VCALENDAR\r
VERSION:2.0\r
PRODID:-//hagander/icalaggregator//NONSGML v1.0//EN\r
""")

		for event in self.events:
			f.write("BEGIN:VEVENT\r\n")
			f.write("DTSTART:%s\r\n" % event.getstart())
			f.write("DTEND:%s\r\n" % event.getend())
			f.write("SUMMARY:%s\r\n" % event.summary)
			f.write("LOCATION:%s\r\n" % (event.location or ''))
			f.write("END:VEVENT\r\n")
		f.write("END:VCALENDAR\r\n")
		return f.getvalue()

	def generate_html(self):
		"""
		Generate the core HTML schedule for the aggregated data. To look good,
		it obviously needs to be wrapped in some header and footer data elsewhere.

		Returns this HTML as a string.

		Implementation uses lots of inefficient scans etc, but given that it's
		never going to deal with more than hundreds of events at a time, it'll
		be fast enough...
		"""

		col_width = 150 # Width of each column
		headersize = 30 # Size of the header *for each day*

		rooms = {}
		days = []

		f = StringIO()

		for i in range(0, len(self.feeds)):
			rooms[self.feeds[i][0]] = i

		for e in self.events:
			if not e.start.date() in days:
				days.append(e.start.date())

		for day in sorted(days):
			# First out first and last this day (yes, it's inefficient, but we don't
			# have much data to deal with..)
			firsttime = None
			lasttime = None
			for e in self.events:
				if not e.start.date() == day: continue
				if not firsttime: firsttime = e.start
				lasttime = e.end

			f.write("<h2>%s</h2>\n" % day)
			f.write("<div class=\"schedwrap\" style=\"width: %spx; height: %spx; \">\n" % (
					len(rooms) * col_width, # width
					self._timediff_to_y_pixels(lasttime, firsttime) + headersize, # height
					))
			# Room headers
			for roomname, roomnum in rooms.items():
				f.write(" <div class=\"sessblock roomheader\" style=\"left: %spx; width: %spx; height:28px;\">%s</div>\n" % (
						roomnum*col_width, col_width-2, roomname,
						))

			# Now write all the sessions for this day
			for e in sorted(self.events):
				if not e.start.date() == day: continue
				f.write(" <div class=\"sessblock\" style=\"top: %spx; left: %spx; width: %spx; height: %spx;\">%s - %s<br/>%s</div>\n" % (
						self._timediff_to_y_pixels(e.start, firsttime) + headersize, # top
						col_width * rooms[e.location], # left
						col_width - 2, # width
						self._timediff_to_y_pixels(e.end, e.start) - 2, # height
						e.start.astimezone(self.timezone).strftime("%H:%M"),
						e.end.astimezone(self.timezone).strftime("%H:%M"),
						e.summary, # text
						))

			# Close this schedwrap
			f.write("</div>\n")
		return f.getvalue()

	def _timediff_to_y_pixels(self, t, compareto):
		"""
		Somewhat hackishly convert a difference in time into pixels,
		to draw a schedule.
		"""
		return ((t - compareto).seconds/60)*1.7

	def _parse_ical(self, f):
		"""
		Parse the ical data in the file stream f, yielding back all the
		events present in the feed.
		"""
		r = IcalReader(f)

		currevent = None
		while True:
			l = r.readline()
			if not l:
				raise Exception('End of stream')
			elif l == 'END:VCALENDAR':
				break
			elif l == 'BEGIN:VEVENT':
				if currevent: raise Exception('Recursive events?!')
				currevent = Event(self.timezone, self.timezone_adjust)
			elif l == 'END:VEVENT':
				if not currevent: raise Exception('End of nonexisting event?!')
				currevent.validate()
				yield currevent
				currevent = None
			elif l.startswith('DTSTART:'):
				currevent.setstart(l[8:])
			elif l.startswith('DTEND:'):
				currevent.setend(l[6:])
			elif l.startswith('SUMMARY:'):
				currevent.summary = l[8:].replace('\,', ',')
			else:
				pass # no error, just ignore...


def append_file(f, fn):
	"""
	Append the contents in the file with name fn to the open file f.
	"""
	f2 = open(fn, 'r')
	f.write(f2.read())
	f2.close()

if __name__=="__main__":
	c = ConfigParser()
	c.read(sys.argv[1])

	a = Aggregator(timezone(c.get('core', 'timezone')),
				   int(c.get('core', 'timezone_adjust_hours')))

	for name in c.options('rooms'):
		a.add_feed(capwords(name), c.get('rooms', name))
	a.pull_all()

	# Generate aggregate icalendar feed
	f = open(c.get('files', 'ical'),'w')
	f.write(a.generate_ical())
	f.close()

	# Generate HTML
	f = open(c.get('files', 'html'), 'w')
	if c.has_option('files', 'htmlheader'):
		append_file(f, c.get('files', 'htmlheader'))
	else:
		f.write("<link rel=\"stylesheet\" href=\"icalaggregator.css\"/>\n")
	f.write(a.generate_html())
	if c.has_option('files', 'htmlfooter'):
		append_file(f, c.get('files', 'htmlfooter'))
	f.close()
