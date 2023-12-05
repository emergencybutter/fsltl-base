"""Match icao types according to aircraft properties.

This module relies on the compare function that will score how two
aircrafts are dissimilar. Higher score the most different.
"""

import json
import csv


class IcaoJson:
    """Load a json file containing all the icaos.

    Track them per ICAO designator. Note that the file may contain more than
    one aircraft with the same designator in which case we keep one arbitrary aircraft.
    """

    def __init__(self, path):
        self.json_path = path
        self.dict = {}

    def load(self):
        with open(self.json_path, 'rb') as fp:
            data = json.load(fp)
        for item in data:
            self.dict[item['Designator']] = item

    def get(self, icao):
        if icao in self.dict:
            return self.dict[icao]
        return None

    def all_designators(self):
        return self.dict.keys()


class CharacteristicsCsv:
    def __init__(self, path):
        self.csv_path = path
        self.dict = {}

    def load(self):
        with open(self.csv_path, encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                self.dict[row['FAA_Designator']] = row

    def get(self, icao):
        if icao in self.dict:
            return self.dict[icao]
        return None


def compare(
        left_icao_data, left_faa_data, right_icao_data, right_faa_data,
        trace: bool = False):
    diff = 0
    log = []

    def add(d, debug_string):
        nonlocal diff, log
        if d:
            diff += abs(d)
            log.append(f'{diff} (+{abs(d)}): {debug_string}')
    # Landplanes and helicopters seaplanes are very different looking:
    if left_icao_data['AircraftDescription'] != right_icao_data['AircraftDescription']:
        add(1000000,
            f'AircraftDescription: {left_icao_data["AircraftDescription"]} {right_icao_data["AircraftDescription"]}')

    def engine_count(x):
        # gannet fairey has a C, probably because it has with a double
        # turboprop engine driving two contra-rotating propellers.
        if x == "C":
            return 1
        return int(x)
    # Aircraft with the Same number of engines are more likely to look alike.
    add((engine_count(
        left_icao_data['EngineCount']) - engine_count(right_icao_data['EngineCount'])) * 10,
        f'engine_count: {engine_count(left_icao_data["EngineCount"])} {engine_count(right_icao_data["EngineCount"])}')

    # Same kind of engines also better
    if left_icao_data['EngineType'] != right_icao_data['EngineType']:
        add(10000,
            f'EngineType: {left_icao_data["EngineType"]} {right_icao_data["EngineType"]}')

    # wake turublence groups, the more appart the more different
    # https://www.icao.int/APAC/Meetings/2021%20RECAT%20Webinar/1.%20Introduction%20to%20RECAT_ICAO.pdf
    # How to convert a pound difference to "looks".
    LB_WEIGHT_FTSQ_WATER = 62.41
    if left_icao_data['WTG'] and right_icao_data['WTG']:
        wtg_metric = {'A': 9400, 'B': 77000, 'C': 90000, 'D': 100000,
                      'E': 136000, 'F': 300000, 'G': 575000, 'Z': 1000000}
        add((wtg_metric[left_icao_data['WTG']] -
             wtg_metric[right_icao_data['WTG']]) / LB_WEIGHT_FTSQ_WATER,
            f"WTG: {left_icao_data['WTG']} {right_icao_data['WTG']}")
    else:
        # Wake turubulence category
        if left_icao_data['WTC'] and right_icao_data['WTC']:
            wtc_metric = {'L': 3500, 'L/M': 10000,
                          'M': 71500, 'H': 150000, 'J': 575000}
            add((wtc_metric[left_icao_data['WTC']] -
                 wtc_metric[right_icao_data['WTC']]) / LB_WEIGHT_FTSQ_WATER,
                f"WTG {left_icao_data['WTC']} {right_icao_data['WTC']}")

    if left_icao_data['ManufacturerCode'] != right_icao_data['ManufacturerCode']:
        # Different manufacturer
        add(100,
            f"Manufacturer: {left_icao_data['ManufacturerCode']} != {right_icao_data['ManufacturerCode']}")
    if left_faa_data and right_faa_data:
        # Ignore winglets or shardlets
        def wingspan(faa):
            w = faa['Wingspan_ft_without_winglets_sharklets']
            if not w:
                w = faa['Wingspan_ft_with_winglets_sharklets']
            return float(w)
        add(wingspan(left_faa_data) - wingspan(right_faa_data),
            f"Wingspan: {wingspan(left_faa_data)} - {wingspan(right_faa_data)}")
        add(float(left_faa_data['Length_ft']) - float(right_faa_data['Length_ft']),
            f"length: {left_faa_data['Length_ft']} {right_faa_data['Length_ft']}")
    else:
        # In order to give priority to similar aircrafts with additional faa data, we add an arbitrary value here.
        add(75, f'no faa data')
    if trace:
        return diff, log
    return diff

class IcaoNotFound(Exception):
    pass


class RightIcaoNotFound(Exception):
    pass


class LeftIcaoNotFound(Exception):
    pass


class AircraftMatcher:
    SIMILAR_THESHOLD = 300

    def __init__(
            self, icao_json_path, aircraft_charasteristics_csv_path):
        self.icao_json = IcaoJson(icao_json_path)
        self.icao_json.load()
        self.faa_csv = CharacteristicsCsv(aircraft_charasteristics_csv_path)
        self.faa_csv.load()

    def all_designators(self) -> [str]:
        return self.icao_json.all_designators()

    def compare(
            self, left_icao: str, right_icao: str, trace: bool = False) -> float:
        left_icao_data = self.icao_json.get(left_icao)
        if not left_icao_data:
            raise LeftIcaoNotFound(
                f'ICAO not found if the ICAO database: {left_icao}')
        left_faa_data = self.faa_csv.get(left_icao)

        right_icao_data = self.icao_json.get(right_icao)
        if not right_icao_data:
            raise RightIcaoNotFound(
                f'ICAO not found if the ICAO database: {right_icao}')
        right_faa_data = self.faa_csv.get(right_icao)
        return compare(
            left_icao_data, left_faa_data, right_icao_data, right_faa_data,
            trace)

    def is_chopper_or_rotorcraft(self, icao: str) -> bool:
        icao_data = self.icao_json.get(icao)
        if not icao_data:
            raise IcaoNotFound(
                f'ICAO not found if the ICAO database: {icao}')
        return icao_data["AircraftDescription"] in ["Helicopter", "Gyrocopter"]

    def most_similar_among(
            self, missing_icao: str, available_icaos: [str]) -> str:
        """Find an icao in available_icaos that is similar the most similar to missing icao."""
        lowest_diff = float('inf')
        lowest_diff_aircraft = None
        for available_aircraft in available_icaos:
            try:
                icao_diff = self.compare(missing_icao, available_aircraft)
            except RightIcaoNotFound:   # Must not be a real icao code such as ASOBO4J
                continue
            if icao_diff < lowest_diff:
                lowest_diff = icao_diff
                lowest_diff_aircraft = available_aircraft
        return lowest_diff_aircraft

    def somewhat_similar_among(
            self, missing_icao: str, available_icaos: [str]) -> [str]:
        """Find all icaos that are somewhat similar according to some heuristics."""
        ret = set()
        for icao_designator in available_icaos:
            try:
                icao_diff = self.compare(missing_icao, icao_designator)
            except RightIcaoNotFound:   # Must not be a real icao code such as ASOBO4J
                continue
            if icao_diff < self.SIMILAR_THESHOLD:
                ret.add(icao_designator)
        return ret
