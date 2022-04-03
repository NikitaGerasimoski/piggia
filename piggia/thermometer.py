#!/usr/bin/env python3

import os
import sys
import subprocess
import time
import sqlite3
import yaml
import board
import adafruit_max31865
import digitalio




class NoThermometerError(Exception):
    '''
    This Error is raised if:
    - no thermometers are found, or
    - the thermometer you specified is not found
    '''
    pass

class Thermometer:
    """
    Represents a DS18B20 thermometer.
    """
    spi = board.SPI()
    cs = digitalio.DigitalInOut(board.D5)
    sensor = adafruit_max31865.MAX31865(spi, cs, wires=3)

    CREATE_TEMPERATURE_TABLE = """
        CREATE TABLE IF NOT EXISTS temperature (
            timestamp DATETIME,
            temp NUMERIC);
        DROP TRIGGER IF EXISTS rowcount;
        CREATE TRIGGER IF NOT EXISTS rowcount
        BEFORE INSERT ON temperature
        WHEN (SELECT COUNT(*) FROM temperature) >= {}
        BEGIN
            DELETE FROM temperature WHERE timestamp NOT IN (
                SELECT timestamp FROM temperature
                ORDER BY timestamp DESC
                LIMIT {}
            );
        END
    """

    def __init__(self, therm_id=None):
        """
        Set up a thermometer.

        Args:
        * therm_id: thermometer ID, without the '28-'
          prefix. If none is specified, choose the
          first thermometer in lexographical order.
        """

        

    def get_temperature(self):
        """
        Return the current temperature in degrees Celcius.
        If thermometer is not ready, returns None. If
        thermometer is not found, raises a
        NoThermometerError.
        """
        current = self.sensor.temperature
        if (current < 0):
            return None
        return current

    def log_to_sqlite_db(self, db_file, time_gap=1, max_entries=10**6):
        """
        Log temperatures to an sqlite database until
        interrupted.

        Arguments:
        * db_file: sqlite database file to write to
        * time_gap: amount of time to sleep between
            thermometer reads, in seconds
        * max_entries: maximum number of entries to put
            in table --- if the table size exceeds this
            number, the oldest entries start getting
            dropped.
        """
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.executescript(self.CREATE_TEMPERATURE_TABLE.format(
            max_entries, max_entries))

        while True:
            try:
                cursor.execute("INSERT INTO temperature values("
                        "datetime('now'), {})".format(self.get_temperature()))
                conn.commit()
                time.sleep(time_gap)
                print("Temperature: {0:0.3f}C".format(self.get_temperature()))
            except KeyboardInterrupt:
                conn.commit()
                conn.close()
                break

def main():
    """
    A little function to test the Thermometer class. Just
    outputs a line every ~five seconds with the amount
    of time elapsed since the program started and the
    current temperature, separated by a comma.
    """
    # load configuration file
    config = yaml.safe_load(open(sys.argv[1], 'r'))

    therm = Thermometer()
    therm.log_to_sqlite_db(config['db_path'])

if __name__ == "__main__":
    main()
