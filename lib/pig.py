import sys
import os
import math
import re
from time import time
from urlparse import urlparse, urlunparse, urljoin
import hashlib
try: import simplejson as json
except ImportError: import json

from lxml import html
import requests


image_extensions = ('.jpg', '.jpeg', '.gif', '.png', '.tiff')


class events:
    skip = "SKIP"
    download = "DOWNLOAD"
    discard = "DISCARD"
    redirect = "REDIRECT"
    fail = "FAIL"

symbols = {
    events.skip: '.',
    events.download: '+',
    events.discard: '-',
    events.redirect: '>',
    events.fail: '?'
}


def new(*args, **kwargs):
    return PIG(*args, **kwargs)


def mkdirp(path):
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise


def slugify(s):
    s = re.sub('^.*://', '', s)
    s = re.sub('-', '_', s)
    s = re.sub('[/\.:]+', '-', s)
    s = re.sub('[^\w]+$', '', s)
    s = re.sub('[^\w\s-]', '', s).strip().lower()
    return re.sub('[-\s]+', '-', s)


class TargetElement:
    duplicate_of = None
    errorcode = None

    def __init__(self, pig, element):
        self.pig = pig
        self.tag = element.tag
        if self.tag == 'a':
            self.raw_url = element.get('href')
        elif self.tag == 'img':
            self.raw_url = element.get('src')
        else:
            raise
        if self.raw_url:
            self.valid = True
            self.purl = urlparse(self.raw_url)
            self.text = html.tostring(element)
            self.filename = os.path.basename(self.purl.path)
            self.name, self.ext = os.path.splitext(self.filename)
            self.slug = slugify(self.name) + self.ext
            self.destination = os.path.join(self.pig.destination, self.slug)
            self.abs_destination = os.path.abspath(self.destination)
            self.redirects = []
            self.is_image = self.purl.path.endswith(image_extensions)
            if not self.purl.scheme:
                self.scheme = self.pig.scheme
            else:
                self.scheme = self.purl.scheme

            if not self.purl.netloc:
                self.netloc = self.pig.parsed.netloc
            else:
                self.netloc = self.purl.netloc

            self.furl = urlunparse((self.scheme, self.netloc, self.purl.path, self.purl.params, self.purl.query, self.purl.fragment))
        else:
            self.valid = False

    def push_redirect(self, url):
        self.redirects.append(url)

    def last_redirect(self):
        return self.redirects[-1]

    def redirected_from(self):
        if len(self.redirects) == 1:
            return self.furl
        if len(self.redirects) > 1:
            return self.redirects[-2]
        else:
            return None

    def canonical_url(self):
        if len(self.redirects) > 0:
            return self.last_redirect()
        else:
            return self.furl

    def mark_duplicate(self, other):
        self.duplicate_of = other

    def set_errorcode(self, code):
        self.errorcode = code


class State:
    pass


class PIG:
    failed = []
    downloaded = []
    retry_limit = 3
    retry_count = 0
    redirect_limit = 2
    hashes = {}
    processed = 0
    discarded = 0
    redirects = 0
    retries = 0
    start = 0
    failures = 0
    downloads = 0
    chunk_size = 128
    download_size = 0
    sym_count_line = 0
    sym_count_block = 0
    sym_blocks = 0
    sym_width = 40
    sym_block = sym_width * 5
    logfile = None
    context = None
    socket = None
    port = 25252

    def __init__(self, target_url,
                 imgdir_path=None, imgdir_name=None, unique=False, verbosity=1,
                 logfile_path=None, flush=False, publish=False, port=None):
        self.target = target_url
        self.parsed = urlparse(self.target)
        self.slug = slugify(self.target)
        self.imgdir_path = imgdir_path
        self.imgdir_name = imgdir_name
        self.unique = unique
        self.verbosity = verbosity
        self.logfile_path = logfile_path
        self.flush = flush
        self.publish = publish
        if self.publish:
            import zmq
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.PUB)
            if port: self.port = port
            address = "tcp://127.0.0.1:{}".format(self.port)
            self.socket.bind(address)
        if not self.imgdir_path:
            self.imgdir_path = os.path.join(os.getcwd(), 'pig-downloads')
        if not self.imgdir_name:
            self.imgdir_name = self.slug

        if self.parsed.scheme:
            self.scheme = self.parsed.scheme
        else:
            self.scheme = 'http'

        self.destination = os.path.join(self.imgdir_path, self.imgdir_name)
        mkdirp(self.destination)

    def timestamp(self):
        t = time() - self.start
        if t < 120:
            t = "{}s".format(int(math.floor(t)))
        elif t < 3600:
            m = int(math.floor(t / 60))
            s = int(math.floor(t % 60))
            t = "{}m{}s".format(m, s)
        else:
            h = int(math.floor(t / 3600))
            m = int(math.floor((t / 60) % 60))
            s = int(math.floor(t % 60))
            t = "{}h{}m{}s".format(h, m, s)
        return t

    def write(self, str="", raw=False, *args):
        if not raw: str += "\n"
        str = str.format(*args)
        sys.stdout.write(str)
        if self.flush: sys.stdout.flush()
        if self.logfile:
            self.logfile.write(str)
            if self.flush:
                self.logfile.flush()
                os.fsync(self.logfile)

    def put(self, s="", *args):
        self.write(s, False, *args)

    def p(self, s, *args):
        self.write(s, True, *args)

    def msg(self, s, *args, **kwargs):
        if self.verbosity > 1:
            if 'sub' in kwargs and kwargs['sub'] > 0:
                s = "{}> {}".format("  " * kwargs['sub'], s)
            else:
                s = "[{}] {}".format(self.processed, s)
            self.put(s, *args)

    def sub(self, s, *args):
        self.msg(s, *args, sub=1)

    def event(self, event, element, msg=None, margs=[], sub=0, **fields):
        symbol = symbols[event]
        if msg and (self.verbosity > 1 or self.publish):
            msg = msg.format(*margs)
        if self.verbosity == 1:
            if self.sym_count_block >= self.sym_block:
                self.sym_blocks += 1
                if self.downloads > 0:
                    self.put(" {}", self.downloads)
                else:
                    self.put()
                self.sym_count_line = 0
                self.sym_count_block = 0
            elif self.sym_count_line >= self.sym_width:
                self.put()
                self.sym_count_line = 0
            self.p(symbol)
            self.sym_count_line += 1
            self.sym_count_block += 1
        elif msg and self.verbosity > 1:
            if sub > 0:
                msg = "{}> {}".format("  " * sub, msg)
            else:
                msg = "[{}] {}".format(self.processed, msg)
            self.put(msg, *margs)
        if self.publish:
            fields['event'] = event
            fields['symbol'] = symbols[event]
            fields['element'] = element.text
            fields['url'] = element.furl
            fields['message'] = msg
            serialized = json.dumps(fields)
            self.socket.send_string(serialized)

    def skip_event(self, element, **args):
        self.event(events.skip, element, **args)

    def download_event(self, element, **args):
        self.event(events.download, element, file=element.abs_destination, **args)

    def discard_event(self, element, **args):
        self.event(events.discard, element,
                   dupe_element=element.duplicate_of.text,
                   dupe_url=element.duplicate_of.furl,
                   dupe_file=element.duplicate_of.destination, **args)

    def redirect_event(self, element, **args):
        self.event(events.redirect, element,
                   from_url=element.redirected_from(),
                   to_url=element.last_redirect(),
                   count=len(element.redirects), **args)

    def fail_event(self, element, **args):
        self.event(events.skip, element, code=element.errorcode, **args)

    def finalize_sym(self):
        if self.sym_count_block > 0:
            pad = " " * (self.sym_width - self.sym_count_line)
            self.put("{} {} | {}", pad, self.downloads, self.timestamp())

    def download_addresses(self, elements, retry=False):
        for e in elements:
            self.msg("Processing `{}`", e.furl)
            if not e.is_image:
                self.skip_event(e, msg="No image extension, skipping.", sub=1)
                continue
            if e not in self.downloaded:
                self.download_address(e)
            else:
                self.skip_event(e, msg="Already downloaded, skipping.", sub=1)
            self.processed += 1
            if retry:
                self.retries += 1
            # XXX pulse out internal state information for client to update
            # from, once per element (statistics, etc.)
            # STATE PROCESSED=27 DOWNLOADS=10 REDIRECTs=5

    def resolve(self, element):
        r = requests.head(element.furl)
        while 'Location' in r.headers and len(element.redirects) <= self.redirect_limit:
            element.push_redirect(r.headers['Location'])
            r = requests.head(r.headers['Location'])
            self.redirects += 1
            self.redirect_event(element, msg="Redirected to {}",
                                margs=[element.last_redirect()], sub=1)
        if 'Location' in r.headers or 'Content-Type' not in r.headers or not r.headers['Content-Type'].startswith('image'):
            return False
        else:
            return r

    def download_address(self, element):
        if self.resolve(element):
            img = requests.get(element.canonical_url(), stream=True)
            if img.status_code == 200:
                self.sub("Downloading `{}`", element.filename)
                if self.unique:
                    md5 = hashlib.md5()
                with open(element.destination, 'wb') as fd:
                    img.raw.decode_content = True
                    for chunk in img.iter_content(self.chunk_size):
                        fd.write(chunk)
                        self.download_size += self.chunk_size
                        if self.unique:
                            md5.update(chunk)
                self.downloaded.append(element)
                self.downloads += 1
                if self.unique:
                    h = md5.digest()
                    if h in self.hashes:
                        os.remove(element.filename)
                        self.discarded += 1
                        element.mark_duplicate(self.hashes[h])
                        self.discard_event(element, msg="Discarding image as duplicate", sub=1)
                    else:
                        self.hashes[h] = element
                        self.download_event(element, msg="Downloaded {}", margs=[element.destination], sub=1)
                else:
                    self.download_event(element, msg="Downloaded {}", margs=[element.destination], sub=1)
            else:
                element.set_errorcode(img.status_code)
                self.fail_event(element,
                                msg="Failed getting `{}` with code {}",
                                margs=[element.canonical_url(), img.status_code],
                                sub=1)
                self.failed.append(url)
        else:
            self.skip_event(element, msg="Not an image, skipping.", sub=1)

    def execute(self):
        self.start = time()
        if self.logfile_path:
            self.logfile = open(self.logfile_path, 'w')
        page = requests.get(self.target)
        tree = html.fromstring(page.content)
        elements = tree.xpath('//a') + tree.xpath('//img')
        elements = [TargetElement(self, e) for e in elements]
        elements = [e for e in elements if e.valid]
        self.download_addresses(elements)
        while len(self.failed) > 0 and self.retry_count <= self.retry_limit:
            self.retry_count += 1
            self.msg("Some image downloads failed; retrying, attempt no. ", self.retry_count)
            last_failed = self.failed
            self.failed = []
            self.download_addresses(last_failed, True)
        self.finalize_sym()
        if self.logfile:
            self.logfile.close()
            self.logfile = None
        self.elapsed = time() - self.start

    def print_stats(self):
        if self.sym_count_line > 0:
            self.put()
        self.put("Elapsed:    {}s | {}m", round(self.elapsed, 2), round(self.elapsed / 60, 2))
        self.put("Processed:  {} | {}/s", self.processed, round(self.processed / self.elapsed, 1))
        self.put("Downloaded: {} | {}/s", self.downloads, round(self.downloads / self.elapsed, 1))
        self.put("Size: {}kb | {}kb/s", self.download_size / 1024, round((self.download_size / 1024) / self.elapsed, 1))
        self.put("Failed:     {}", len(self.failed))
        self.put("Failures:   {}", self.failures)
        self.put("Retries:    {}", self.retries)
        self.put("Redirects:  {}", self.redirects)
        self.put("Discarded:  {}", self.discarded)
