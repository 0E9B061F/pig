**Python Image Grabber** (PIG) is a simple single-page image scraper.

1. [Synopsis](#synopsis)
2. [Shorthand Key](#shorthand-key)
3. [Verbosity and Output](#verbosity-and-output)
4. [Examples](#examples)


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


## Verbosity and output

PIG has three levels of verbosity. The default verbosity level is 1. Verbosity
is controlled by specifying the `-q` and `-v` flags.

#### Verbosity 0

At verbosity 0, PIG will run silently. The `-q` flag sets verbosity to 0.

#### Verbosity 1

Standard verbosity. Output is represented by a symbolic shorthand. Total
downloads are given to the right of the shorthand output, and finally the total
time is given with the final download count.

Example:

    ........................................
    ........................................
    ............+........................+..
    .......+.........>+...+.................
    .....+.......................+.......... 7
    .............+......................+...
    .......+......+......+....+.............
    ............+....................+......
    ....+...........+....+..................
    ......+..........+.............+........ 21
    .+...+.........>+.............+....+....
    ...........+............................
    ...........++++++++++++++++++++--+++++++
    .-..+..                                  55 | 38s

See the section [Shorthand Key](#shorthand-key) above for a guide to these
symbols.

#### Verbosity 2

Full output, with multiple lines of information for every element
processed, including full URLs and paths. The `-v` flag will raise verbosity to 2.

#### Print statistics

Run PIG with the `-s` flag to print a set of statistics before exiting,
including data transferred and operation counts.


## Examples

#### Simple usage

Call the `pig` executable with a complete URL:

    pig http://www.google.com

Images will be downloaded to `./pig-downloads/google-com`


#### The PATH option

Specify the `-p PATH` option to change where the image directory will be
created:

    pig -p images/logos http://www.google.com

Images will be downloaded to `./images/logos/google-com`


#### The NAME option

Specify the `-n NAME` option to change the image directory name:

    pig -n google-logo http://www.google.com

Images will be downloaded to `./pig-downloads/google-logo`


#### Discarding duplicates

Specify the `-u` flag to discard duplicate images:

    pig -u http://example.com

PIG employs a simple hashing scheme to detect duplicates. It will only detect
exact duplicate images.
