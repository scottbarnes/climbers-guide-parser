import re
import copy
# import locale
import fileinput
from dataclasses import dataclass
from typing import List
import sys
from bs4 import BeautifulSoup, Tag

### Config ###
INPUT_FILE="/home/scott/Documents/A_Climbers_Guide/palisades.html"
# U Notch in palisades.html needs manual adjusting of a misplaced <i>.
### End config ###

# Dataclasses for:
# regions
# - intro
# - the historical resume, topography, approaches & campsites, passes, and peaks for the region
# historical resume
# - region
# topography and its relation to climbing
# - region
# approaches and campsites
# - direction
# - region
# principal passes
# - name
# - class
# - elevation
# - region
# - description
# peaks
# - name
# - elevation (list?)
# - routes {set of the routes or whatever}
# - region
# routes
# - route # / name
# - peak
# - class
# - description

@dataclass
class Region:
    """ Climbing region. Will be own document in DB. """
    name: str
    intro_text: str

placeholder = Region("Pending", "Pending")

@dataclass
class Pass:
    """ Climbing/hiking pass. Will be own document in DB. """
    name: str = "Pending"
    class_rating: str = "Pending"
    elevation: str = "Pending"
    description: str = "Pending"
    region: Region = placeholder


def prepare_file():
    """
    Do some initial formatting of the files to make them easier to work with.
    This writes changes to each file and only needs to be run once.
    """
    # 'encoding=' added in python 3.10.
    with fileinput.FileInput(INPUT_FILE, inplace=True, backup='.bak', encoding='windows-1252') as file:
        for line in file:
            print(line.replace('<p><i>', '<p class="peak"><i>'), end='')

def get_soup() -> BeautifulSoup:
    """
    Parse the book chapter and return it as an object.
    """
    with open(INPUT_FILE, encoding='windows-1252') as file:  # encoding is not ISO.
        soup = BeautifulSoup(file, 'lxml')

    return soup

def get_between_siblings(bs_tag: Tag, html_tag: str) -> list:
    """
    Takes a bs4 tag and an str html tag and returns a list of all bs4.element.Tag and
    bs4.element.NavigableString between the two.
    the two. E.g.
        bs_tag = soup.find("h4", string="Principal Passes")
        html_tag = "h4"
    The above returns everything between <h4>Principal Passes</h4> and the next <h4> tag.

    Note: the problem with this is that it returns a list and loses navigability and
    bs components must be re-extracted.
    """
    output = [] # list with bs4.element.Tag and bs4.element.NavigableString.
    for sibling in bs_tag.next_siblings:
        if sibling.name == html_tag:
            break
        output.append(copy.copy(sibling))

    return output

def pass_parser(tag: Tag) -> Pass:
    """
    Take the bs4 <p> tag holding the pass information, parse it, and return a
    Pass dataclass.
    Extract the first <i> tag as it has the pass name and elevation, if present.
    Then use regex and string replacement to extract and remove the class rating,
    leaving only the description text.
    """

    mountain_pass = Pass()

    # Remove the random <a> tags that indicate book page numbers.
    if tag.a:
        tag.a.decompose()

    # Process any pass names or elevations (first italics, if present.)
    if tag.i:
        name_and_elevation: Tag = tag.i.extract()  # Removes <i> from <p> contents.
        name_and_elevation_str: str = name_and_elevation.string.extract()
        pattern = re.compile(r"\((.+)\)")  # Match up to first "(", where elevation starts.
        match = pattern.search(name_and_elevation_str)
        if match:
            # locale.setlocale( locale.LC_ALL, 'en_US.UTF-8' )
            # elevation = locale.atoi(match.group(1))
            elevation = match.group(1)
            mountain_pass.elevation = elevation
        pattern = re.compile(r".*?(?=\()")  # Match up to first "." to get peak name.
        match2 = pattern.search(name_and_elevation_str)
        if match2:
            name = match2.group(0).strip(" ")
            mountain_pass.name = name

    # Get pass class rating, if present. Grab the text from <p> and do regex and
    # string replace directly on it to parse out class rating. Remainder is the
    # pass description.
    text = tag.get_text()
    if text:
        text = text.replace('\n', ' ')
        pattern = re.compile(r"Class.*?(\.)")
        match3 = pattern.search(text)
        if match3:
            class_rating = match3.group(0).strip('.')
            mountain_pass.class_rating = class_rating
            text = text.replace(match3.group(0), '').strip(' ')
        else:
            text = text.strip(' ')

        mountain_pass.description = text

    return mountain_pass

def get_passes(soup: BeautifulSoup) -> List:
    """
    Parse the soup and return a list of pass dataclasses.
    """
    output = []
    pass_section_start: Tag = soup.find("h4", string="Principal Passes")
    # All the <p> tags are passes, and <h4> ends the section.
    for sibling in pass_section_start.next_siblings:
        if sibling.name == "p":
            output.append(pass_parser(sibling))
        elif sibling.name == "h4":
            break

    return output

def get_peaks(soup: BeautifulSoup): # -> List:
    """
    Parse the soup and return a list of peak datacasses.
    """
    # Add a class to all peak code (<p><i>peak name</i></p>) to make work easier.
    for tag in soup.find_all(re.compile(r"<p\s*.*><i\s*.*>")):
        print(tag)

    for tag in soup.find_all(re.compile(r"^b")):
        print(tag)
