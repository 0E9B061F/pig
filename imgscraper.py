

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

    def __init__(self, root_url, downloads_path=False):
        self.root = root_url
        self.slug = slugify(self.root)
        if downloads_path:
            self.downloads = downloads_path
        else:
            self.downloads = os.path.join(os.getcwd(), self.slug)
        os.makedirs(self.downloads)

    def download_addresses(self, addresses):
        for url in addresses:
            print "processing `" + url + "`"
            url = urlparse(url)
            if not url.path.endswith(self.image_extensions):
                continue
            filename = os.path.basename(url.path)
            if not url.netloc:
                url = urljoin(self.root, url.path)
            else:
                url = urlunparse(url)
            if not url in self.downloaded:
                print "  getting `" + url + "`"
                print "  downloading to `" + filename + "`"
                self.download_address(url, filename)
            else:
                print "  already downloaded, skipping"

    def download_address(self, url, filename):
        filename = os.path.join(self.downloads, filename)
        img = requests.get(url, stream=True)
        if img.status_code == 200:
            with open(filename, 'wb') as f:
                img.raw.decode_content = True
                shutil.copyfileobj(img.raw, f)
            self.downloaded.append(url)
        else:
            print "failed getting `" + url + "` with code " + img.status_code
            self.failed.append(url)

    def scrape(self):
        page = requests.get(self.root)
        tree = html.fromstring(page.content)
        addresses = tree.xpath('//a/@href') + tree.xpath('//img/@src')
        self.download_addresses(addresses)
        while failed.length > 0 and retry_count <= retry_limit:
            retry_count += 1
            print "Some image downloads failed; retrying, attempt no. " + retry_count
            last_failed = failed
            failed = []
            self.download_addresses(last_failed)

scraper = ImageScraper('https://en.wikipedia.org/wiki/Capitoline_Brutus')
scraper.scrape()
