import sys
import datetime
import multiprocessing as mp

import ephem
import numpy as np
import pyorbital
from pyorbital.orbital import Orbital

from SatTrack.format import format
from SatTrack.units import ConvertUnits
from SatTrack.observatory import get_observatory_data
###############################################################################
def init_download_worker(input_counter):
    """
    Initialize worker for download
    PARAMETERS
    counter:
    """
    global counter

    counter = input_counter
###############################################################################
class Compute:
    """Class to compute whether a satellite is visible or not"""

    def __init__(self,
        satellite: "str",
        time_parameters: "dictionary",
        observatory_data: "dictionary",
        tle_file_location: "str",
        ):
        """
        PARAMETERS

            day: day of observation
            window: specifies if observation is either morning or evening
            time_zone: time zone of the observatory


        """
        window = time_parameters["window"]

        if window not in ["morning", "evening"]:
            print(f'window keyword must be of either "morning" or "evening"')
            sys.exit()

        self.satellite = satellite
        # self.window = time_parameters["window"]
        self.time_parameters = self.set_time_parameters(time_parameters)


        self.observatory_data = self._set_observatory_data(observatory_data)

        self.tle_file_location = tle_file_location

        # self.observer = None


    ###########################################################################
    def compute_visibility_of_satellite(self):

        # if time_delta = 60, then it will move minute by minute
        delta_in_seconds = self.time_parameters["delta"]
        time_delta_in_seconds = datetime.timedelta(seconds=delta_in_seconds)

        [hour, day] = self.set_window()

        date_time = datetime.datetime(
            year=self.time_parameters["year"],
            month=self.time_parameters["month"],
            day=day,
            hour=hour,
            minute=0,
            second=0
        )

        return [time_delta_in_seconds, date_time]
    ###########################################################################
    def set_time_parameters(self, time_parameters: "dictionary"):

        time_parameters["year"] = int(time_parameters["year"])
        time_parameters["month"] = int(time_parameters["month"])
        time_parameters["day"] = int(time_parameters["day"])
        time_parameters["delta"] = float(time_parameters["delta"])

        return time_parameters
    ###########################################################################
    ###########################################################################
    def set_dark_satellite(self):

        dark_satellite = Orbital(
                                    self.satellite,
                                    tle_file=self.tle_file_location
                                )

        return dark_satellite
    ###########################################################################
    def set_observer(self):

        observer = ephem.Observer()
        observer.epoch = "2000"
        observer.pressure = 1010
        observer.temp = 15
        observatory_latitude = self.observatory_data["latitude"] # degrees
        observer.lat = np.radians(observatory_latitude)
        #######################################################################
        observatory_longitude = self.observatory_data["longitude"] # degrees
        observer.lon = np.radians(observatory_longitude)
        #######################################################################
        # observatory_altitude = self.observatory_data["altitude"] / 1000.0  # in km
        observer.elevation = self.observatory_data["altitude"]  # in meters
        # observatory_time_zone = observatory_data["tz"]
        self.observer = observer

        return self.observer
    ###########################################################################
    def _set_observatory_data(self, data_observatory: "dictionary"):
        """
        Transform data from observatories.txt file at home.
        Degrees are positive to the east and negative to the west

        PARAMETERS
            observatory_data: contains parameters of observatory
            {
                'name': 'European Southern Observatory, La Silla',
                'longitude': [70, 43.8], # entries for [deg, ', ']
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
        for parameter_observatory, parameters_values in data_observatory.items():

            if type(parameters_values) == list:
                sign = 1 # negative to the west and positive to the east
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

                    update_format[parameter_observatory] += parameter / (60 ** idx)
                ###############################################################
                update_format[parameter_observatory] = sign * update_format[parameter_observatory]

            else:
                update_format[parameter_observatory] = parameters_values

            if parameter_observatory == "longitude":

                if update_format[parameter_observatory] > 180.0:
                    update_format[parameter_observatory] = 360 - update_format[parameter_observatory]

                else:
                    update_format[parameter_observatory] = -update_format[parameter_observatory]

        return update_format
    ###########################################################################
    def update_observer(self):
        # observer.date = ephem.date(date_time)
        # ra, dec = observer.radec_of(
        #     np.radians(satellite_azimuth), np.radians(satellite_altitude)
        # )
        pass
    ###########################################################################
    def set_window(self)-> "list":
        """
        Set day and  hour of observation according to time zone

        OUTPUTS

            [hour: "int", day: "int"]:
                set according to time window and time zone

                hour:
                day:
        """

        window = self.time_parameters["window"]
        day = self.time_parameters["day"]
        observatory_time_zone = self.observatory_data["tz"]

        if (window == "morning") and (observatory_time_zone < 0):

            day -= 1

        hour = self._set_hour(window,observatory_time_zone)

        return [hour, day]
    ###########################################################################
    def _set_hour(self, window: "str",observatory_time_zone: "int")-> "int":

        if window == "evening":

            hour = 12 + observatory_time_zone

        elif window == "morning":

            hour = 0 + observatory_time_zone

        if hour >= 24:
            hour -= 24

        elif hour < 0:
            hour += 24

        return hour
    ###########################################################################

###############################################################################
def compute_visible(
    satellite: "str",
    window: "str",
    observatory_data: "dict",
    tle_file: "str",
    year: "int",
    month: "int",
    day: "int",
    seconds_delta: "int",
    satellite_altitude_lower_bound: "float",
    sun_zenith_lower: "float",
    sun_zenith_upper: "float",
) -> "list":

    """
    Computes when a satellite is visible

    PARAMETERS

        satellite: satellite type, e.g, oneweb or starlink
        window: time frame for obsevation, e.g, evening
        observatory_data:
        tle_file: name of tle file to use for computations
        year: year of the observation
        month: month of the observation
        day: day of the observation
        seconds_delta: time step to update satellite's dynamics
        satellite_altitude_lower_bound:
        sun_zenith_lower:
        sun_zenith_upper:

    OUTPUT

    """
    convert = ConvertUnits()
    ############################################################################
    # observer = ephem.Observer()
    # observer.epoch = "2000"
    # observer.pressure = 1010
    # observer.temp = 15
    ################################################################
    observatory_latitude = observatory_data["latitude"]
    # observer.lat = np.radians(observatory_latitude)
    ################################################################
    observatory_longitude = observatory_data["longitude"]
    # observer.lon = np.radians(observatory_longitude)
    ################################################################
    observatory_altitude = observatory_data["altitude"] / 1000.0  # in km
    # observer.elevation = observatory_data["altitude"]  # in meters
    ################################################################
    observatory_time_zone = observatory_data["tz"]
    ############################################################################
    # darksat = Orbital(satellite, tle_file=f"{tle_file}")
    ############################################################################
    time_parameters = {
        "year": year, "month": month, "day": day,
        "delta": 60, "window": window}
    test_observatory = {'name': 'European Southern Observatory, La Silla',
        'longitude': [70, 43.8],
        'latitude': [-29, 15.4],
        'altitude': 2347.0,
        'tz': 4}
    compute_class = Compute(
        satellite,
        time_parameters,
        test_observatory,
        tle_file,
        )

    # [hour, day] = compute_class.set_window()
    darksat = compute_class.set_dark_satellite()
    observer = compute_class.set_observer()
    ############################################################################
    # if time_delta = 60, then it will move minute by minute
    # time_delta = datetime.timedelta(seconds=seconds_delta)
    # date_time = datetime.datetime(year, month, day, hour, minute=0, second=0)
    [time_delta, date_time] = compute_class.compute_visibility_of_satellite()
    ############################################################################
    satellite_azimuth0 = 0
    satellite_altitude0 = 0
    ############################################################################
    write = []
    ############################################################################
    number_iterations = (12 * 60 * 60) / seconds_delta
    number_iterations = range(int(number_iterations))

    print(f"Compute visibility of: {satellite}", end="\r")
    # Add precentage :)
    for time_step in number_iterations:
        ####################################################################
        # computes the current latitude, longitude of the satellite's
        # footprint and its current orbital altitude
        try:
            darksat_latitude_logitude = darksat.get_lonlatalt(date_time)
        except:
            return None
        ####################################################################
        # uses the observer coordinates to compute the satellite azimuth
        # and elevation, negative elevation implies satellite is under
        # the horizon
        satellite_azimuth, satellite_altitude = darksat.get_observer_look(
            date_time,
            observatory_longitude,
            observatory_latitude,
            observatory_altitude,
        )
        ####################################################################
        # gets the Sun's RA and DEC at the time of observation
        sun_ra, sun_dec = pyorbital.astronomy.sun_ra_dec(date_time)

        sun_RA = convert.RA_in_radians_to_hours(RA=sun_ra)
        sun_DEC = convert.radians_to_degrees(radians=sun_dec)
        ####################################################################
        sun_zenith_angle = pyorbital.astronomy.sun_zenith_angle(
            date_time, observatory_longitude, observatory_latitude
        )
        ####################################################################
        observer.date = ephem.date(date_time)
        ra, dec = observer.radec_of(
            np.radians(satellite_azimuth), np.radians(satellite_altitude)
        )
        #######################################################################
        [
            ra_satellite_h,
            ra_satellite_m,
            ra_satellite_s
        ]= convert.RA_in_radians_to_hh_mm_ss(RA=ra)

        [
            dec_satellite_d,
            dec_satellite_m,
            dec_satellite_s
        ]= convert.DEC_in_radians_to_dd_mm_ss(DEC=dec)
        #######################################################################
        visible = (satellite_altitude > satellite_altitude_lower_bound) and (
            sun_zenith_lower < sun_zenith_angle < sun_zenith_upper
        )

        if visible:
            ################################################################
            # compute the change in AZ and ALT of the satellite position
            # between current and previous observation
            ## difference in azimuth arcsecs
            delta_azimuth = (satellite_azimuth - satellite_azimuth0) * 3600
            ## difference in altitude in arcsecs
            delta_altitude = (satellite_altitude - satellite_altitude0) * 3600
            ####################################################################
            dt = time_delta.total_seconds()
            angular_velocity = (
                np.sqrt(delta_azimuth ** 2 + delta_altitude ** 2) / dt
            )

            data_str, data_str_simple = format.data_formating(
                date_time,
                darksat_latitude_logitude,
                satellite_azimuth,
                satellite_altitude,
                ra_satellite_h,
                ra_satellite_m,
                ra_satellite_s,
                dec_satellite_d,
                dec_satellite_m,
                dec_satellite_s,
                sun_RA,
                sun_DEC,
                sun_zenith_angle,
                angular_velocity,
            )
            ####################################################################
            write.append([data_str, data_str_simple])
        ########################################################################
        # current position, time as the "previous" for next observation
        satellite_azimuth0 = satellite_azimuth
        satellite_altitude0 = satellite_altitude
        date_time += time_delta
    ############################################################################
    if len(write) > 0:
        return [[satellite] + data for data in write]

################################################################################
