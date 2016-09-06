**Python Image Grabber** (PIG) is a simple single-page image scraper.

1. [Synopsis](#synopsis)
2. [Shorthand Key](#shorthand)
3. [Examples](#examples)

<div id="synopsis"></div>
## Synopsis

`pig [-p PATH] [-n NAME] [-u] URL`

Given a `URL`, PIG will find and download all images either embedded in the
page (`<img src="foo.jpg">`) or linked to from the page (`<a
href="foo.jpg">`). It will only follow links directly to images; it will not
crawl to other pages. PIG will follow a limited number of redirects to find a
linked image. Downloaded images will be stored in a directory under the working
directory, named after the given URL. PIG will avoid downloading the same URL
twice, and will retry failed downloads.

See `pig -h` for a full list of options.


<div id="shorthand"></div>
## Shorthand Key

PIG uses a set of shorthand symbols for its default output; see the table below
for their meaning:

Operation | Shorthand
----------|----------
Skip      | .
Download  | +
Discard   | -
Redirect  | >
Fail      | ?


<div id="examples"></div>
## Examples

#### Simple usage

Call the `pig` executable with a complete URL:

    pig http://google.com

Images will be downloaded to `./pig-downloads/google-com`


#### The PATH option

Specify the `-p PATH` option to change where the image directory will be
created:

    pig -p images/logos http://google.com

Images will be downloaded to `./images/logos/google-com`


#### The NAME option

Specify the `-n NAME` option to change the image directory name:

    pig -n google-logo http://google.com

Images will be downloaded to `./pig-downloads/google-logo`


#### Discarding duplicates

Specify the `-u` flag to discard duplicate images:

    pig -u http://example.com

PIG employs a simple hashing scheme to detect duplicates. It will only detect
exact duplicate images.
