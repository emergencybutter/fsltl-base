from typing import Optional, TextIO
import os
import re
import io
import pathlib


class InvalidVariation(Exception):
    pass


# https://discord.com/channels/781587165989175386/1181077957041725480
def _icao_designator_fixup(icao: str):
    if icao == "737":
        return "B737"
    return icao


class Section:
    def __init__(self, cfgfile: 'AircraftCfgFile', name: str):
        self.dict = {}
        self.name = name
        self.cfgfile = cfgfile

    def __setitem__(self, key, value):
        self.dict[key] = value

    def __getitem__(self, key: str):
        if key in self.dict:
            return self.dict[key]
        # Scan for parents with the same section name before giving up.
        for section in self.cfgfile.get_section_bases(self.name):
            if key in section.dict:
                return section.dict[key]
        raise KeyError(f'key {key} not found in {self}')

    def __contains__(self, key: str):
        if key in self.dict:
            return True
        # Scan for parents with the same section name before giving up.
        for section in self.cfgfile.get_section_bases(self.name):
            if key in section.dict:
                return True
        return False

    def __delitem__(self, key: str):
        del self.dict[key]

    def __len__(self):
        return len(self.dict)

    def __repr__(self):
        return f'Section<name: {self.name} dict: {self.dict}>'

    def __iter__(self):
        return self.dict.__iter__()

    def fields(self):
        return self.dict.keys()

    def get(self, k):
        if k in self:
            return self[k]
        return None


def _canonical_path(path):
    return pathlib.Path(path).resolve()


class AircraftCfgFile:
    """Parses and represents a aircraft.cfg file.

    aircraft.cfg contain the MSFS identifier for model and livery combinations
    as well as some aircraft characteristics. As far as I can tell, for a given
    ICAO type code there is only one aircraft.cfg, but there could be multiple
    liveries in a single file. However in the case of FSLTL, each set of
    texture has its own directory and aircraft.cfg. There are some aircraft.cfg
    with multiple instances of the FLTSIM.x section, but I believe they exists
    only to fix details related to msfs internal ATC, so we don't care for
    vatsim/vpilot.
    """

    GENERAL_SECTION = 'GENERAL'
    FLTSIM_SECTION = 'FLTSIM'
    VARIATION_SECTION = 'VARIATION'

    def __init__(self, path: Optional[str]):
        self.path = None
        if path:
            self.path = _canonical_path(path)
        self.sections = {}
        self.base = None

    def set_section(self, name: str, section: Section):
        self.sections[name] = section

    def __getitem__(self, key: str):
        return self.sections[key]

    def __contains__(self, key: str):
        return key in self.sections

    def __repr__(self):
        return f'CfgFile: {repr(self.sections)}'

    @property
    def base_path(self) -> Optional[str]:
        if self.VARIATION_SECTION not in self.sections:
            return None
        return self.sections[self.VARIATION_SECTION]['base_container']

    def set_base(self, base: str):
        self.base = base

    def get_section_bases(self, section_name: str) -> [Section]:
        """Scan for parent sections.

        Note that we don't support index sections (ie FLTSIM.3).
        """
        add_section = []
        if section_name in self:
            add_section = [self[section_name]]
        if self.base:
            return add_section + self.base.get_section_bases(section_name)
        else:
            return add_section

    @property
    def general(self):
        return self.sections[self.GENERAL_SECTION]

    @property
    def icao_type_designator(self):
        return _icao_designator_fixup(self.general['icao_type_designator'])

    @property
    def fltsims(self):
        return self.sections[self.FLTSIM_SECTION]

    def __str__(self):
        return f'AircraftCfg<path: {self.path} sections: {self.sections}>'

    def valid(self) -> bool:
        return (self.GENERAL_SECTION in self.sections and
                self.FLTSIM_SECTION in self.sections and
                self.icao_type_designator)


def _eval_value(value: str):
    """Evaluate the value side of an assignment in a cfg file.

    Probably the weirdest aspect of these cfg files is that the rhs can be a raw string or quoted...
    """
    if value.startswith('"'):
        match = re.fullmatch(r'"(.*)"', value)
        return match[1]
    match = re.fullmatch(r'[0-9]+', value)
    if match:
        return int(match[0])
    match = re.fullmatch(r'[0-9.]+', value)
    if match:
        return float(match[0])
    return value

def loads(buf: str) -> AircraftCfgFile:
    return loadio(path=None, f=io.StringIO(buf))


def load(path: str) -> AircraftCfgFile:
    with open(path, "r") as f:
        return loadio(path, f)


def loadio(path: Optional[str], f: TextIO) -> AircraftCfgFile:
    cfgfile = AircraftCfgFile(path)
    section = None
    section_index = None
    for line_ in f.readlines():
        # Remove comment and end of line
        line = re.sub(r';.*', '', line_.rstrip())
        match = re.fullmatch(
            r'\[(([^\].]+)(?:\.([a-zA-Z0-9_]+))?)\]', line)
        # If a new section
        if match:
            fullname, prefix, suffix = match[1], match[2], match[3]
            section = Section(cfgfile, fullname)
            section_name = prefix
            section_index = None
            sub_match = re.fullmatch(r'[0-9]+', str(suffix))
            if sub_match:
                section_index = int(suffix)
                if section_name not in cfgfile.sections:
                    cfgfile.set_section(section_name, [])
                cfgfile.sections[section_name].append(section)
                assert len(
                    cfgfile.sections[section_name]) == section_index + 1
            else:
                cfgfile.set_section(section_name, section)
        else:
            if not line:
                continue
            # else, the current section
            try:
                key_, value_ = line.split('=', 1)
            except ValueError:
                print(f'{path}: {line}')
                raise
            key, value = key_.rstrip(), value_.strip()
            match = re.fullmatch(r'([a-zA-Z][a-zA-Z_0-9]+)\.([0-9]+)', key)
            if match:
                key = match[1]
                index = int(match[2])
                if key not in section:
                    section[key] = []
                section[key].append(_eval_value(value))
                assert len(section[key]) == index + 1
            else:
                section[key] = _eval_value(value)
    assert cfgfile.valid()
    return cfgfile


def link(cfgfiles: [AircraftCfgFile]):
    path_to_cfgfile = {}
    for cfgfile in cfgfiles:
        path_to_cfgfile[str(cfgfile.path).lower()] = cfgfile
    for cfgfile in cfgfiles:
        if cfgfile.base_path:
            dirname = pathlib.Path(cfgfile.path).parent
            base_path = dirname.joinpath(pathlib.PureWindowsPath(
                cfgfile.base_path)).resolve().joinpath('aircraft.cfg')
            if str(base_path).lower() not in path_to_cfgfile:
                raise InvalidVariation(
                    f'key {str(base_path).lower()} not in {path_to_cfgfile.keys()}')
            cfgfile.set_base(path_to_cfgfile[str(base_path).lower()])


def scan(path: str) -> [AircraftCfgFile]:
    all_aircraft_cfg_files = []
    # Move to cfgfile.py
    with os.scandir(path) as scan:
        for entry in scan:
            if entry.is_dir():
                fullpath = None
                with os.scandir(entry.path) as scan:
                    for entry in scan:
                        if entry.is_file() and entry.name.lower() == "aircraft.cfg":
                            fullpath = entry.path
                if fullpath:
                    try:
                        ac = load(fullpath)
                    except FileNotFoundError:
                        print(f'Warning: {fullpath} not found.')
                        pass
                    if ac.valid():
                        all_aircraft_cfg_files.append(ac)
    link(all_aircraft_cfg_files)
    return all_aircraft_cfg_files


def _fake_file_content(icao: str, titles: [str]) -> str:
    ret = f"""[GENERAL]
icao_type_designator = "{icao}"
"""
    for index, title in enumerate(titles):
        ret += f"""
[FLTSIM.{index}]
title = "{title}" ; Variation name
"""
    return ret

# Here we're listing aircrafts in the default MSFS that are lacking in FSLTL.
# If fsltl has something, we will use it intead, because we're assuming if they bothered
# adding a model of an aircraft instead of reusing the microsoft one they have a resonable reason.
_DEFAULT_AIRCRAFTS = {
    # FSLTL_C208B_ZZZZ
    # "C208": ["Cessna 208B Grand Caravan EX"],
    # SLTL_A20N_ZZZZ//FSLTL_Medium_Generic
    # "A20N": ["Airbus A320 Neo Asobo",
    #          "Airbus A320 Neo Asobo AirTraffic 00",
    #          "Airbus A320 Neo Asobo AirTraffic 01",
    #          "Airbus A320 Neo Asobo AirTraffic 02"],
    # FSLTL_B748_ZZZZ//FSLTL_B748F_ZZZZ
    # "B748": ["Boeing 747-8i Asobo"],
    # FSLTL_GA_BE36_ZZZ
    # "BE36": ["Bonanza G36 Asobo"],
    # FSLTL_GA_C152_ZZZ
    # "C152": ["Cessna 152 Asobo"],
    # FSLTL_GA_C172_ZZZ
    # "C172": ["Cessna Skyhawk G1000 Asobo",
    #          "Cessna 172SP Asobo AirTraffic 00",
    #          "Cessna 172SP Asobo AirTraffic 01",
    #          "Cessna 172SP Asobo AirTraffic 02",
    #          "Cessna 172SP Asobo AirTraffic 03"],
    "CP10": ["Mudry Cap 10 C"],
    # FSLTL_GA_C25C_ZZZ//FSLTL_GA_C25C_M-MIKE//FSLTL_GA_C25C_PS-CSF
    # "C25C": ["Cessna CJ4 Citation Asobo"],
    # FSLTL_GA_DA40-NG_ZZZ//DA40-NG Asobo
    # "DA40": ["DA40-NG Asobo"],
    # FSLTL_GA_DA62_ZZZ//FSLTL_GA_DA62_Sapphire_Blue//FSLTL_GA_DA62_Sapphire_Gold
    # "DA62": ["DA62 Asobo"],
    # FSLTL_GA_DR400_ZZZ
    # "DR40": ["DR400 Asobo"],
    "E300": ["Extra 330 Asobo"],
    "F18H": ["Boeing F/A 18E Super Hornet Asobo"],
    "F18S": ["Boeing F/A 18E Super Hornet Asobo"],
    "FDCT": ["FlightDesignCT Asobo"],
    "A5": ["Icon A5 Asobo"],
    # FSLTL_GA_B350_ZZZZ
    # "B350": ["Beechcraft King Air 350i Asobo"],
    "CC19": ["Asobo NXCub"],
    "PTS2": ["Pitts Asobo"],
    "SAVG": ["Asobo Savage Cub"],
    # FSLTL_GA_TBM9_ZZZ//FSLTL_GA_TBM9_N960DH//FSLTL_GA_TBM9_N960VM
    #"TBM9": ["TBM 930 Asobo",
    #         "TBM 930 Asobo AirTraffic 00",
    #         "TBM 930 Asobo AirTraffic 01",
    #         "TBM 930 Asobo AirTraffic 02"],
    # FSLTL_GA_VL3_ZZZ
    "VL3": ["VL3 Asobo"],
}

def defaults() -> [AircraftCfgFile]:
    ret = []
    for k, v in _DEFAULT_AIRCRAFTS.items():
        ret.append(loads(_fake_file_content(k, v)))
    return ret