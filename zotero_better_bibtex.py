"""
Integration with zotero better bibtex
"""
# > Imports
from functools import partial
from contextlib import closing
from textwrap import dedent
from sys import platform
import subprocess

from urllib.request import urlopen
from urllib.parse import urlencode, urlunparse,ParseResult

import sublime
import sublime_plugin

# > Constants

# >> URL of bbtex server/api
BBTEX_SCHEME = 'http'
BBTEX_NETLOC = '127.0.0.1:23119'  # localhost, port 23119
BBTEX_PATH = '/better-bibtex/cayw'

# >> default query for api
DEFAULT_CAYW_QUERY = {'format': 'citep'}


# >> Window Refocus

# async

# necessary as zotero retains focus
# probably requires async operation
if platform == "darwin":
	def refocus_sublime():  #type: ignore
		# print('refocus!')
		output = subprocess.check_output([
				"osascript", "-e",
				'activate application "Sublime Text"'],
			)
		return output
		# command = '''osascript -e \'activate application "Sublime Text"\' &'''
		# output = subprocess.check_output(command, shell=True)
		# return output

		# p = subprocess.Popen([
		# 		"osascript", "-e",
		# 		'activate application "Sublime Text"'],
		# 		stdout = subprocess.PIPE
		# 	)
		# p.wait(5)
		# return p.stdout.read().decode()  # type: ignore
# Yea ... need other OS solutions here
else:
	def refocus_sublime():
		return



# > Utility Functions

def insert_at_cursor(edit, view, text):
    sel = view.sel()[0].begin()
    view.insert(edit, sel, text)


def url_from_params(base: dict, **params):
	'''Generate a url from dictionaries of the base url and query params

	base must contain keys {'scheme', 'netloc', 'path'}
	eg: {'scheme': 'http', 'netloc': '127.0.0.1:23119', 'path': '/better-bibtex/cayw'}

	params kwargs are used as a dict to provide individual query params for the url

	Consider using functools.partial to set the base of the url
	'''

	base_required_keys = {'scheme', 'netloc', 'path'}
	assert (len(base_required_keys.difference(base.keys())) == 0), 'must provide "scheme", "netloc" and "path"'

	actual_parse_args = {"params": '', "fragment": ''}
	actual_parse_args.update(base)
	actual_parse_args['query'] = urlencode(params)

	parse_obj = ParseResult(**actual_parse_args)
	url = urlunparse(parse_obj)

	return url

def get_request(url: str) -> str:

	with closing(urlopen(url)) as response:
		response_text = response.read().decode()

	return response_text


# easy generation of URLs for better bibtex api/server
bbtex_base_url = partial(
	url_from_params,
	{'scheme': BBTEX_SCHEME, 'netloc': BBTEX_NETLOC, 'path': BBTEX_PATH}
	)

def test_bbtex_api():
	try:
		probe_url = bbtex_base_url(probe=True)
		probe_resp = get_request(probe_url)

		return True

	except Exception as exp:
		message = dedent(f"""Could not access API!
			API Base URL: {bbtex_base_url()}
			Exception:
			{exp}
		""")
		sublime.error_message(message)


def bbtex_cayw_request(**kwargs: str):

	# create desired URL for requesting the better bibtex API
	query_params = kwargs if kwargs else DEFAULT_CAYW_QUERY
	citation_url = bbtex_base_url(**query_params)

	# open the request, grab the return text and close the connection
	with closing(urlopen(citation_url)) as zot_result:
		citation = zot_result.read().decode()

	return citation


# > Commands

# >> Gui TextCommand

class ZoteroCaywCommand(sublime_plugin.TextCommand):

	def run(self, edit, **query_params):

		# test connection
		if not test_bbtex_api():
			return

		citation = bbtex_cayw_request(**query_params)
		sublime.set_timeout_async(refocus_sublime)

		insert_at_cursor(edit, self.view, citation)
