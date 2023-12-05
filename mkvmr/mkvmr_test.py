import unittest
import mkvmr
import pathlib
import os


class TestMkvmrMethods(unittest.TestCase):
    def setUp(self):
        self.data_path = pathlib.Path(
            os.path.dirname(__file__)).joinpath('data')
        self.aircraft_path = pathlib.Path(
            os.path.dirname(__file__)).joinpath(
            '../fsltl-traffic-base/SimObjects/Airplanes')

    def test_smoke(self):
        indexer = mkvmr.Indexer(self.data_path, self.aircraft_path)
        indexer.scan()
        indexer.index()

    # This test should be in cfgfile_test.py
    def test_base_resolution(self):
        indexer = mkvmr.Indexer(self.data_path, self.aircraft_path)
        indexer.scan()
        indexer.index()
        ups_md11 = indexer.fsltl_type_designators['MD11'].cfgs['UPS']
        self.assertTrue(len(ups_md11) == 1, ups_md11)
        ups_md11 = ups_md11[0]
        # ups_md11's is a fltsim section, find the config, and the general section
        general = ups_md11.cfgfile['GENERAL']
        self.assertTrue(len(general.dict) == 1)
        self.assertTrue('Category' in general)
        self.assertTrue(general['Category'] == 'airplane')


if __name__ == '__main__':
    unittest.main()
