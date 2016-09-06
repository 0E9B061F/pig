import os
import re
from urlparse import urlparse, urlunparse, urljoin
from lxml import html
import requests
from time import time
import hashlib
import sys
import math


image_extensions = ('.jpg', '.jpeg', '.gif', '.png', '.tiff')

class symbols:
    skip     = "."
    download = "+"
    discard  = "-"
    redirect = ">"
    fail     = "?"


def new(*args):
    return ImageGrabber(*args)

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


class ImageGrabber:
    failed = []
    downloaded = []
    retry_limit = 3
    retry_count = 0
    redirect_limit = 2
    hashes = []
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

    def __init__(self, target_url, imgdir_path=None, imgdir_name=None, unique=False, verbosity=1):
        self.target = target_url
        self.slug = slugify(self.target)
        self.imgdir_path = imgdir_path
        self.imgdir_name = imgdir_name
        self.unique = unique
        self.verbosity = verbosity
        if not self.imgdir_path:
            self.imgdir_path = os.path.join(os.getcwd(), 'pig-downloads')
        if not self.imgdir_name:
            self.imgdir_name = self.slug

        self.destination = os.path.join(self.imgdir_path, self.imgdir_name)
        mkdirp(self.destination)

    def timestamp(self):
        t = time() - self.start
        if t < 120:
            t = "{}s".format(int(math.floor(t)))
        elif t < 3600:
            m = int(math.floor(t / 60))
            s = int(math.floor(t % 60))
            t = "{}m{}s".format(m,s)
        else:
            h = int(math.floor(t / 3600))
            m = int(math.floor((t / 60) % 60))
            s = int(math.floor(t % 60))
            t = "{}h{}m{}s".format(h,m,s)
        return t


    def put(self, s, *args):
        print(s.format(*args))

    def msg(self, s, *args):
        if self.verbosity > 1:
            self.put(s, *args)

    def sub(self, s, *args):
        self.msg(u"  > "+s, *args)

    def sym(self, c):
        if self.verbosity == 1:
            if self.sym_count_block >= self.sym_block:
                self.sym_blocks += 1
                if self.downloads > 0:
                    self.put(" {}", self.downloads)
                else:
                    print("")
                self.sym_count_line = 0
                self.sym_count_block = 0
            elif self.sym_count_line >= self.sym_width:
                print("")
                self.sym_count_line = 0
            sys.stdout.write(c)
            self.sym_count_line += 1
            self.sym_count_block += 1

    def finalize_sym(self):
        if self.sym_count_block > 0:
            pad = " " * (self.sym_width - self.sym_count_line)
            self.put("{} {} | {}", pad, self.downloads, self.timestamp())

    def download_addresses(self, addresses, retry=False):
        for url in addresses:
            self.msg("Processing `{}` . . .", url)
            url = urlparse(url)
            if not url.path.endswith(image_extensions):
                self.sub("No image extension, skipping.")
                self.sym(symbols.skip)
                continue
            filename = os.path.basename(url.path)
            if not url.scheme:
                rootscheme = urlparse(self.target).scheme
                if rootscheme:
                    scheme = rootscheme
                else:
                    scheme = 'http'
            else:
                scheme = False
            if not url.netloc:
                url = urljoin(self.target, url.path)
            else:
                if scheme:
                    url = "{}:{}".format(scheme, urlunparse(url))
                else:
                    url = urlunparse(url)
            if not url in self.downloaded:
                self.download_address(url, filename)
            else:
                self.sub("Already downloaded, skipping.")
                self.sym(symbols.skip)
            self.processed += 1
            if retry:
                self.retries += 1

    def resolve(self, url):
        r = requests.head(url)
        redirects = 0
        while 'Location' in r.headers and redirects < self.redirect_limit:
            r = requests.head(r.headers['Location'])
            self.redirects += 1
            redirects += 1
            self.sym(symbols.redirect)
        if 'Location' in r.headers or not 'Content-Type' in r.headers:
            return False
        else:
            return r

    def download_address(self, url, filename):
        name, ext = os.path.splitext(filename)
        filename = slugify(name) + ext
        filename = os.path.join(self.destination, filename)
        r = self.resolve(url)
        if r and r.headers['Content-Type'].startswith('image'):
            img = requests.get(url, stream=True)
            if img.status_code == 200:
                self.sub("Downloading `{}` to `{}`", url, filename)
                if self.unique:
                    md5 = hashlib.md5()
                with open(filename, 'wb') as fd:
                    img.raw.decode_content = True
                    for chunk in img.iter_content(self.chunk_size):
                        fd.write(chunk)
                        self.download_size += self.chunk_size
                        if self.unique:
                            md5.update(chunk)
                self.downloaded.append(url)
                self.downloads += 1
                if self.unique:
                    h = md5.digest()
                    if h in self.hashes:
                        os.remove(filename)
                        self.discarded += 1
                        self.sym(symbols.discard)
                    else:
                        self.hashes.append(h)
                        self.sym(symbols.download)
                else:
                    self.sym(symbols.download)
            else:
                self.sub("Failed getting `{}` with code {}", url, img.status_code)
                self.sym(symbols.fail)
                self.failed.append(url)
        else:
            self.sub("Not an image, skipping.")
            self.sym(symbols.skip)

    def execute(self):
        self.start = time()
        page = requests.get(self.target)
        tree = html.fromstring(page.content)
        addresses = tree.xpath('//a/@href') + tree.xpath('//img/@src')
        self.download_addresses(addresses)
        while len(self.failed) > 0 and self.retry_count <= self.retry_limit:
            self.retry_count += 1
            self.msg("Some image downloads failed; retrying, attempt no. ", self.retry_count)
            last_failed = self.failed
            self.failed = []
            self.download_addresses(last_failed, True)
        self.finalize_sym()
        self.elapsed = time() - self.start

    def print_stats(self):
        if self.sym_count_line > 0:
            print("")
        self.put("Elapsed:    {}s | {}m", round(self.elapsed, 2), round(self.elapsed / 60, 2))
        self.put("Processed:  {} | {}/s", self.processed, round(self.processed / self.elapsed, 1))
        self.put("Downloaded: {} | {}/s", self.downloads, round(self.downloads / self.elapsed, 1))
        self.put("Size: {}kb | {}kb/s", self.download_size / 1024, round((self.download_size / 1024) / self.elapsed, 1))
        self.put("Failed:     {}", len(self.failed))
        self.put("Failures:   {}", self.failures)
        self.put("Retries:    {}", self.retries)
        self.put("Redirects:  {}", self.redirects)
        self.put("Discarded:  {}", self.discarded)
