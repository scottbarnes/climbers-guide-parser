import json
import re
# import sys
import uuid
from datetime import datetime
from dataclasses import asdict, dataclass, field
from typing import List

from bs4 import BeautifulSoup, Tag # type: ignore
from slugify import slugify # type: ignore
import click # type: ignore
from sqlalchemy.orm import sessionmaker # type: ignore

from .database import Base, DB # type: ignore
from .models import PeakModel, RouteModel, RegionModel, PassModel # type: ignore

### Config ###

DBTYPE = 'sqlite'
# DBNAME = ':memory:'  # Store in memory, for testing.
DBNAME = 'babble.sqlite'  # Filename for sqlite db.

# INPUT_FILES=[
#     "/home/scott/Documents/A_Climbers_Guide/whitney.html",
#     # "/home/scott/Documents/A_Climbers_Guide/palisades.html",
# ]

INPUT_FILES = [
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
    """Climbing/hiking pass. Will be own document in DB."""

    created: str
    last_modified: str
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


@dataclass
class Route:
    """Route. Will be own documennt in DB."""

    created: str
    last_modified: str
    route_id: str
    name: str = ""
    aka: list[str] = field(default_factory=list)
    # peak: Peak = placeholder_peak  # Circular dependency; set after creation.
    class_rating: str = ""
    description: str = ""
    slug: str = ""


@dataclass
class Peak:
    """Peak. Will be own document in DB."""

    created: str
    last_modified: str
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
    """Climbing region. Will be own document in DB."""

    created: str
    last_modified: str
    region_id: str
    name: str
    # intro_text: str
    peaks: list[Peak] = field(default_factory=list)
    passes: list[Pass] = field(default_factory=list)
    slug: str = ""


def get_soup(INPUT_FILE) -> BeautifulSoup:
    """
    Parse the book chapter and return it as an object, after parsing it as
    a string to make navigation easier later.
    """
    with open(INPUT_FILE, encoding="windows-1252") as file:  # encoding is not ISO.
        soup = BeautifulSoup(file, "lxml")

    # Remove all links
    links = soup.find_all("a")
    for link in links:
        # link.extract()
        link.decompose()
    soup = str(soup)
    soup = soup.replace("<p><i>", '<p class="peak"><i>')  # <p><i> is only peaks to <p><i>References
    soup = soup.replace("\n", " ")  # The string process adds a lot of "\n".
    soup = BeautifulSoup(soup, "lxml")

    return soup


def pass_parser(tag: Tag, region: Region) -> Pass:
    """
    Take the bs4 <p> tag holding the pass information, parse it, and return a
    Pass dataclass.
    Extract the first <i> tag as it has the pass name and elevation, if present.
    Then use regex and string replacement to extract and remove the class rating,
    leaving only the description text.
    """
    uid = str(uuid.uuid4())
    mountain_pass = Pass(pass_id=uid, created=datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
                         last_modified=datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'))
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
    mountain_pass.region = region.name
    mountain_pass.region_slug = region.slug

    # Add the pass back into the region.
    region.passes.append(mountain_pass)

    return mountain_pass


def get_passes(soup: BeautifulSoup, region: Region) -> List[Pass]:
    """
    Parse the soup and return a list of pass dataclasses.
    """
    passes: List[Pass] = []
    pass_section_start = soup.find("h4", string=re.compile(r"passes", re.IGNORECASE))

    # All the <p> tags (after the start) contain passes, and <h4> ends the section.
    # When the <h4> tag is found, we're done.
    if not isinstance(pass_section_start, Tag):
        return passes  # Some regions have no passes, so bail out.

    for sibling in pass_section_start.next_siblings:
        # if sibling.name == "p":
        if isinstance(sibling, Tag) and sibling.name == "p":
            p = pass_parser(sibling, region)
            # Don't add non-passes.
            if "References" in p.name or "Photographs" in p.name:
                continue
            passes.append(p)
        elif isinstance(sibling, Tag) and sibling.name == "h4":
            break

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
    p = re.compile("\\d\\s[NEWS]")
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
    route = Route(route_id=uid, created=datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
                  last_modified=datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'))

    # If wanting to remove "Route X" prefix, could do it here by splitting on "." after extraction.
    if kind == "Route" and tag.i:
        parsed_route_name = tag.i.extract().string
        if parsed_route_name:
            route.name = parsed_route_name.strip(" .,") # Removes <i></i> and returns contents.
    elif kind == "Class":
        route.name = "Route 1"  # This is the only included route for the peak.

    route.class_rating = tag.text.split(".")[0].strip()  # Returns "Class 1", above.
    route.description = tag.text.split(".", 1)[1].strip()
    route.slug = slugify(f'{route.name} {route.route_id.split("-")[-1]}')
    # This can't be typed on the class because of circular dependecies with
    # Peak and Route when defining them.
    route.peak: Peak = peak # type: ignore

    return route


def parse_peak(tag: Tag, region: Region) -> Peak:
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
    peak = Peak(peak_id=uid, created=datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
                last_modified=datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'))
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
    peak.region = region.name
    peak.region_slug = region.slug

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


def get_peaks(soup: BeautifulSoup, region: Region) -> tuple[List[Peak], Region]:
    """
    Parse the soup and return a list of peak datacasses and an updated region
    that includes the peak..
    """
    peaks = soup.find_all(class_="peak")
    # parsed_peaks = List[Peak]
    parsed_peaks = []
    for peak in peaks:
        p = parse_peak(peak, region)
        # Don't add non-peaks.
        if "References" in p.name or "Photographs" in p.name:
            continue

        # Add the peak to the parsed peaks and region.
        parsed_peaks.append(p)
        region.peaks.append(p)

    return parsed_peaks, region


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


def get_region(soup: BeautifulSoup) -> Region:
    """
    Get the region and return it.
    """

    title_string = parse_region(soup)

    # return "no region"
    uid = str(uuid.uuid4())
    region = Region(name=title_string, region_id=uid, created=datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
                    last_modified=datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'))
    region.slug = slugify(f'{region.name} {region.region_id.split("-")[-1]}')

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
        region = get_region(soup)  # Get the current region.
        p, r = get_peaks(soup, region)  # Get the peaks and updated region.
        peaks += p
        regions.append(r)
        passes += get_passes(soup, region)

    return peaks, passes, regions


def write_json(i: list, kind: str):
    """Write out json to a set of files."""
    output = []
    for e in i:
        output.append(asdict(e))

    with open(f"output-{kind}.json", "a") as outfile:
        json.dump(output, outfile, indent=4, default=str, sort_keys=True)


def output_json():
    """ Parse and output to JSON """
    peaks, passes, regions = do_peaks_passes_regions()
    write_json(peaks, "peaks")
    write_json(passes, "passes")
    write_json(regions, "regions")
    click.echo("JSON files written to the current directory.")

def output_sqlite():
    """ Parse output to SQLite """

    # Set up database.
    engine = DB(dbtype=DBTYPE, dbname=DBNAME).create_db_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Get the peak, passes, and regions, though in a way just the regions are
    # used.
    peaks, passes, regions = do_peaks_passes_regions()

    # For each region, process all peaks and passes.
    for region in regions:
        r = RegionModel(
            name=region.name,
            slug=region.slug,
            region_id=region.region_id,
            created=datetime.now(),
            last_modified=datetime.now(),
        )

        # Process each peak in the region.
        for peak in region.peaks:
            p = PeakModel(
                created=datetime.now(),
                last_modified=datetime.now(),
                peak_id=peak.peak_id,
                name=peak.name,
                aka=peak.aka,
                elevations=peak.elevations,
                description=peak.description,
                location_description=peak.location_description,
                gps_coordinates=peak.gps_coordinates,
                utm_coordinates=peak.utm_coordinates,
                slug=peak.slug,
                # This probably needs to get the already created specific region
                # and then to work with that.
                # region_id=r,
                # region_slug=peak.region_slug,
            )

            # Append this peak to its region.
            r.peaks.append(p)

            # For each route on the peak, add it to the list via the peak's
            # routes, so that the relation between the two is set.
            for route in peak.routes:
                rte = RouteModel(
                    name=route.name,
                    aka=route.aka,
                    class_rating=route.class_rating,
                    description=route.description,
                    route_id=route.route_id
                )
                # Add the route to the peak.
                p.routes.append(rte)

            # With Peak constructed and the routes added, add the peak.
            session.add(p)

        # Process each pass in the region.
        for mountain_pass in region.passes:
            p = PassModel(
                created=datetime.now(),
                last_modified=datetime.now(),
                pass_id=mountain_pass.pass_id,
                class_rating=mountain_pass.class_rating,
                description=mountain_pass.description,
                name=mountain_pass.name,
                slug=mountain_pass.slug,
            )
            r.passes.append(p)
            session.add(p)

        # Add the region
        print(f"Processing {region.name}\n")
        session.add(r)
    # Save the database changes.
    session.commit()

    first_peak = session.query(PeakModel).first()
    last_peak = session.query(PeakModel).order_by(PeakModel.id.desc())[2]
    print(f"Fetching the first peak:\n{first_peak}")
    print(f"Fetching the third from the last peak:\n{last_peak}")
    print(f"\nShowing more data about {last_peak.name}\n \
          id: {last_peak.id}\n \
          created: {last_peak.created}\n \
          last_modified: {last_peak.last_modified}\n \
          peak_id: {last_peak.peak_id}\n \
          aka: {last_peak.aka}\n \
          elevations: {last_peak.elevations}\n \
          description: {last_peak.description}\n \
          location_description: {last_peak.location_description}\n \
          gps_coordinates: {last_peak.gps_coordinates}\n \
          utm_coordinates: {last_peak.utm_coordinates}\n \
          slug: {last_peak.slug}\n \
          region: {last_peak.region}\n \
          routes: {last_peak.routes}\n \
          ")

    regions_db = session.query(RegionModel).all()
    print(f"Regions are: {regions_db}\n")
    print(f"First region and peak are: {regions_db[0].peaks[0]}\n")
    print(f"First region and pass are: {regions_db[0].passes[0]}\n")


@click.command(no_args_is_help=True)
@click.option("-j", "--json", is_flag=True, help="Write to 'output-[kind].json'")
# @click.option("-s", "--sqlite", type=click.File(), help="Write to SQLite DB at path")
@click.option("-s", "--sqlite", is_flag=True, help="Write to SQLite DB at path")
def main(json, sqlite):
    """ Parse A Climber's Guide to the High Sierra HTML files and output them
    as desired. """
    if json:
        return output_json()
    elif sqlite:
        return output_sqlite()
