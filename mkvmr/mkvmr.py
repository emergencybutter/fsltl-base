"""Generate a VMR file from FSLTL files and a heuristic.

FSLTL ships with many aircrafts and liveries. Let's start by indexing them.
We'll start with icao type, then icao airline code.
aircraft.cfg files sometimes have more that one aircraft, but I believe they
all share the same look. They are used to manage the in-game atc and not very
useful for vatsim. However, because I'm not sure, I index all these too and
verify that they don't use the same textures.
Then we'll build a database of all icao codes. For each icao codes well
gather some identifying properties, such as type of engine (prop, turboprop,
jet) number of engine, and size characteristics.
Then we will build a scoring system so that we match the best possible fsltl
model to each icao code.
Finally we dump a VMR file that encodes all that information in one place.
"""

import aircraftcfg
import collections
import os
import re
# We use sqlite3 to dump state to a db for manual analysis.
import sqlite3
import json
import pathlib
import matcher


class InvalidData(Exception):
    pass


class FsltlIcaoType:
    """Track all the aircraft.cfg files and fltsim subsections per icao type designator."""

    def __init__(self, icao_type_designator):
        self.icao_type_designator = icao_type_designator
        self.cfgs = collections.defaultdict(lambda: [])

    def append_cfg(self, cfg, canonicalize):
        for fltsim in cfg.fltsims:
            airline = "undefined"
            if "icao_airline" in fltsim:
                airline = fltsim["icao_airline"]
            if airline.upper() in ('ZZZ', 'ZZZZ', ''):
                airline = "undefined"
            # Here, we the canonical callsign for similar callsigns. ie SHT and
            # BWA are all bundled under BWA.
            self.cfgs[canonicalize(airline)].append(fltsim)
        # There are a bunch of stub aircrafts that add airlines, but don't add
        # liveries. We remove them here.
        undefs = set()
        todel = []
        if "undefined" in self.cfgs:
            for undef in self.cfgs['undefined']:
                undefs.add((undef.cfgfile.path, undef.get(
                    'model'), undef.get('texture')))
        for airline, fltsims in self.cfgs.items():
            filtered = []
            if airline != "undefined":
                for fltsim in fltsims:
                    if (fltsim.cfgfile.path, fltsim.get('model'), fltsim.get('texture')) not in undefs:
                        filtered.append(fltsim)
                if filtered:
                    self.cfgs[airline] = filtered
                else:
                    todel.append(airline)
        for d in todel:
            del self.cfgs[d]

    def airline_fltsims(self):
        return self.cfgs


class AirlineAliases:
    def __init__(self, path):
        self.path = path
        self.dict = {}
        self.canonical_dict = {}

    def load(self):
        with open(self.path, 'rb') as f:
            data = json.load(f)
        for datum in data:
            self.dict[datum['airline_icao']] = datum['aliases']
            for alias in datum['aliases']:
                self.canonical_dict[alias] = datum['airline_icao']

    def aliases(self, airline):
        if airline in self.dict:
            return self.dict[airline]
        return []

    def canonical(self, airline):
        if airline in self.canonical_dict:
            return self.canonical_dict[airline]
        return airline

    def all_aliases(self):
        ret = []
        for aliases in self.dict.values():
            ret = ret + aliases
        return ret


class Indexer:
    def __init__(self, data_path, path):
        self.path = path
        self.data_path = data_path
        self.all_cfg = []
        self.fsltl_type_designators = {}
        self.airline_aliases = self._load_aliases()
        self.airline_to_fsltl_icaos = collections.defaultdict(lambda: [])

    def scan(self):
        self.all_cfg = aircraftcfg.scan(self.path) + aircraftcfg.defaults()

    def index(self):
        for a in self.all_cfg:
            if a.icao_type_designator in self.fsltl_type_designators:
                icao_type = self.fsltl_type_designators[a.icao_type_designator]
            else:
                icao_type = FsltlIcaoType(a.icao_type_designator)
                self.fsltl_type_designators[a.icao_type_designator] = icao_type
            icao_type.append_cfg(
                a, lambda a: self.airline_aliases.canonical(a))
            for airline in icao_type.airline_fltsims().keys():
                if airline != "undefined":
                    self.airline_to_fsltl_icaos[airline].append(a)

    def list(self):
        ret = []
        for code in self.fsltl_type_designators.keys():
            configs = self.fsltl_type_designators[code].cfgs.keys()
            for config in configs:
                ret.append(f'{code}: {config}')
        return ret

    def _load_aliases(self):
        airline_aliases = AirlineAliases(
            f'{self.data_path}/airline_aliases.json')
        airline_aliases.load()
        return airline_aliases

    def dump(self, output):
        data = matcher.AircraftMatcher(
            f'{self.data_path}/icao.json',
            f'{self.data_path}/aircraft-characteristics.csv')
        lines = []
        for icao_designator in data.all_designators():
            title_list = None
            # MSFS does not accept external program adding helis.
            if data.is_chopper_or_rotorcraft(icao_designator):
                continue
            similar_fsltl = data.most_similar_among(
                icao_designator, self.fsltl_type_designators.keys())
            icao_type = self.fsltl_type_designators[similar_fsltl]
            # We need to be a little better here, if airline is undefined, dump
            # the most similar plane. However ignore entries with airlines
            # then for each airlines, compile a list of icao type designators
            # of aircrafts that can be matched well enough.
            fltsims = icao_type.airline_fltsims()["undefined"]
            title_list = [f['title'] for f in fltsims]
            titles = '//'.join(title_list)
            print(
                f'Generic match: {icao_designator} -> {similar_fsltl} ({titles})')
            lines.append(
                f'<ModelMatchRule TypeCode="{icao_designator}" ModelName="{titles}" />\n')
        for airline, fsltl_icaos in self.airline_to_fsltl_icaos.items():
            # Build a list of types for which we have models for the current airline.
            airline_type_designators = set(
                [fsltl_icao.icao_type_designator for fsltl_icao in fsltl_icaos])
            # Collect these types and similar types.
            similar_type_designators = set()
            for airline_type_designator in airline_type_designators:
                #print(
                #    f'YYY {airline_type_designator} -> {data.somewhat_similar_among(airline_type_designator, data.all_designators())}')
                similar_type_designators = similar_type_designators.union(
                    data.somewhat_similar_among(airline_type_designator, data.all_designators()))
            # Dump an airline entry for each type that is similar to something we have a livery for, for this airline.
            for icao_designator in similar_type_designators:
                similar_fsltl = data.most_similar_among(
                    icao_designator, airline_type_designators)
                icao_type = self.fsltl_type_designators[similar_fsltl]
                fltsims = icao_type.airline_fltsims()[airline]
                titles = '//'.join([f['title'] for f in fltsims])
                for alias in [airline] + self.airline_aliases.aliases(airline):
                    print(
                        f'Airline match: {airline} {alias}, {icao_designator} -> {similar_fsltl} ({titles})')
                    lines.append(
                        f'<ModelMatchRule CallsignPrefix="{alias}" ' +
                        f'TypeCode="{icao_designator}" ModelName="{titles}" />\n')
        prefix_lines = ['<?xml version="1.0" encoding="utf-8"?>\n',
                        '<ModelMatchRuleSet>\n']
        suffix_lines = ['</ModelMatchRuleSet>\n']
        with open(output, 'w') as fout:
            fout.writelines(prefix_lines + lines + suffix_lines)

    def dump_similar(self):
        data = matcher.AircraftMatcher(
            f'{self.data_path}/icao.json',
            f'{self.data_path}/aircraft-characteristics.csv')
        for icao_designator in data.all_designators():
            similar = data.most_similar_among(
                icao_designator, self.fsltl_type_designator)
            print(f'{icao_designator} -> {similar}')


def dump(indexer):
    cnx = sqlite3.connect("dump.db")
    cursor = cnx.cursor()
    cursor.execute("DROP TABLE IF EXISTS fsltl_aircraft;")
    cursor.execute(
        "CREATE TABLE fsltl_aircraft(Category, performance, wip_indicator,icao_type_designator, icao_manufacturer, icao_model, icao_engine_type, icao_engine_count, icao_WTC, icao_generic);")
    for aircraft in indexer.all_cfg:
        cursor.execute(
            f"INSERT INTO fsltl_aircraft VALUES ({','.join(['?']*10)});",
            [aircraft.general.get('Category'),
             aircraft.general.get('performance'),
             aircraft.general.get('wip_indicator'),
             aircraft.general.get('icao_type_designator'),
             aircraft.general.get('icao_manufacturer'),
             aircraft.general.get('icao_model'),
             aircraft.general.get('icao_engine_type'),
             aircraft.general.get('icao_engine_count'),
             aircraft.general.get('icao_WTC'),
             aircraft.general.get('icao_generic')])
    cnx.commit()


def main():
    indexer = Indexer(pathlib.Path(
        os.path.dirname(__file__)).joinpath('data'),
        pathlib.Path(
        os.path.dirname(__file__)).joinpath(
        '../fsltl-traffic-base/SimObjects/Airplanes'))

    indexer.scan()
    indexer.index()
    indexer.dump('output.vmr')
    # dump(indexer)


if __name__ == "__main__":
    main()
