import asyncio
import concurrent.futures

import logging
from urllib.parse import urljoin, urlunparse, urlsplit, urlunsplit

import re
from urllib.parse import urlparse
from urllib.request import urlopen, Request
from urllib.robotparser import RobotFileParser

import mimetypes
import os

class IllegalArgumentError(ValueError):
	pass

class Crawler:

	# Variables

	domain	= ""

	urls_to_crawl = set([])
	crawled_or_crawling = set([])


	not_parseable_resources = (".jpg", ".jpeg", ".png", ".gif")

	# TODO also search for window.location={.*?}
	linkregex = re.compile(b'<a [^>]*href=[\'|"](.*?)[\'"][^>]*?>')
	imageregex = re.compile (b'<img [^>]*src=[\'|"](.*?)[\'"].*?>')

	response_code={}


	output_file = None

	target_domain = ""
	scheme		  = ""

	def __init__(self,num_threads=1, domain=""):
		self.domain 	= domain
		self.num_threads = num_threads
		self.urls_to_crawl = {self.clean_link(domain)}
		self.num_crawled = 0

		if num_threads <= 0:
			raise IllegalArgumentError("Number or workers must be positive")

		try:
			url_parsed = urlparse(domain)
			self.target_domain = url_parsed.netloc
			self.scheme = url_parsed.scheme
		except:
			logging.error("Invalide domain")
			raise IllegalArgumentError("Invalid domain")

		try:
			self.output_file = open("sitemap.json", 'w')
		except:
			logging.error ("Output file not available.")
			exit(255)

	def __call_crawl(self):
		print("[", file=self.output_file)
		links = []
		while len(self.urls_to_crawl) != 0:
			current_url = self.urls_to_crawl.pop()
			self.crawled_or_crawling.add(current_url)
			single_link = self.__crawl(current_url)
			if  single_link == None:
				continue
			else:
				links.append(single_link)
				links_list = ', '.join(links)
				links_list ="    'links': ["+links_list+"]},"
			print(links_list, file=self.output_file)
		print("]", file=self.output_file)


	def run(self):

		logging.info("Start the crawling process")

		if self.num_threads ==1:
			self.__call_crawl()

		else:
			event_loop = asyncio.get_event_loop()
			try:
				while len(self.urls_to_crawl) != 0:
					executor = concurrent.futures.ThreadPoolExecutor(self.num_threads)
					event_loop.run_until_complete(self.crawl_all_pending_urls(executor))
			finally:
				event_loop.close()
		logging.info("Crawling has reached end of all found links")

	async def crawl_all_pending_urls(self, executor):
		event_loop = asyncio.get_event_loop()

		crawl_tasks = []
		for url in self.urls_to_crawl:
			self.crawled_or_crawling.add(url)
			task = event_loop.run_in_executor(executor, self.__call_crawl(), url)
			crawl_tasks.append(task)

		self.urls_to_crawl = set()

		logging.debug('waiting on all crawl tasks to complete')
		await asyncio.wait(crawl_tasks)
		logging.debug('all crawl tasks have completed nicely')
		return

	def __crawl(self, current_url):
		url = urlparse(current_url)
		# logging.info("Crawling #{}: {}".format(self.num_crawled, url.geturl()))
		self.num_crawled += 1

		request = Request(current_url, headers={"User-Agent":"Sitemap crawler"})

		# Ignore ressources listed in the not_parseable_resources
		if not url.path.endswith(self.not_parseable_resources):
			try:
				response = urlopen(request)
			except Exception as e:
				if hasattr(e,'code'):
					if e.code in self.response_code:
						self.response_code[e.code]+=1
					else:
						self.response_code[e.code]=1
				return
		else:
			response = None

		# Read the response
		if response is not None:

			msg = response.read()
			if response.getcode() in self.response_code:
				self.response_code[response.getcode()]+=1
			else:
				self.response_code[response.getcode()]=1

			response.close()

		else:
			msg = "".encode( )

		# Search for images in the current page.
		images = self.imageregex.findall(msg)

		image_links = []
		for image_link in list(set(images)):
			image_link = image_link.decode("utf-8", errors="ignore")

			# Ignore link starting with data:
			if image_link.startswith("data:"):
				continue

			# If path start with // get the current url scheme
			if image_link.startswith("//"):
				image_link = url.scheme + ":" + image_link
			# Append domain if not present
			elif not image_link.startswith(("http", "https")):
				if not image_link.startswith("/"):
					image_link = "/{0}".format(image_link)
				image_link = "{0}{1}".format(self.domain.strip("/"), image_link.replace("./", "/"))


			# Ignore other domain images
			image_link_parsed = urlparse(image_link)
			if image_link_parsed.netloc != self.target_domain:
				continue
			image_links.append(self.htmlspecialchars(image_link))


		page_url = "    {'page_url':" +  self.htmlspecialchars(url.geturl())+","
		print(page_url,file=self.output_file)
		image_links = ', '.join(image_links)
		image_links ="    'images': ["+image_links+"],"
		print(image_links, file=self.output_file)
		if self.output_file:
			self.output_file.flush()

		# Found links
		links = self.linkregex.findall(msg)
		for link in links:
			link = link.decode("utf-8", errors="ignore")

			if link.startswith('/'):
				link = url.scheme + '://' + url[1] + link
			elif link.startswith('#'):
				link = url.scheme + '://' + url[1] + url[2] + link
			elif link.startswith(("mailto", "tel")):
				continue
			elif not link.startswith(('http', "https")):
				link = self.clean_link(urljoin(current_url, link))

			# Remove the anchor part if needed
			if "#" in link:
				link = link[:link.index('#')]

			# Parse the url to get domain and file extension
			parsed_link = urlparse(link)
			domain_link = parsed_link.netloc
			target_extension = os.path.splitext(parsed_link.path)[1][1:]

			if link in self.crawled_or_crawling:
				continue
			if link in self.urls_to_crawl:
				continue

			if domain_link != self.target_domain:
				continue
			if parsed_link.path in ["", "/"]:
				continue
			if "javascript" in link:
				continue
			if self.is_image(parsed_link.path):
				continue
			if parsed_link.path.startswith("data:"):
				continue

			# Check if the current file extension is allowed or not.
			self.urls_to_crawl.add(link)
		return self.htmlspecialchars(url.geturl())


	def clean_link(self, link):
		parts = list(urlsplit(link))
		parts[2] = self.resolve_url_path(parts[2])
		return urlunsplit(parts)
		
	def resolve_url_path(self, path):
		# From https://stackoverflow.com/questions/4317242/python-how-to-resolve-urls-containing/40536115#40536115
		segments = path.split('/')
		segments = [segment + '/' for segment in segments[:-1]] + [segments[-1]]
		resolved = []
		for segment in segments:
			if segment in ('../', '..'):
				if resolved[1:]:
					resolved.pop()
			elif segment not in ('./', '.'):
				resolved.append(segment)
		return ''.join(resolved)

	@staticmethod
	def is_image(path):
		 mt,me = mimetypes.guess_type(path)
		 return mt is not None and mt.startswith("image/")


	@staticmethod
	def htmlspecialchars(text):
		return text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")



