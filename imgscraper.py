

# Need image likeness (scale) comparison command
# remove all thumbs

import os
import re
import shutil
from urlparse import urlparse, urlunparse, urljoin
from lxml import html
import requests

# need something to compare image lickness, invariant of image scale
# calculate speed at end; total downloaded / run time
# record total requests made, number of redirects, failures, and total images downloaded

def msg():
    pass

def sub():
    pass

def slugify(s):
    s = re.sub('^.*://', '', s)
    s = re.sub('-', '_', s)
    s = re.sub('[/\.:]+', '-', s)
    s = re.sub('[^\w]+$', '', s)
    s = re.sub('[^\w\s-]', '', s).strip().lower()
    return re.sub('[-\s]+', '-', s)

class ImageScraper:
    image_extensions = ('.jpg', '.jpeg', '.gif', '.png', '.tiff')
    failed = []
    downloaded = []
    retry_limit = 3
    retry_count = 0
    redirect_limit = 2

    def __init__(self, root_url, downloads_path=False):
        self.root = root_url
        self.slug = slugify(self.root)
        if downloads_path:
            self.downloads = os.path.join(downloads_path, self.slug)
        else:
            self.downloads = os.path.join(os.getcwd(), self.slug)
        try:
            os.makedirs(self.downloads)
        except OSError:
            if not os.path.isdir(self.downloads):
                raise

    def download_addresses(self, addresses):
        for url in addresses:
            print "processing `" + url + "`"
            url = urlparse(url)
            if not url.path.endswith(self.image_extensions):
                print "  no image extension, skipping"
                continue
            filename = os.path.basename(url.path)
            if not url.scheme:
                rootscheme = urlparse(self.root).scheme
                if rootscheme:
                    scheme = rootscheme
                else:
                    scheme = 'http'
            else:
                scheme = False
            if not url.netloc:
                url = urljoin(self.root, url.path)
            else:
                if scheme:
                    url = scheme + ':' + urlunparse(url)
                else:
                    url = urlunparse(url)
            if not url in self.downloaded:
                self.download_address(url, filename)
            else:
                print "  already downloaded, skipping"

    def resolve(self, url):
        r = requests.head(url)
        redirects = 0
        while 'Location' in r.headers and redirects < self.redirect_limit:
            r = requests.head(r.headers['Location'])
            redirects += 1
        if 'Location' in r.headers or not 'Content-Type' in r.headers:
            return False
        else:
            return r

    def download_address(self, url, filename):
        name, ext = os.path.splitext(filename)
        filename = slugify(name) + ext
        filename = os.path.join(self.downloads, filename)
        r = self.resolve(url)
        if r and r.headers['Content-Type'].startswith('image'):
            img = requests.get(url, stream=True)
            if img.status_code == 200:
                print "  getting `" + url + "`"
                print "  downloading to `" + filename + "`"
                with open(filename, 'wb') as f:
                    img.raw.decode_content = True
                    shutil.copyfileobj(img.raw, f)
                self.downloaded.append(url)
            else:
                print "failed getting `" + url + "` with code " + img.status_code
                self.failed.append(url)
        else:
            print "  not an image"

    def scrape(self):
        page = requests.get(self.root)
        tree = html.fromstring(page.content)
        addresses = tree.xpath('//img/@src') + tree.xpath('//a/@href')
        self.download_addresses(addresses)
        while len(self.failed) > 0 and self.retry_count <= self.retry_limit:
            self.retry_count += 1
            print "Some image downloads failed; retrying, attempt no. " + self.retry_count
            last_failed = self.failed
            self.failed = []
            self.download_addresses(last_failed)

scraper = ImageScraper('http://jbeckwith.com/2012/11/28/5-steps-to-a-better-windows-command-line/', 'test-scrapes')
scraper.scrape()
