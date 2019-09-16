#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import os
import json
import crawler

# setting parameters
parser = argparse.ArgumentParser(description='Crawler pour la creation de site map')
parser.add_argument('-n', '--num_threads', type=int, default=1, help="Number of threads for multithreading")
group = parser.add_mutually_exclusive_group()
group.add_argument('--domain', action="store", default="", help="Target domain inputed by user")

arg = parser.parse_args()

# Overload config with parameters
dict_arg = arg.__dict__


if dict_arg["domain"] == "":
	print ("You must provide a domain!")
	exit()
if not(dict_arg["domain"].startswith("http")):
	print("Add http tag in url!")
	dict_arg["domain"] ="http://"+dict_arg["domain"]

crawl = crawler.Crawler(**dict_arg)
crawl.run()

