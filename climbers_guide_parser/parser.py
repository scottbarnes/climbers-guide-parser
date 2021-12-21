import re
import uuid
import copy
# import locale
import fileinput
import json
from slugify import slugify
from dataclasses import asdict, dataclass, field
from typing import List
import sys
from bs4 import Comment, BeautifulSoup, Tag

### Config ###

# INPUT_FILES=[
#     "/home/scott/Documents/A_Climbers_Guide/whitney.html",
#     # "/home/scott/Documents/A_Climbers_Guide/palisades.html",
# ]

INPUT_FILES=[
    "/home/scott/Documents/A_Climbers_Guide/mono_pass_to_pine_creek_pass.html",
    "/home/scott/Documents/A_Climbers_Guide/kaweahs_great_western_divide.html",
    "/home/scott/Documents/A_Climbers_Guide/palisades_to_kearsarge_pass.html",
    "/home/scott/Documents/A_Climbers_Guide/bond_to_tioga_other_peaks.html",
    "/home/scott/Documents/A_Climbers_Guide/mammoth_pass_to_mono_pass.html",
    "/home/scott/Documents/A_Climbers_Guide/evolution_black_divide.html",
    "/home/scott/Documents/A_Climbers_Guide/minarets_ritter_range.html",
    "/home/scott/Documents/A_Climbers_Guide/palisades.html",
    "/home/scott/Documents/A_Climbers_Guide/kings-kern_divide.html",
    "/home/scott/Documents/A_Climbers_Guide/yosemite_valley.html",
    "/home/scott/Documents/A_Climbers_Guide/cathedral_range.html",
    "/home/scott/Documents/A_Climbers_Guide/mount_humphreys.html",
    "/home/scott/Documents/A_Climbers_Guide/sawtooth_ridge.html",
    "/home/scott/Documents/A_Climbers_Guide/leconte_divide.html",
    "/home/scott/Documents/A_Climbers_Guide/kings_canyon.html",
    "/home/scott/Documents/A_Climbers_Guide/clark_range.html",
    "/home/scott/Documents/A_Climbers_Guide/whitney.html",
]

### End config ###

## Manual adjustments and notes
# Use http://www.highsierratopix.com/high-sierra-map/map.php to help locate passes.
# Just look at the git repository for the HTML files for any adjustments.

# Output
# In [40]: for i, p in enumerate(passes):
#     ...:     with open('output.txt', 'a') as outfile:
#     ...:         json.dump(asdict(passes[i]), outfile, indent=4)
#     ...:

# placeholder = Region("Pending", "Pending", "Pending")

@dataclass
class Pass:
    """ Climbing/hiking pass. Will be own document in DB. """
    pass_id: str
    name: str = "Pending"
    aka: list[str] = field(default_factory=list)
    class_rating: str = "Pending"
    elevations: list[str] = field(default_factory=list)
    description: str = "Pending"
    location_description: str = ""
    slug: str = ""
    region: str = ""
    region_slug: str = ""
    # region: Region = placeholder

@dataclass
class Route:
    """ Route. Will be own documennt in DB. """
    route_id: str
    name: str = ""
    aka: list[str] = field(default_factory=list)
    # peak: Peak = placeholder_peak  # TODO: Circular dependency issue here with peak and route.
    class_rating: str = ""
    description: str = ""
    slug: str = ""

@dataclass
class Peak:
    """ Peak. Will be own document in DB. """
    peak_id: str
    name: str = ""
    aka: list[str] = field(default_factory=list)
    elevations: list[str] = field(default_factory=list)
    routes: list[Route] = field(default_factory=list)
    # region: Region =  placeholder
    description: str = ""
    location_description: str = ""
    gps_coordinates: str = ""
    utm_coordinates: str = ""
    slug: str = ""
    region: str = ""
    region_slug: str = ""

@dataclass
class Region:
    """ Climbing region. Will be own document in DB. """
    region_id: str
    name: str
    # intro_text: str
    peaks: list[Peak] = field(default_factory=list)
    passes: list[Pass] = field(default_factory=list)
    slug: str = ""


uid = str(uuid.uuid4())
placeholder_peak = Peak(peak_id=uid)

def get_soup(INPUT_FILE) -> BeautifulSoup:
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

def pass_parser(tag: Tag) -> Pass:
    """
    Take the bs4 <p> tag holding the pass information, parse it, and return a
    Pass dataclass.
    Extract the first <i> tag as it has the pass name and elevation, if present.
    Then use regex and string replacement to extract and remove the class rating,
    leaving only the description text.
    """
    uid = str(uuid.uuid4())
    mountain_pass = Pass(pass_id=uid)
    # elevations = List[str]
    name = ""
    location_description = ""

    if tag.i:
        name, elevations, location_description = get_name_elevation_and_description(tag.i)
        tag.i.decompose()  # Clear out the <i> tag with the name and elevation.

        mountain_pass.elevations = elevations
        mountain_pass.name = name

    mountain_pass.class_rating = tag.text.split(".")[0].strip()  # Returns "Class 1", above.
    mountain_pass.description = tag.text.split(".", 1)[1].strip()
    mountain_pass.location_description = location_description
    mountain_pass.slug = slugify(f'{mountain_pass.name} {mountain_pass.pass_id.split("-")[-1]}')

    return mountain_pass

def get_passes(soup: BeautifulSoup) -> List:
    """
    Parse the soup and return a list of pass dataclasses.
    """
    passes = []
    pass_section_start: Tag = soup.find("h4", string=re.compile(r"passes", re.IGNORECASE))
    # All the <p> tags are passes, and <h4> ends the section.
    # Use 'try' to catch when there are no passes in the file.
    try:
        for sibling in pass_section_start.next_siblings:
            if sibling.name == "p":
                p = pass_parser(sibling)
                # Don't add non-passes.
                if "References" in p.name or "Photographs" in p.name:
                    continue
                passes.append(p)
            elif sibling.name == "h4":
                break
    except AttributeError:
        return passes

    return passes

def get_name_elevation_and_description(tag: Tag) -> tuple[str, List[str], str]:
    """
    Parse a tag to extract the name, elevation, and location description. Return it as a
    tuple of the form: name: str, elevations: List[str], location_description: str. Tag has the form:
    <i>Glacier Notch (13,000+).</i>
    <i>Peak 12,135 (12,205n; 1 NW of Recess Peak)</i>
    """
    # name, _, elevations = tag.string.partition("(")
    location_description = ""
    name, _, elevations = tag.text.partition("(")
    name = name.strip(" ,.")
    elevations = [e.strip(".,)( ") for e in elevations.split(";")]  # split on ";" and strip each.
    # Get narrative location descriptions (e.g 0.6 NE of Mount Morgan) and remove it from
    # the list of elevations.
    p = re.compile('\\d\\s[NEWS]')
    for i, e in enumerate(elevations):
        if p.search(e):
            location_description = elevations.pop(i)

    return (name, elevations, location_description)

def parse_route(tag: Tag, peak: Peak, kind: str) -> Route:
    """
    Parses a tag containing a route and returns a route dataclass. Tag has the
    form:
    <p> <i>Route 1. West slope.</i> Class 1. This is the easiest of the major peaks of the Palisades. ... </p>
    or:
    <p><i>Kat Walk.</i> Class 4. First ascent September 1929 by Ralph S. Griswold.
    or
    Parses a tag containing a 'default' (i.e. single, unnumbered) route and
    returns a route dataclass. Tag has the form:
    <p>
    Class 3. First ascent by David R. Brower, Hervey Voge, and Norman
    Clyde on June 25, 1934. From the northeast follow the arête from Crag
    5 to the 5-6 notch, and ascend the west side of the northwest arête.
    </p>

    TODO: Circular dependency here with peak referencing the route, and the
    route referecing the peak.
    """
    uid = str(uuid.uuid4())
    route = Route(route_id=uid)

    # If wanting to remove "Route X" prefix, could do it here by splitting on "." after extraction.
    if kind == "Route":
        route.name = tag.i.extract().string.strip(" .,")          # Removes <i></i> and returns contents.
    elif kind == "Class":
        route.name = "Route 1"  # This is the only included route for the peak.

    route.class_rating = tag.text.split(".")[0].strip()  # Returns "Class 1", above.
    route.description = tag.text.split(".", 1)[1].strip()
    route.slug = slugify(f'{route.name} {route.route_id.split("-")[-1]}')
    # route.peak = peak

    return route

def parse_peak(tag: Tag) -> Peak:
    """
    Parse a tag containing a peak, and its related tags and return a peak
    dataclass. tag is of the following forms:
        <p class="peak"><i>Mount Agassiz (13,882; 13,891n)</i></p>
        <p class="peak"><i>Peak 12,135 (12,205n; 1 NW of Recess Peak)</i></p>
    Uses get_name_elevation_and_description() to extract the name, elevation,
    and description, then steps through the following tags, parses routes, and
    stops at the start of the next peak or the end of the chapter.

    Additionally, if a peak has no enumerated routes (e.g. Route 1, Route 2),
    but lists a route starting with "Class X. Ascend the north slope", or
    something of that nature, run parse_route_unenumerated to create that as
    the default Route 1.

    Finally, if it's a 'yosemite.html' route description, that's parsed also.
    """
    uid = str(uuid.uuid4())
    peak = Peak(peak_id=uid)
    name, elevations, location_description = get_name_elevation_and_description(tag)

    # For each peak, go through and process the peak name, elevation(s),
    # route(s), and description.
    for _, sibling in enumerate(tag.next_siblings):
        # Only operate on tags
        if not isinstance(sibling, Tag):
            continue

        # Stop at the next peak or the end of the chapter.
        if "class" in sibling.attrs:
            if sibling.attrs["class"] == ["peak"]:
                break  # Stopping as this is the next peak.
        elif "clear" in sibling.attrs:
            if sibling.attrs["clear"] == "all":
                break  # End of the chapter.

        # Get the first word of any strings, as it's used to parse the route,
        # and just add anything else to the peak's description.
        first_word = sibling.text.strip().split(" ")[0].strip()
        if first_word in ["Route", "Class"]:
            peak.routes.append(parse_route(sibling, peak, first_word))
        elif is_route_has_no_route_prefix(sibling):
            peak.routes.append(parse_route(sibling, peak, "Route"))
        else:
            peak.description += sibling.text.strip() + "\n"

    peak.name = name
    peak.elevations = elevations
    peak.location_description = location_description
    peak.slug = slugify(f'{peak.name} {peak.peak_id.split("-")[-1]}')

    return peak

def is_route_has_no_route_prefix(tag):
    """
    Returns true if it's a yosemite.html style route without the Route X prefix.
    <p><i>Kat Walk.</i> Class 4. First ascent September 1929 by Ralph S. Griswold.
    """
    # There may be no <i> tag sibling, so catch the AttributeError if it's not
    # there.
    try:
        p = re.compile("^[A-Z].+[^\\.\\)][\\.]")
        return p.match(tag.i.string) is not None

    except AttributeError:
        return False

def get_peaks(soup: BeautifulSoup) -> List[Peak]:
    """
    Parse the soup and return a list of peak datacasses.
    """
    peaks = soup.find_all(class_="peak")
    # parsed_peaks = List[Peak]
    parsed_peaks = []
    for peak in peaks:
        p = parse_peak(peak)
        # Don't add non-peaks.
        if "References" in p.name or "Photographs" in p.name:
            continue

        parsed_peaks.append(p)

    return parsed_peaks

def parse_region(soup: BeautifulSoup) -> str:
    """
    Parse the soup, get the region, and return it.
    """
    title_string = ""

    title = soup.find("i", string=re.compile(r"Sierra"))
    if title:
        region = title.find_next("h3")

        if region:
            title_string = region.text

    return title_string

def get_region(soup: BeautifulSoup, peaks: list[Peak], passes: list[Pass]) -> Region:
    """
    Get the region, then go through already parsed peaks and passes and add them to the region.
    """

    title_string = parse_region(soup)

    # return "no region"
    uid = str(uuid.uuid4())
    region = Region(name=title_string, region_id=uid)
    region.slug = slugify(f'{region.name} {region.region_id.split("-")[-1]}')

    # Add the peaks and passes to the region, and the region to the peaks and
    # the passes.
    for peak in peaks:
        region.peaks.append(peak)
        peak.region = region.name
        peak.region_slug = region.slug

    for mountain_pass in passes:
        region.passes.append(mountain_pass)
        mountain_pass.region = region.name
        mountain_pass.region_slug = region.slug

    return region

def do_peaks_passes_regions() -> tuple[list[Peak], list[Pass], list[Region]]:
    """
    Iterate through the book and run the scripts on each input.
    """
    peaks = []
    passes = []
    regions = []

    for file in INPUT_FILES:
        soup = get_soup(file)
        peaks += get_peaks(soup)
        passes += get_passes(soup)
        regions.append(get_region(soup, peaks, passes))

    return peaks, passes, regions


def write_json(input: list, type: str):
    """ Write out json to a set of files. """
    output = []
    for e in input:
        output.append(asdict(e))

    with open(f"output-{type}.json", "a") as outfile:
        json.dump(output, outfile, indent=4)

def get_json():
    """ Write out the json files. """
    peaks, passes, regions = do_peaks_passes_regions()
    write_json(peaks, "peaks")
    write_json(passes, "passes")
    write_json(regions, "regions")

