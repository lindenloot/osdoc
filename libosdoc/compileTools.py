# -*- coding: utf-8 -*-

"""
This file is part of osdoc.

osdoc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

osdoc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with osdoc.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import yaml
import re
import shutil
import subprocess
import csv
from md5 import md5
from libosdoc.versions import generateVersionList, branchStatus
from libosdoc.pdf import pdfWalk
from libosdoc.gitinfo import setGitInfo, gitBranch

def getInfo(path):

	"""
	desc:
		Retrieves YAML info from a Markdown document.

	arguments:
		path:	The path to the document.

	returns:
		A dictionary with YAML info.
	"""

	s = open(path).read().decode(u'utf-8')
	l = s.split(u'---')
	if len(l) < 3:
		print u'getInfo(): Failed to parse %s' % path
		return None
	y = yaml.load(l[1])
	return y

def setInfo(path, i):

	"""
	desc:
		Modifies the YAML info inside a Markdown document. The file is not
		modified directly, but returned as a string.

	arguments:
		path:	The path to the document.
		i:		A dictionary with the YAML info.

	returns:
		A string with the modified document.
	"""

	# Sortkey has to be string, otherwise it will not be parsed correctly by
	# yaml
	s = open(path).read().decode(u'utf-8')
	l = s.split(u'---')
	if len(l) < 3:
		return None
	yml = u''
	for key, value in i.iteritems():
		yml += u'%s: %s\n' % (key, value)
	l[1] = yml
	s = u'---\n' + u'---'.join(l[1:])
	return s

def listContent(dirname=u'content', l=[]):

	"""
	desc:
		Lists all content files in a given directory.

	keywords:
		dirname:	The content directory or None to use the last command line
					parameter.
		l:			A list to append the files to (for recursion purposes).

	returns:
		A list of all content Markdown files.
	"""

	print(u'\nListing content (%s) ...' % dirname)
	for basename in os.listdir(dirname):
		if basename.startswith(u'_'):
			continue
		path = os.path.join(dirname, basename)
		if os.path.isdir(path):
			l = listContent(dirname=path, l=l)
		elif basename.endswith(u'.md'):
			i = getInfo(path)
			if i != None:
				l.append((path, i))
				print(u'+ %s (%d)' % (path, len(l)))
	return l

def callOptimizeHTML(path):

	"""
	desc:
		Recursively compresses all HTML files in the path using
		htmlcompressor.jar

	arguments:
		path:	The folder path to optimize.
	"""

	for fname in os.listdir(path):
		fname = os.path.join(path, fname)
		if os.path.isdir(fname):
			callOptimizeHTML(fname)
		elif fname.lower().endswith(u'.html'):
			s1 = os.path.getsize(fname)
			cmd = [u'java', u'-jar', u'htmlcompressor.jar', u'--compress-js',
				fname, u'-o', fname]
			subprocess.call(cmd)
			s2 = os.path.getsize(fname)
			print u'Optimized:\t%s (%d kB -> %d kB, %d%%)' % (fname, s1, s2,
				(100.*s2/s1))

def adjustRootRelativeURLs(path, branch):

	"""
	desc:
		Recursively walks through a folder and replaces all root-relative URLs
		by a branched URL. Processes HTML and CSS files.

	arguments:
		path:		The path to walk through.
		branch:		The branch to add.
	"""

	print(u'Adjusting root-relative URLs (%s)' % path)
	for fname in os.listdir(path):
		fname = os.path.join(path, fname)
		if os.path.isdir(fname):
			adjustRootRelativeURLs(fname, branch)
			continue
		if fname.lower().endswith(u'.html'):
			html = open(fname).read().decode(u'utf-8')
			regex = u'(?P<_type>href|src)\\s*=\\s*["\'](?P<url>/.*?)["\']'
			for g in re.finditer(regex, html):
				url = g.group(u'url')
				if url.startswith(u'//'):
					print(u'Ignoring odd URL in %s: %s' % (fname, url))
					continue
				old = g.group()
				new = u'%s="/%s%s"' % (g.group(u'_type'), branch, url)
				html = html.replace(old, new)
			open(fname, u'w').write(html.encode(u'utf-8'))
		elif fname.lower().endswith(u'.css'):
			css = open(fname).read().decode(u'utf-8')
			open(fname, u'w').write(css.encode(u'utf-8'))
			regex = u'url\(["\'](?P<url>.*?)["\']\)'
			for g in re.finditer(regex, css):
				url = g.group(u'url')
				if url.startswith(u'//'):
					print(u'Ignoring odd URL in %s: %s' % (fname, url))
					continue
				old = g.group()
				new = u'url(\'/%s%s\')' % (branch, url)
				css = css.replace(old, new)
			open(fname, u'w').write(css.encode(u'utf-8'))

def copyFile(fromPath, toPath):

	"""
	Copies a file and creates the target folder structure if it doesn't exist.

	Arguments:
	fromPath	--	The source file.
	toPath		--	The target file.
	"""

	if not os.path.exists(os.path.dirname(toPath)):
		os.makedirs(os.path.dirname(toPath))
	shutil.copyfile(fromPath, toPath)

def parseOsdocYaml(path, info, s):

	"""
	Parses OSDOC-specific YAML sections to implement specific functionality.

	Arguments:
	path	--	The path to the page.
	info	--	A dictionaty with the page's front matter.
	s		--	A string with the page content.

	Returns:
	A string with the parsed page contents.
	"""

	import re
	from academicmarkdown import build, HTMLFilter

	print u'Parsing %s (%s) with academicmarkdown' % (info[u'title'], path)
	# We need to find all images, and copy these to the _content folder
	for r in re.finditer(u'%--(.*?)--%', s, re.M|re.S):
		try:
			d = yaml.load(r.groups()[0])
		except:
			print u'Invalid YAML block: %s' % r.groups()[0]
			continue
		if not u'figure' in d:
			continue
		src = os.path.join(path, u'img', info['permalink'][1:], \
			d[u'figure'][u'source'])
		print u'Copying %s' % src
		copyFile(src, u'_'+src)
	# Add all source paths to the build path, so that we can reference to
	# figures etc without considering paths
	build.path += [os.path.join(path, u'img', info['permalink'][1:]), \
		os.path.join(path, u'lst', info['permalink'][1:]), \
		os.path.join(path, u'tbl', info['permalink'][1:])]
	# Set the correct templates
	build.codeTemplate = u'jekyll'
	build.figureTemplate = u'jekyll'
	build.tableTemplate = u'kramdown'
	# Disable markdown filters
	build.preMarkdownFilters = []
	build.postMarkdownFilters = []
	# Enable clickable anchor headers
	build.TOCAnchorHeaders = True
	build.TOCAppendHeaderRefs = True
	s = build.MD(s)
	s = HTMLFilter.DOI(s)
	# Remove the content/ part of figure paths, because it does not apply to
	# the generated site.
	s = s.replace(u'![content/', u'![/')
	s = s.replace(u'(content/', u'(/')
	# Remove the three newly added entries from the build path.
	build.path = build.path[:-3]
	return s

def gitInfo(path):

	"""
	desc:
		Generates a string with git information for a given page.

	arguments:
		path:	The path to the page.

	returns:
		A string with git info.
	"""

	cmd = [u'git', u'log', u'--format="Revision <a href=\'https://github.com/smathot/osdoc/commit/%H\'>#%h</a> on %cd"', u'-n', u'1', path]
	out, err = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()
	return out

def compileLess():

	"""
	desc:
		Compiles the less stylesheets to css.
	"""

	print(u'\nCompiling .less to .css ...')
	cmd = ['lesscpy', '-X', 'content/stylesheets/main.less']
	subprocess.call(cmd, stdout=open(u'_content/stylesheet.css', u'w'))

def copyResources(layout):

	"""
	desc:
		Copies non-Markdown resources.
	"""

	print(u'\nCopying non-page resources ...')
	shutil.copytree(u'content/_includes', u'_content/_includes')
	shutil.copytree(u'content/_layouts', u'_content/_layouts')
	shutil.copytree(u'content/attachments', u'_content/attachments')
	shutil.copytree(u'content/img', u'_content/img')
	shutil.copy(u'content/favicon.ico', u'_content/favicon.ico')
	shutil.copy(u'content/_layouts/osdoc-%s.html' % (layout),
		u'_content/_layouts/osdoc.html')

def preprocessMarkdown(content, group):

	"""
	desc:
		Pre-processes the markdown source with academicmarkdown.
	"""

	print(u'\nCompiling pages ...')
	sortkey = [0,0]
	_group = 'General'
	sitemap = open('sitemap.txt').read().decode(u'utf-8')
	for title in sitemap.split(u'\n'):
		if title.startswith(u'#') or title.strip() == u'':
			continue
		if title.startswith(u'\t'):
			sortkey[1] += 1
			level = 1
		else:
			sortkey[0] += 1
			level = 0
		title = title.strip()
		if title.startswith(u':'):
			show = False
			title = title[1:]
		else:
			show = True
		i = 0
		for path, info in content:
			if info[u'title'].lower() == title.lower():
				# Strip of the 'content' bit from the path and prepend the
				# target path.
				targetPath = '_'+path
				if level > 0:
					print u'\t',
				else:
					_group = info[u'group']
				print '-> %s (%s)' % (title, path)
				info[u'show'] = show
				info[u'sortkey'] = u'%.3d.%.3d' % (sortkey[0], sortkey[1])
				info[u'level'] = level
				info[u'group'] = _group
				info[u'figures'] = 0
				info[u'videos'] = 0
				info[u'listings'] = 0
				info[u'tables'] = 0
				info[u'gitinfo'] = gitInfo(path)
				info[u'gitlink'] = \
					u'https://github.com/smathot/osdoc/blob/master/%s' \
					% path
				if group == None or group.lower() == \
					_group.lower() or title.lower() == u'home':
					s = setInfo(path, info)
					# Fix missing alt tags
					s = s.replace(u'![](', u'![No alt text specified](')
					s = parseOsdocYaml(os.path.dirname(path), info, s)
					if not os.path.exists(os.path.dirname(targetPath)):
						os.mkdir(os.path.dirname(targetPath))
					open(targetPath.encode(sys.getfilesystemencoding()), \
						u'w').write(s.encode(u'utf-8'))
				i += 1
		if i > 1:
			raise Exception(u'Multiple matches for "%s"' % title)
		if i == 0:
			raise Exception(u'Failed to find "%s"' % title)

def runJekyll(status):

	"""
	desc:
		Compiles the site to HTML with Jekyll.
	"""

	print(u'\nCreating _config.yml')
	cfg = {
		'notifications' : False,
		'status' : status,
		'pygments':	True,
		'markdown': 'kramdown',
		'source': '_content',
		'destination': '_tmp',
		}
	yaml.dump(cfg, open('_config.yml', 'w'))
	print u'\nLaunching jekyll'
	subprocess.call([u'jekyll'])

def createTarball(siteFolder):

	"""
	desc:
		Creates a tarball of the site.
	"""

	print(u'\nCreating tarball (osdoc.tar.gz)')
	cmd = [u'tar', u'-zcvf', u'osdoc.tar.gz', u'-C', siteFolder, u'.', \
		u'--exclude-from=dev-scripts/excludefromgz.txt']
	subprocess.call(cmd)
	shutil.move(u'osdoc.tar.gz', siteFolder)

def checkDeadLinks(branch):

	"""
	desc:
		Checks the site for dead links.
	"""

	print(u'\nChecking for dead links')
	cmd = [u'linkchecker', u'--no-warnings', u'-o', u'csv', \
		u'http://localhost:8000/%s' % branch]
	subprocess.call(cmd, stdout=open(u'deadlinks.log', u'w'))
	nErr = 0
	for l in open(u'deadlinks.log').read().decode(u'utf-8').split(
		u'\n')[4:]:
		r = l.split(u';')
		if len(r) < 6 or r[0] == u'urlname':
			continue
		url = r[0]
		# Don't check index.pdf pages, as they are generated later on, and
		# don't check e-mail addresses.
		if url.endswith(u'index.pdf') or url.startswith(u'mailto:'):
			continue
		parent = r[1]
		warning = r[3]
		valid = r[5] == u'False'
		nErr += 1
		print '%s\n\tin %s' % (url, parent)
	print u'%d dead link(s) found' % nErr

def compileSite(layout=u'inpage', group=None, jekyll=True, optimizeHTML=False,
	tarball=False,	checkLinks=False, gitInfo=False):

	"""
	desc:
		Compiles the site.

	keywords:
		layout:
			desc:	Indicates the layout to be used. Should be 'fullpage' or
					'inpage'.
			type:	[str, unicode]
		group:
			desc:	The name of a group (subsection) to speed up compilation for
					debugging purposes.
			type:	[str, unicode, NoneType]
		jekyll:
			desc:	Indicates whether Jekyll should be called to compile the
					site source to HTML.
			type:	bool
		optimizeHTML:
			desc:	Indicates whether HTML should be optimized/ minified.
			type:	bool
		tarball:
			desc:	Indicates whether a tarball of the site should be generated.
			type:	bool
		checkLinks:
			desc:	Indicates whether the site should be checked for dead links.
			type:	bool
		gitInfo:
			desc:	Indicates whether gitinfo should be updated.
			type:	bool

	returns:
		desc:	The folder where the site has been generated.
		type:	unicode
	"""

	assert(layout in [u'fullpage', u'inpage'])
	branch = gitBranch()
	status = branchStatus(branch)
	print(u'Branch:\t%s\nStatus:\t%s\n' % (branch, status))
	if gitInfo:
		setGitInfo()
	print(u'\nRecreating _content ...')
	if os.path.exists('_content'):
		shutil.rmtree('_content')
	os.makedirs('_content')
	copyResources(layout)
	generateVersionList(branch)
	compileLess()
	content = listContent(l=[])
	preprocessMarkdown(content=content, group=group)
	if jekyll:
		runJekyll(status)
	if branch != '':
		adjustRootRelativeURLs('_tmp', branch)
		siteFolder = u'_site/%s' % branch
	else:
		siteFolder = u'_site'
	print(u'Moving site to %s' % siteFolder)
	if os.path.exists(siteFolder):
		shutil.rmtree(siteFolder)
	shutil.move(u'_tmp', siteFolder)
	if optimizeHTML:
		callOptimizeHTML(siteFolder)
	if tarball:
		createTarball(siteFolder)
	if checkLinks:
		checkDeadLinks(branch)
	return siteFolder
