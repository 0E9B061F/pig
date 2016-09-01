**imgscraper** is a simple, general image scraping utility written in python.

Given a URL, **imgscraper** will find and download all images either embedded in
the page (<img&nbsp;src="foo.jpg">) or linked to from the page
(<a&nbsp;href="foo.jpg">). It will not crawl to other pages. Downloaded images
will be stored in a directory under the working directory, named after the given
URL. **imgscraper** will avoid downloading the same URL twice, and will retry failed
downloads, by default, three times each.

In the future, downloaded duplicate images will be discarded. Thumbnails will
also be discarded, using visual cues as well as similar filenames. A crawl mode
will also be implemented.
