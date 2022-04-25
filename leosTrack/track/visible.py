"""Compute visibility of LEO sats according to observation constraints"""
import datetime

import ephem
import numpy as np
from pyorbital.orbital import Orbital

from leosTrack.units import ConvertUnits

###############################################################################
CONVERT = ConvertUnits()


class ComputeVisibility:
    """Class to compute whether a satellite is visible or not"""

    def __init__(
        self,
        time_parameters: dict,
        observatory_data: dict,
        observation_constraints: dict,
        tle_file_location: str,
    ):
        """
        PARAMETERS

            time_parameters: parameters of the observation date

                if custom_window is True,
                [
                    ('year', year of observation, eg, '2021')
                    ('month', month of observation, eg, '11'),
                    ('day', day of observation, eg, '25'),
                    ('delta', time step resolution in seconds, eg, '60'),
                    ('window', either 'morning' or 'evening')
                ]

                if custom_window is False,
                if custom_window is True,
                [
                    ('year', '2021')
                    ('month', '11'),
                    ('day', '25'),
                    # observation starts at 22[h]: 30[m]: 56[s]
                    ('start_hour', '22')
                    ('start_minute', '30'),
                    ('start_second', '56'),
                    # observation finishes at 02[h]: 20[m]: 15[s]
                    ('finish_hour', '02')
                    ('finish_minute', '20'),
                    ('finish_second', '15'),
                    ('delta', time step resolution in seconds, eg, '60'),
                ]

            observatory_data: contains parameters of observatory
                {
                    'name': 'European Southern Observatory, La Silla',
                    'longitude': [70, 43.8], # entries for [deg, ', ']
                    'latitude': [-29, 15.4],
                    'altitude': 2347.0, # in meters above sea level
                    'tz': 4
                }

            observation_constraints: constrains for visibility of a satellite
                {
                    'observatory': 'lasilla'
                    'satellite': 'oneweb'

                    # lower bound for altitude of satellite to be
                    # considered visible, in [units]

                    'lowest_altitude_satellite': '30' # degree

                    # if sun zenith is between these bounds satellite
                    # is considered baseurl

                    'sun_zenith_lowest': '97' # degree
                    'sun_zenith_highest': '114' # degree
                }

            tle_file_location: path to tle file used to compute visibility
        """
        #######################################################################

        self.time_parameters = time_parameters
        # if time_delta = 60, then it will move minute by minute
        self.time_delta = datetime.timedelta(seconds=time_parameters["delta"])

        # from heredo:
        self.observatory_data = self.set_observatory_data(observatory_data)
        # import sys
        # sys.exit()

        self.constraints = observation_constraints

        self.tle_file_location = tle_file_location

        self.observer = None
        # self._set_observer()

    def get_satellite_ra_dec_from_azimuth_and_altitude(
        self, satellite_azimuth: float, satellite_altitude: float
    ) -> list:
        """
        Compute satellite RA [hh, mm, ss] and DEC [dd, mm, ss] using
        satellite's azimuth and altitude in degrees.

        PARAMETERS
            satellite_azimuth: [degree]
            satellite_altitude: [degree]

        OUTPUTS
            [
                [ra_satellite_h, ra_satellite_m, ra_satellite_s],
                [dec_satellite_d, dec_satellite_m, dec_satellite_s]
            ]

        """

        [
            right_ascension_satellite,
            declination_satellite,
        ] = self.observer.radec_of(
            np.radians(satellite_azimuth), np.radians(satellite_altitude)
        )
        ##################################################################
        [
            ra_satellite_h,
            ra_satellite_m,
            ra_satellite_s,
        ] = CONVERT.right_ascension_in_radians_to_hh_mm_ss(
            right_ascension=right_ascension_satellite
        )

        [
            dec_satellite_d,
            dec_satellite_m,
            dec_satellite_s,
        ] = CONVERT.declination_in_radians_to_dd_mm_ss(
            declination=declination_satellite
        )

        return [
            [ra_satellite_h, ra_satellite_m, ra_satellite_s],
            [dec_satellite_d, dec_satellite_m, dec_satellite_s],
        ]

    ###########################################################################
    def _set_dark_satellite(self, satellite: str) -> Orbital:
        """
        Set dark satellite object for orbital computations

        PARAMETERS
            satellite: name of the satellite to work on that is present
                the tle_file provided for the computations, eg, "ONEWEB-0008"

        OUTPUTS
            dark_satellite: instance of class pyorbital.orbital.Orbital

        """

        dark_satellite = Orbital(satellite, tle_file=self.tle_file_location)

        return dark_satellite

    ###########################################################################
    def _set_observer(self) -> None:
        """
        Set location on earth from which the observation of dark satellites
        will be made. The observe, an instance of ephem.Observer, allows
        to compute the position of celestial bodies from the selected
        location, in this case, the observatory location
        """

        observer = ephem.Observer()
        observer.epoch = "2000"
        observer.pressure = 1010
        observer.temp = 15
        #######################################################################
        observatory_latitude = self.observatory_data["latitude"]  # degrees
        observer.lat = np.radians(observatory_latitude)
        #######################################################################
        observatory_longitude = self.observatory_data["longitude"]  # degrees
        observer.lon = np.radians(observatory_longitude)
        #######################################################################
        observer.elevation = self.observatory_data["altitude"]  # in meters
        self.observer = observer

    ###########################################################################
    @staticmethod
    def set_observatory_data(data_observatory: dict) -> dict:
        """
        Transform data from observatories.txt file at home to degree in float.
        In the original file, longitude is possitive to the west.
        In the output, longitude is negative to the west

        PARAMETERS
            observatory_data: contains parameters of observatory
            {
                'name': 'European Southern Observatory, La Silla',
                'longitude': [70, 43.8],
                'latitude': [-29, 15.4],
                'altitude': 2347.0, # in meters above sea level
                'tz': 4
            }

        OUTPUTS
            update_observatory_data: update parameters of observatory
            {
                'name': 'European Southern Observatory, La Silla',
                'longitude': -70.73,
                'latitude': -29.256666666666668,
                'altitude': 2347.0,
                'tz': 4
            }
        """
        update_format = {}
        #######################################################################
        for (
            parameter_observatory,
            parameters_values,
        ) in data_observatory.items():

            if isinstance(parameters_values, list) is True:
                sign = 1  # negative to the west and positive to the east
                update_format[parameter_observatory] = 0
                ###############################################################
                for idx, parameter in enumerate(parameters_values):

                    # parameter will be in degrees, minutes and seconds
                    # idx=0 -> degrees
                    # idx=1 -> minutes
                    # idx=2 -> seconds
                    # maybe a lamda function with map?
                    if parameter < 0:
                        sign = -1
                        parameter = abs(parameter)

                    update_format[parameter_observatory] += parameter / (
                        60 ** idx
                    )
                ###############################################################
                update_format[parameter_observatory] = (
                    sign * update_format[parameter_observatory]
                )

            else:
                update_format[parameter_observatory] = parameters_values

            if parameter_observatory == "longitude":

                if update_format[parameter_observatory] > 180.0:
                    update_format[parameter_observatory] = (
                        360 - update_format[parameter_observatory]
                    )

                else:
                    update_format[parameter_observatory] = -update_format[
                        parameter_observatory
                    ]

        update_format["tz"] = datetime.timedelta(hours=data_observatory["tz"])
        return update_format

    ###########################################################################
    def _update_observer_date(self, date_time: datetime.datetime) -> None:

        self.observer.date = ephem.date(date_time)

    ###########################################################################
