import re
import copy
# import locale
import fileinput
from dataclasses import dataclass, field
from typing import List
import sys
from bs4 import BeautifulSoup, Tag

### Config ###
INPUT_FILE="/home/scott/Documents/A_Climbers_Guide/evolution_black_divide.html"
# Manual adjustments
# palisades.html: U Notch in needs manual adjusting of a misplaced <i>.
# evolution_black_divide.html needs <p> on Route 2 for Mount Haeckel.
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
    # elevation: str = "Pending"
    elevations: list[str] = field(default_factory=list)
    description: str = "Pending"
    # region: Region = placeholder

@dataclass
class Route:
    """ Route. Will be own documennt in DB. """
    name: str = "Pending"
    # peak: Peak = placeholder_peak  # TODO: Circular dependency issue here with peak and route.
    class_rating: str = "Pending"
    description: str = "Pending"

@dataclass
class Peak:
    """ Peak. Will be own document in DB. """
    name: str = "Pending"
    elevations: list[str] = field(default_factory=list)
    routes: list[Route] = field(default_factory=list)
    # region: Region =  placeholder
    description: str = ""

placeholder_peak = Peak()

def get_soup() -> BeautifulSoup:
    """
    Parse the book chapter and return it as an object, after parsing it as
    a string to make navigation easier later.
    """
    with open(INPUT_FILE, encoding='windows-1252') as file:  # encoding is not ISO.
        soup = BeautifulSoup(file, 'lxml')

    # Remove all links
    links = soup.find_all("a")
    for link in links:
        # link.extract()
        link.decompose()
    soup = str(soup)
    soup = soup.replace('<p><i>', '<p class="peak"><i>')  # <p><i> is only peaks to <p><i>References
    soup = soup.replace('\n', ' ')  # The string process adds a lot of "\n".
    soup = BeautifulSoup(soup, 'lxml')

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
    # elevations = List[str]
    name = ""
    if tag.i:
        name, elevations = get_name_and_elevation(tag.i)
        tag.i.decompose()  # Clear out the <i> tag with the name and elevation.

        mountain_pass.elevations = elevations
        mountain_pass.name = name

    mountain_pass.class_rating = tag.text.split(".")[0].strip()  # Returns "Class 1", above.
    mountain_pass.description = tag.text.split(".", 1)[1].strip()

    return mountain_pass

def get_passes(soup: BeautifulSoup) -> List:
    """
    Parse the soup and return a list of pass dataclasses.
    """
    output = []
    pass_section_start: Tag = soup.find("h4", string=re.compile(r"passes", re.IGNORECASE))
    # All the <p> tags are passes, and <h4> ends the section.
    for sibling in pass_section_start.next_siblings:
        if sibling.name == "p":
            output.append(pass_parser(sibling))
        elif sibling.name == "h4":
            break

    return output

def get_name_and_elevation(tag: Tag) -> tuple[str, List[str]]:
    """
    Parse a tag to extract the name and elevation. Return it as a
    tuple of the form: name: str, elevations: List[str]. Tag has the form:
    <i>Glacier Notch (13,000+).</i>
    """
    # name, _, elevations = tag.string.partition("(")
    name, _, elevations = tag.text.partition("(")
    name = name.strip()
    elevations = [e.strip(".)( ") for e in elevations.split(";")]  # split on ";" and strip each.
    return (name, elevations)

def parse_route(tag: Tag, peak: Peak) -> Route:
    """
    Parses a tag containing a route and returns a route dataclass.
    Tag has the form:
    <p> <i>Route 1. West slope.</i> Class 1. This is the easiest of the major peaks of the Palisades. ... </p>

    TODO: Circular dependency here with peak referencing the route, and the route referecing the peak.
    """
    route = Route()

    # If wanting to remove "Route X" prefix, could do it here by splitting on "." after extraction.
    route.name = tag.i.extract().string.strip()          # Removes <i></i> and returns contents.
    route.class_rating = tag.text.split(".")[0].strip()  # Returns "Class 1", above.
    route.description = tag.text.split(".", 1)[1].strip()
    # route.peak = peak

    return route


def parse_peak(tag: Tag) -> Peak:
    """
    Parse a tag containing a peak, and its related tags and return a peak dataclass.
    tag is of the form: <p class="peak"><i>Mount Agassiz (13,882; 13,891n)</i></p>
    Uses get_name_and_elevation() to extract the name and elevation, then steps through
    the following tags, parses routes, and stops at the start of the next peak.
    """
    peak = Peak()
    name, elevations = get_name_and_elevation(tag)

    # Process the routes, stopping at the next peak.
    for _, sibling in enumerate(tag.next_siblings):
        if isinstance(sibling, Tag):
            if "class" in sibling.attrs:
                if sibling.attrs["class"] == ["peak"]:
                    break  # Stopping as this is the next peak.
            elif sibling.text.strip().split(" ")[0].strip() == "Route":  # "Route" is the first word of the string.
                peak.routes.append(parse_route(sibling, peak))
            else:
                peak.description += sibling.text.strip() + "\n"

    peak.name = name
    peak.elevations = elevations

    return peak

def get_peaks(soup: BeautifulSoup) -> List[Peak]:
    """
    Parse the soup and return a list of peak datacasses.
    """
    peaks = soup.find_all(class_="peak")
    # parsed_peaks = List[Peak]
    parsed_peaks = []
    for peak in peaks:
        parsed_peaks.append(parse_peak(peak))

    return parsed_peaks
