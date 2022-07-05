import unittest

import bs4

from climbers_guide_parser import (
    __version__,
    get_passes,
    get_peaks,
    get_region,
    get_soup,
)

# Constants
PREFIX = "/home/scott/Documents/A_Climbers_Guide/"
PALISADES = PREFIX + "palisades.html"
KAWEAHS = PREFIX + "kaweahs_great_western_divide.html"
YOSEMITE = PREFIX + "yosemite_valley.html"


class TestVersion(unittest.TestCase):
    def test_version(self):
        assert __version__ == "0.2.0"


class TestSoup(unittest.TestCase):
    """Verify the soup loads all right."""

    def setUp(self):
        self.soup = get_soup(PALISADES)
        self.peak = self.soup.find(
            "p", class_="peak", string="Disappointment Peak (13,900+; 13,917n)"
        )

    def test_soup_import(self):
        """Make sure the soup is BeautifulSoup."""
        self.assertIsInstance(self.soup, bs4.BeautifulSoup)

    def test_find_a_peak_generally(self):
        """Make sure it's possible to find a peak."""
        self.assertTrue("Disappointment" in self.peak.text)


class TestPeakAndRoute(unittest.TestCase):
    """Test the major features when adding a peak."""

    def setUp(self):
        self.soup = get_soup(PALISADES)
        self.region = get_region(self.soup)
        self.peaks, self.region = get_peaks(self.soup, self.region)
        self.peak2 = self.peaks[8]

    def test_get_peak_name(self):
        """Load a peak from get_peaks()."""
        self.assertTrue(self.peak2.name == "Middle Palisade")

    def test_a_route(self):
        """Try to load a route from an already loaded peak."""
        self.assertTrue(self.peak2.routes[2].name == "Route 3. Northwest ridge")

    def test_get_class(self):
        """Get a class rating."""
        self.assertTrue(self.peak2.routes[2].class_rating == "Class 4")

    def test_an_elevation(self):
        """Verify we can find elevation information."""
        self.assertTrue(self.peak2.elevations[1] == "14,040n")

    def test_a_description(self):
        """Verify we can get a description."""
        self.assertTrue(
            self.peak2.description
            == "First ascent August 26, 1921, by F. P. Farquhar and A. F. Hall, by Route 1 (SCB,"
            " 1922, 264).\n\n"
        )


class TestAlternatePeakNameFormat(unittest.TestCase):
    """
    Some files have a differently formatted peak name line similar to:
    <p><i>Peak 10,400 (2 W of Mount Stewart)</i></p>
    Test it.
    """

    def setUp(self):
        self.soup = get_soup(KAWEAHS)
        self.region = get_region(self.soup)
        self.peaks, self.region = get_peaks(self.soup, self.region)
        self.peak = self.peaks[-5]

    def test_get_peaks(self):
        """Load a peak from get_peaks()."""
        self.assertTrue(self.peak.name == "Peak 10,400")

    def test_get_peak_location(self):
        """Get the peak location as described in the peak name/title."""
        self.assertTrue(self.peak.location_description == "2 W of Mount Stewart")


class TestYosemiteStyleRoutes(unittest.TestCase):
    """
    yosemite_valley.html handles routes a bit different, and many routes are
    simply named rather than using "Route X" as a prefix:
    <p><i>Higher Cathedral Spire (6,114)</i></p>
    <p>
    <i>Southwest face.</i> Maximum class 5.
    First ascent April 15, 1934, by
    """

    def setUp(self):
        self.soup = get_soup(YOSEMITE)
        self.region = get_region(self.soup)
        self.peaks, self.region = get_peaks(self.soup, self.region)
        self.peak = self.peaks[-11]

    def test_get_peaks(self):
        """Load a peak from get_peaks()."""
        self.assertTrue(self.peak.name == "Higher Cathedral Spire")

    def test_a_route(self):
        """Try to load a route from an already loaded peak."""
        self.assertTrue(self.peak.routes[0].name == "Southwest face")


class TestRegions(unittest.TestCase):
    """
    Test some regions.
    """

    def setUp(self):
        self.soup = get_soup(YOSEMITE)
        self.soup_with_passes = get_soup(PALISADES)
        self.region = get_region(self.soup)
        self.peaks, self.region = get_peaks(self.soup, self.region)
        self.passes = get_passes(self.soup_with_passes, self.region)

    def test_get_region_name(self):
        """Get the region name."""
        self.assertTrue(self.region.name == "Yosemite Valley")

    def test_get_peak_region(self):
        """Get the peak's region from within the region list."""
        self.assertTrue(self.region.peaks[18].region == "Yosemite Valley")

    def test_peak_name_in_region(self):
        """Get a peak's name from within the region list."""
        self.assertTrue(self.region.peaks[18].name == "Washington Column")

    def test_pass_name_in_region(self):
        """Get a pass's name from within the region list."""
        self.assertTrue(self.region.passes[1].name == "Jigsaw Pass")


if __name__ == "__main__":
    unittest.main()
