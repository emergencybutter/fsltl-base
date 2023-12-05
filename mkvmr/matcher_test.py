import unittest
import matcher
import os
import pathlib
import mkvmr


class TestMatcher(unittest.TestCase):
    AVAILABLE = [
        'A319',
        'A320',
        'A321',
        'A332',
        'A333',
        'A359',
        'A388',
        'B737',
        'B738'
    ]

    def test_compare(self):
        m = matcher.AircraftMatcher(
            pathlib.Path(os.path.dirname(__file__)).joinpath('data/icao.json'),
            pathlib.Path(os.path.dirname(__file__)).joinpath(
                'data/aircraft-characteristics.csv'))
        self.assertEqual(m.compare('A306', 'A306'), 0)
        cessna_diff, log = m.compare('C152', 'A332', trace=True)
        diff, log = m.compare('A306', 'A332', trace=True)
        self.assertLess(diff, cessna_diff, msg='\n'.join(log))

    def test_similarity(self):
        m = matcher.AircraftMatcher(
            pathlib.Path(os.path.dirname(__file__)).joinpath('data/icao.json'),
            pathlib.Path(os.path.dirname(__file__)).joinpath(
                'data/aircraft-characteristics.csv'))
        self.assertEqual(m.most_similar_among('A319', self.AVAILABLE), 'A319')
        self.assertEqual(m.most_similar_among('A320', self.AVAILABLE), 'A320')
        self.assertEqual(m.most_similar_among('A321', self.AVAILABLE), 'A321')
        self.assertEqual(m.most_similar_among('A332', self.AVAILABLE), 'A332')
        self.assertEqual(m.most_similar_among('A333', self.AVAILABLE), 'A333')
        self.assertEqual(m.most_similar_among('A359', self.AVAILABLE), 'A359')
        self.assertEqual(m.most_similar_among('A388', self.AVAILABLE), 'A388')
        self.assertEqual(m.most_similar_among('B737', self.AVAILABLE), 'B737')
        self.assertEqual(m.most_similar_among('B738', self.AVAILABLE), 'B738')
        self.assertEqual(m.most_similar_among("A306", self.AVAILABLE), 'A321')
        self.assertEqual(m.most_similar_among("A310", self.AVAILABLE), 'A321')
        self.assertEqual(m.most_similar_among("A319", self.AVAILABLE), 'A319')
        self.assertEqual(m.most_similar_among("A320", self.AVAILABLE), 'A320')
        self.assertEqual(m.most_similar_among("A321", self.AVAILABLE), 'A321')
        self.assertEqual(m.most_similar_among("A332", self.AVAILABLE), 'A332')
        self.assertEqual(m.most_similar_among("A333", self.AVAILABLE), 'A333')
        self.assertEqual(m.most_similar_among("A338", self.AVAILABLE), 'A332')
        self.assertEqual(m.most_similar_among("A339", self.AVAILABLE), 'A333')
        self.assertEqual(m.most_similar_among("A342", self.AVAILABLE), 'A332')
        self.assertEqual(m.most_similar_among("A343", self.AVAILABLE), 'A333')
        self.assertEqual(m.most_similar_among("A345", self.AVAILABLE), 'A359')
        self.assertEqual(m.most_similar_among("A346", self.AVAILABLE), 'A359')
        self.assertEqual(m.most_similar_among("A359", self.AVAILABLE), 'A359')
        self.assertEqual(m.most_similar_among("A35K", self.AVAILABLE), 'A359')
        self.assertEqual(m.most_similar_among("A388", self.AVAILABLE), 'A388')
        # babyyyy beluuuuuuga
        self.assertEqual(m.most_similar_among("A3ST", self.AVAILABLE), 'A319')
        self.assertEqual(m.most_similar_among("B732", self.AVAILABLE), 'B737')
        self.assertEqual(m.most_similar_among("B733", self.AVAILABLE), 'B737')
        self.assertEqual(m.most_similar_among("B734", self.AVAILABLE), 'B737')
        self.assertEqual(m.most_similar_among("B735", self.AVAILABLE), 'B737')
        self.assertEqual(m.most_similar_among("B736", self.AVAILABLE), 'B737')
        self.assertEqual(m.most_similar_among("B737", self.AVAILABLE), 'B737')
        self.assertEqual(m.most_similar_among("B738", self.AVAILABLE), 'B738')

    def test_ga_similarity(self):
        data_path = pathlib.Path(
            os.path.dirname(__file__)).joinpath('data')
        aircraft_path = pathlib.Path(
            os.path.dirname(__file__)).joinpath(
            '../fsltl-traffic-base/SimObjects/Airplanes')
        indexer = mkvmr.Indexer(data_path, aircraft_path)
        indexer.scan()
        indexer.index()
        available = set(indexer.fsltl_type_designators.keys())

        m = matcher.AircraftMatcher(
            pathlib.Path(os.path.dirname(__file__)).joinpath('data/icao.json'),
            pathlib.Path(os.path.dirname(__file__)).joinpath(
                'data/aircraft-characteristics.csv'))
        self.assertEqual(m.most_similar_among('SR22', available), 'DA40')
        self.assertEqual(m.most_similar_among('DA62', available), 'DA62')
        self.assertEqual(m.most_similar_among('GLF5', available), 'E170')

    def test_somewhat(self):

        m = matcher.AircraftMatcher(
            pathlib.Path(os.path.dirname(__file__)).joinpath('data/icao.json'),
            pathlib.Path(os.path.dirname(__file__)).joinpath(
                'data/aircraft-characteristics.csv'))
        self.assertEqual(
            set(
                [
                 'A148',
                 'A178',
                 'A743',
                 'AN72',
                 'B712',
                 'B732',
                 'B733',
                 'B734',
                 'B735',
                 'BA11',
                 'C1',
                 'C56X',
                 'CL35',
                 'DC92',
                 'DC93',
                 'DC94',
                 'DC95',
                 'E190',
                 'E195',
                 'F100',
                 'F70',
                 'GA4C',
                 'GA5C',
                 'GA6C',
                 'GA7C',
                 'GA8C',
                 'GJ11',
                 'GL5T',
                 'GL7T',
                 'GLEX',
                 'GLF5',
                 'GLF6',
                 'J20',
                 'KF21',
                 'KZLA',
                 'SU95',
                 'T134',
                 'T334',
                 'X59',
                 ]),
            m.somewhat_similar_among(
                "E190", m.all_designators()))


if __name__ == '__main__':
    unittest.main()
