# Python-Sitemap

Simple script to crawl websites and create and write a sitemap.json of all public link in it.

Warning : This script only works with ***Python3***

## Simple usage

	>>> python main.py --domain http://blog.lesite.us --output sitemap.xml

## Advanced usage

#### Enable Image Sitemap

```
python3 main.py --domain www.mozilla.org
```

#### Multithreaded

```
python3 main.py  --num_threads 3 --domain www.mozilla.org

```
