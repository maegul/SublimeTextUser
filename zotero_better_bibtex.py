"""
Integration with zotero better bibtex
"""
# > Imports
from functools import partial
from contextlib import closing
from textwrap import dedent
from sys import platform
import subprocess
import json

from typing import Optional, Sequence

from urllib.request import Request, urlopen
from urllib.parse import urlencode, urlunparse,ParseResult

import sublime
import sublime_plugin

# > Constants

# >> URL of bbtex server/api
BBTEX_SCHEME = 'http'
BBTEX_NETLOC = '127.0.0.1:23119'  # localhost, port 23119
BBTEX_PATH = '/better-bibtex/cayw'
BBTEX_BASE_URL_COMPONENTS = {'scheme': BBTEX_SCHEME, 'netloc': BBTEX_NETLOC, 'path': BBTEX_PATH}

BBTEX_JSONRPC_URL = 'http://localhost:23119/better-bibtex/json-rpc'
BBTEX_JSONRPC_HEADERS = {
	'Content-Type': 'application/json',
	'Accept':'application/json'
}

# PRESUMED SHALLOW FOR COPYING LATER!!!
BBTEX_JSONRPC_SEARCH_DATA = {
	'jsonrpc':'2.0',
	'method':'item.search',
	'params': ['']  # to be updated
}

BBTEX_JSONRPC_BILBIOGRAPHY_DATA = {
	'jsonrpc':'2.0',
	'method': 'item.bibliography',
	'params': [  # to be updated
		# [],  # add citekeys to this list
		# {'quickCopy': True, 'contentType': 'text'}
	]
}

BBTEX_JSONRPC_BILBIOGRAPHY_DATA_PARAMS_FORMAT = {
	'quickCopy': True,
	'contentType': 'text'
}

# >> default queries and headers
DEFAULT_CAYW_QUERY = {'format': 'citep'}
DEFAULT_CITATION_FORMAT = 'citep'



# >> Window Refocus

# necessary as zotero retains focus
if platform == "darwin":
	def refocus_sublime():  #type: ignore
		# print('refocus!')
		output = subprocess.check_output([
				"osascript", "-e",
				'activate application "Sublime Text"'],
			)
		return output

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


# easy generation of URLs for better bibtex api/server
bbtex_base_url = partial(
	url_from_params,
	BBTEX_BASE_URL_COMPONENTS
	)


def get_request(url: str) -> str:

	with closing(urlopen(url)) as response:
		response_text = response.read().decode()

	return response_text


def post_request(url: str, data: dict, headers: dict):

	data_encoded = json.dumps(data).encode('utf-8')
	req = Request(url, data=data_encoded, headers=headers, method='POST')

	with closing(urlopen(req)) as response:
		response_text = response.read().decode()

	return response_text

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


def bbtex_search_request(params: str):

	data = BBTEX_JSONRPC_SEARCH_DATA.copy()  # presumes shallow!
	data['params'] = [params]

	response = post_request(
		url = BBTEX_JSONRPC_URL,
		data = data,
		headers=BBTEX_JSONRPC_HEADERS
		)

	results_data = json.loads(response)

	return results_data


def bbtex_bibliography_data(citekeys: list):
	data = BBTEX_JSONRPC_BILBIOGRAPHY_DATA.copy()
	data['params'] = [
		citekeys,
		BBTEX_JSONRPC_BILBIOGRAPHY_DATA_PARAMS_FORMAT
	]


	return data


def bbtex_bibliography_request(citekeys: list):

	data = bbtex_bibliography_data(citekeys)
	response = post_request(
		url = BBTEX_JSONRPC_URL,
		data = data,
		headers = BBTEX_JSONRPC_HEADERS
		)

	result_data = json.loads(response)

	# only meaningful part of the response
	return result_data['result']


def parse_source(data: dict):

	parsed_data = {}

	# author
	author_data = data.get('author', '-')
	if isinstance(author_data, (list, tuple)):
		parsed_data['first_author_text'] = author_data[0].get('family', '-')
		if len(author_data) > 1:
			parsed_data['author_text'] = f"{parsed_data['first_author_text']}, {author_data[-1].get('family', '-')}"
		else:
			parsed_data['author_text'] = f"{parsed_data['first_author_text']}"

	# title
	parsed_data['title_text'] = data.get('title', '-')

	# date
	try:
		parsed_data['date_text'] = data['issued']['date-parts'][0][0]
	except Exception:
		parsed_data['date_text'] = '-'

	# container
	parsed_data['container_text'] = data.get('container-title', '-')

	# aggregates
	parsed_data['source_text'] = f"{parsed_data['author_text']} {parsed_data['title_text']} ({parsed_data['date_text']}) {parsed_data['container_text']}"
	parsed_data['source_details'] = fr"<b>{parsed_data['date_text']}</b> <i>{parsed_data['container_text']}</i>"

	return parsed_data


def process_source_data(s: dict):

	# >>! Need to handle missing keys or data
	# this function breaks and the whole plugin breaks!!
	if len(s['author']) > 1:
		author_text = f"{s['author'][0]['family']}, {s['author'][-1]['family']}"
	else:
		author_text = f"{s['author'][0]['family']}"

	source_date = s['issued']['date-parts'][0][0]
	source_container = s['container-title']

	source_text = f"{author_text}-{s['title']} ({source_date}) {source_container}"

	source_details = fr"<b>{source_date}</b> <i>{source_container}</i>"

	return source_text, source_details


def make_listinput_item(s: dict, i: int):
	# text, details = process_source_data(s)
	parsed_obj = parse_source(s)

	# >>! use a custom object to parse all needed details once
	# and store the objects for convenient retrieval later
	# return sublime.ListInputItem(text, {'idx': i, 'source': s}, details)
	return sublime.ListInputItem(parsed_obj['source_text'], {'idx': i, 'source': s, 'parsed_obj': parsed_obj}, parsed_obj['source_details'])


# def make_preview_html(s: dict):
# 	auth_text = s['author'][0]['family']
# 	date_text = s['issued']['date-parts'][0][0]
# 	container_text = s['container-title']
# 	title_text = s['title']

# 	html_code = dedent(f'''
# 		<div style="border: 1px solid color(var(--foreground) alpha(35%)); padding: 4px">
# 		<p style="margin: 0px"><b>{auth_text}</b> ({date_text}) <i>{container_text}</i>
# 		<p style="margin: 0px; padding-top:2px">{title_text}</p>
# 		</div>
# 	''')

# 	return sublime.Html(html_code)
def make_preview_html(s: dict):
	author_text, date_text, container_text, title_text = (
			s['author_text'], s['date_text'], s['container_text'], s['title_text']
		)

	html_code = dedent(f'''
		<div style="border: 1px solid color(var(--foreground) alpha(35%)); padding: 4px">
		<p style="margin: 0px"><b>{author_text}</b> ({date_text}) <i>{container_text}</i>
		<p style="margin: 0px; padding-top:2px">{title_text}</p>
		</div>
	''')

	return sublime.Html(html_code)



# > Commands

# >> CAYW (cite as your write) TextCommand

class ZoteroCaywCommand(sublime_plugin.TextCommand):

	def run(self, edit, **query_params):

		# test connection
		if not test_bbtex_api():
			return

		citation = bbtex_cayw_request(**query_params)
		sublime.set_timeout_async(refocus_sublime)

		insert_at_cursor(edit, self.view, citation)


# >> General Search and Cite

# Using the better bibtex export (JSONRPC) API for searching and exporting full bibliographies

class ZoteroSearchParamsInputHandler(sublime_plugin.TextInputHandler):
	'''Text input for input to quick search (auth, year, title)
	'''

	def __init__(self, selected_sources: Optional[Sequence] = None):

		# selected sources for carrying over previous selections
		# to new instances of a selection input or search input
		# so that the final citation can contain sources from multiple input handlers
		if selected_sources:
			self.selected_sources = selected_sources
		else:
			# default to empty list so that can be run as initial input handler
			self.selected_sources = []

	def placeholder(self):
		return 'Search author, title or year'

	def next_input(self, args):
		# >>> run actual search
		# get params from this input handler
		search_params = args['zotero_search_params']
		response = bbtex_search_request(params=search_params)

		# select source from list of sources in response
		return ZoteroSourceInputHandler(response['result'], selected_sources = self.selected_sources)


class ZoteroSourceInputHandler(sublime_plugin.ListInputHandler):
	'''Select source from list of multiple sources
	'''

	def __init__(self, results, selected_sources=None, precompiled_items=False):
		self.precompiled_items = precompiled_items
		# results from free quick search
		# list of sources generated from the search
		# OR, if precompiled, the items to be listed for selection
		self.results = results

		# carryover any previously selected sources
		# from this same source_input_handler or another search
		if selected_sources:
			self.selected_sources = selected_sources
		else:
			self.selected_sources = []

	def list_items(self):
		# >>>! don't make for every recursion if possible!
		if self.precompiled_items:
			self.items = self.results
			return (self.results, 1)
		else:
			items = [
				# item for opting out of this list to cite or run another search
				sublime.ListInputItem(
					'Done',
					# passing selected sources in Done allows to be passed to final command
					# idx: None used for conditionals elsewhere
					{'idx': None, 'source': self.selected_sources},
					"Search again or cite")
				]

			# adding sources (as listinput items) to list of options
			for i, s in enumerate(self.results):
				items.append(make_listinput_item(s, i))
			self.items = items  # for passing as precompiled items

			#              V--> "1" means initial selection at index 1 (second) item
			return (items, 1)

	def preview(self, value):
		if value['idx'] is not None:  # ie, an actual source
			return make_preview_html(value['parsed_obj'])
		elif value['idx'] is None:
			# hack to prevent bug of preview window being too small when cite option selected first
			# provide as many ps and divs as for sources
			return sublime.Html(
				"<div><p>Continue with another search or cite selected sources</p><p></p></div>")

	def description(self, value, text):
		if value['idx'] is not None:
			# s = value['source']
			s = value['parsed_obj']
			return f"{s['first_author_text']} ({s['date_text']})"

	def next_input(self, args):

		# selected item from this input handler
		selection = args['zotero_source']

		if selection['idx'] is not None:  # ie, an actual source
			# >>> Aggregate selected sources
			# here is the main code that aggregates sources
			# this self.selected_sources gets passed along until the end
			# take only source, and discard the idx
			self.selected_sources.append(selection['source'])
			# pass selected sources to a new input handler as well as previously collected results
			# pass precompiled items to save on compute
			return ZoteroSourceInputHandler(self.items, selected_sources = self.selected_sources, precompiled_items=True)
		elif selection['idx'] is None:
			# go to search manager to select next step
			# selected_sources should at least be an empty list ... safe to simply pass to Class
			return ZoteroSearchManagerInputHandler(self.selected_sources)


class ZoteroSearchManagerInputHandler(sublime_plugin.ListInputHandler):
	'''Manage whether to cite with current sources or continue with a new search
	'''

	def __init__(self, selected_sources):
		self.selected_sources = selected_sources

	def list_items(self):

		# passing allong selected_sources allows for collection by final command
		items = [
			['Cite', {'idx': None, 'source': self.selected_sources}],
			['New Search', {'idx': 1, 'source': self.selected_sources}]
		]

		return items

	def next_input(self, args):
		# selection from this input handler
		selection = args['zotero_search_manager']

		# if new search, go back to search_params but with previously selected sources
		if selection['idx'] == 1:
			return ZoteroSearchParamsInputHandler(selected_sources=self.selected_sources)


class ZoteroSearchCommand(sublime_plugin.TextCommand):
	'''Main search command.  Starts input handlers and inserts results into text
	'''

	def run(self, edit, format=None, **kwargs):

		sources = kwargs['zotero_search_manager']['source']
		citekeys = [s['citekey'] for s in sources]

		# >>> Preparing final citation
		if format is None:
			citation_format = DEFAULT_CITATION_FORMAT
		else:
			citation_format = format

		if citation_format in ('cite', 'citep'):
			citekeys_text = ','.join(citekeys)
			citation = f'\\{citation_format}{{{citekeys_text}}}'
		elif citation_format == 'full citation':
			citation = bbtex_bibliography_request(citekeys)
		else:
			sublime.error_message('Invalid source_format')
			return

		insert_at_cursor(edit, self.view, citation)


	def input(self, args):
		# start input handlers
		return ZoteroSearchParamsInputHandler()



