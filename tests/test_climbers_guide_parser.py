import unittest

from climbers_guide_parser import __version__
from climbers_guide_parser import get_soup, get_peaks
import bs4

# Constants
PALISADES = "/home/scott/Documents/A_Climbers_Guide/palisades.html"

class TestVersion(unittest.TestCase):
    def test_version(self):
        assert __version__ == '0.1.0'

class TestSoup(unittest.TestCase):

    def setUp(self):
        self.soup = get_soup(PALISADES)
        self.peak = self.soup.find("p", class_="peak", string="Disappointment Peak (13,900+; 13,917n)")
        self.peaks = get_peaks(self.soup)
        self.peak2 = self.peaks[8]

    def test_soup_import(self):
        """ Make sure the soup is BeautifulSoup. """
        self.assertIsInstance(self.soup, bs4.BeautifulSoup)

    def test_find_a_peak_generally(self):
        """ Make sure it's possible to find a peak. """
        self.assertTrue("Disappointment" in self.peak.text)


    def test_get_peaks(self):
        """ Load a peak from get_peaks(). """
        self.assertTrue(self.peak2.name == "Middle Palisade")

    def test_a_route(self):
        """ Try to load a route from an already loaded peak. """
        self.assertTrue(self.peak2.routes[2].name == "Route 3. Northwest ridge")

    def test_get_class(self):
        """ Get a class rating. """
        self.assertTrue(self.peak2.routes[2].class_rating == "Class 4")


    def test_an_elevation(self):
        """ Verify we can find elevation information. """
        self.assertTrue(self.peak2.elevations[1] == "14,040n")

    def test_a_description(self):
        """ Verify we can get a description. """
        self.assertTrue(self.peak2.description == "First ascent August 26, 1921, by F. P. Farquhar and A. F. Hall, by Route 1 (SCB, 1922, 264).\n\n")
        

if __name__ == '__main__':
    unittest.main()
