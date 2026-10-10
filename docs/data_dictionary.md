# Data dictionary (Phase 2 draft)

Generated from observed headers and shallow profiling. Meanings, units, timestamp policy, and target selection require review.

| Observed column | Initial evidence | Nulls | Sample values |
|---|---|---:|---|
| `City` | possible location | 0 | Delhi; Mumbai; Chennai |
| `Datetime` | possible timestamp | 2,402 | 2015-01-01 00:00:00; 2015-01-01 00:00:00; 2015-01-01 00:00:00 |
| `PM2.5` | possible pollutant/AQI, numeric-like sample | 0 | 258.0; 120.1; 130.1 |
| `PM10` | possible pollutant/AQI, numeric-like sample | 0 | 340.6; 47.9; 375.0 |
| `NO` | numeric-like sample | 2,402 | 191.0; 165.3; 21.9 |
| `NO2` | possible pollutant/AQI, numeric-like sample | 0 | 13.4; 57.9; 23.7 |
| `NOx` | numeric-like sample | 2,402 | 104.1; 139.2; 205.6 |
| `NH3` | numeric-like sample | 2,402 | 16.2; 14.4; 33.6 |
| `CO` | numeric-like sample | 0 | 1.15; 0.76; 3.5 |
| `SO2` | possible pollutant/AQI, numeric-like sample | 0 | 39.8; 3.3; 63.0 |
| `O3` | possible pollutant/AQI, numeric-like sample | 0 | 70.4; 23.2; 138.9 |
| `Benzene` | numeric-like sample | 2,402 | 11.64; 11.35; 16.3 |
| `Toluene` | numeric-like sample | 2,402 | 10.23; 11.38; 24.07 |
| `Xylene` | numeric-like sample | 2,402 | 1.95; 1.53; 0.56 |
| `AQI` | possible pollutant/AQI, numeric-like sample | 0 | 411.5; 134.8; 329.6 |
| `AQI_Bucket` | possible pollutant/AQI | 2,402 | Moderate; Poor; Poor |
| `Date` | possible timestamp | 379,941 | 01/01/18; 02/01/18; 03/01/18 |
| `Station` | possible location | 338,603 | Station_D1; Station_D2; Station_M1 |
