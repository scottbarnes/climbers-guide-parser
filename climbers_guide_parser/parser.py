import re
import copy
import locale
from dataclasses import dataclass
from typing import List
import sys
from bs4 import BeautifulSoup, Tag

### Config ###
INPUT_FILE="/home/scott/Documents/A_Climbers_Guide/palisades.html"
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
    """ Climbing/hiking p ass. Will be own document in DB. """
    name: str = "Pending"
    class_rating: str = "Pending"
    elevation: str = "Pending"
    description: str = "Pending"
    region: Region = placeholder


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
    """

    mountain_pass = Pass()
    # name: str = ""
    # elevation: str = ""
    
    # Remove the random <a> tags that indicate book page numbers.
    if tag.a:
        tag.a.decompose()

    # Pass name and elevation are the first italics.
    if tag.i:
        name_and_elevation: Tag = tag.i.extract()  # Removes <i> from <p> contents.
        name_and_elevation_str: str = name_and_elevation.string.extract()
        pattern = re.compile("\((.+)\)")
        match = pattern.search(name_and_elevation_str)
        if match:
            # locale.setlocale( locale.LC_ALL, 'en_US.UTF-8' )
            # elevation = locale.atoi(match.group(1))
            elevation = match.group(1)
            mountain_pass.elevation = elevation
        pattern = re.compile(".*?(?=\()")
        match2 = pattern.search(name_and_elevation_str)
        if match2:
            name = match2.group(0).strip(" ")
            mountain_pass.name = name


        # if not name:
        #     name = ""
        # if not elevation:
        #     elevation = 0

    text = tag.get_text()
    if text:
        text = text.replace('\n', ' ')
        pattern = re.compile("Class.*?(\.)")
        match3 = pattern.search(text)
        if match3:
            class_rating = match3.group(0).strip('.')
            mountain_pass.class_rating = class_rating
            text = text.replace(match3.group(0), '').strip(' ')
        else:
            text = text.strip(' ')

        mountain_pass.description = text

    # pass_dc = Pass()
    # pass_dc.name=name
    # pass_dc.elevation=elevation
    return mountain_pass
    # return tag


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
        # else:
        #     print("Couldn't find next section tag: <h4>. Exiting.")
        #     sys.exit()


    # Get the <p> tags with the individual pass data.
    # unparsed_passes: List = get_between_siblings(tag, "h4")
    # # Because this is just a regular list, find the bs4 tags to work on.
    # for element in unparsed_passes:
    #     if isinstance(element, Tag):
    #         # Parse the specific bs4 <p> tag with the pass info.
    #         output.append(pass_parser(element))

    return output
