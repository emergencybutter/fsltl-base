import unittest
import aircraftcfg

class TestCfgFile(unittest.TestCase):
    def test_load(self):
        path = "fsltl-traffic-base/SimObjects/Airplanes/FSLTL_MD11F/aircraft.CFG"
        cfg_file = aircraftcfg.load(path)
        self.assertTrue('GENERAL' in cfg_file.sections)
        self.assertTrue('FLTSIM' in cfg_file.sections)
        self.assertTrue(cfg_file['FLTSIM'].__class__ == [].__class__)
        self.assertEqual(len(cfg_file['FLTSIM']), 1)
        self.assertIn('title', cfg_file['FLTSIM'][0])
        self.assertEqual(len(cfg_file['EFFECTS']['effect']), 3)

    def test_scan(self):
        path = "fsltl-traffic-base/SimObjects/Airplanes"
        cfg_files = aircraftcfg.scan(path)
        self.assertGreaterEqual(len(cfg_files), 1000)
        for cfgfile in cfg_files:
            if cfgfile.fltsims[0]['title'] == "FSLTL_FSPXAI_MD11_FDX-Fedex":
                self.assertEqual(cfgfile.base.fltsims[0]['title'], "FSLTL_MD11F_ZZZZ")
                break
                

if __name__ == '__main__':
    unittest.main()

