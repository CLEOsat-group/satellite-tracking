"""Compute visibility of LEO sats according to observation constraints"""
import datetime
import sys

import numpy as np
import pyorbital

from leosTrack import output
from leosTrack.track.visible import ComputeVisibility, CONVERT


class FixWindow(ComputeVisibility):
    """Class to compute whether a satellite is visible or not"""

    def __init__(
        self,
        time_parameters: dict,
        observatory_data: dict,
        observation_constraints: dict,
        tle_file_location: dict,
    ):
        # init parent class
        ComputeVisibility.__init__(
            self,
            time_parameters,
            observatory_data,
            observation_constraints,
            tle_file_location,
        )

    def compute_visibility_of_satellite(self, satellite_name: str) -> list:
        """
        PARAMETERS
            satellite: name of a satellite, eg, "ONEWEB-0008"

        OUTPUT
            list with visible satellites data ?
        """

        ######################################################################
        # I have to set the observer per satelitte inside this function,
        # otherwise with mp.pool the line:
        # observer = ephem.Observer()
        # cannot be serialized avoiding the parallel computation.
        # Therefore in parallel the observer will be set over and over
        self._set_observer()
        satellite = self._set_dark_satellite(satellite_name)

        start_date_time, finish_date_time = self.get_date_time_object(
            time_parameters=self.time_parameters,
            time_zone=self.observatory_data["tz"],
        )

        date_time = start_date_time

        observation_window_seconds = (
            finish_date_time - start_date_time
        ).total_seconds()

        number_of_time_steps = int(
            observation_window_seconds / self.time_delta.total_seconds()
        )
        #######################################################################
        previous_satellite_azimuth = 0
        previous_satellite_altitude = 0
        #######################################################################
        visible_satellite_data = []
        #######################################################################
        print(f"Compute visibility of: {satellite_name}", end="\r")

        for _ in range(number_of_time_steps):
            # compute current latitude, longitude of the satellite's
            # footprint and its current orbital altitude
            # satellite_lon_lat_alt = satellite.get_lonlatalt(date_time)
            # Check with jeremy what was the error that motivated this block
            try:
                satellite_lon_lat_alt = satellite.get_lonlatalt(date_time)
            except:
                return None
            ###################################################################
            # uses the observer coordinates to compute the satellite azimuth
            # and elevation, negative elevation implies satellite is under
            # the horizon. altitude must be in kilometers
            [
                satellite_azimuth,
                satellite_altitude,
            ] = satellite.get_observer_look(
                date_time,
                self.observatory_data["longitude"],
                self.observatory_data["latitude"],
                self.observatory_data["altitude"] / 1000.,
            )
            ###################################################################
            # gets the Sun's RA and DEC at the time of observation
            [
                sun_right_ascension, sun_declination
            ] = pyorbital.astronomy.sun_ra_dec(date_time)

            sun_right_ascension = CONVERT.right_ascension_in_radians_to_hours(
                right_ascension=sun_right_ascension
            )
            sun_declination = np.rad2deg(sun_declination)
            ###################################################################
            self._update_observer_date(date_time)

            [
                [ra_satellite_h, ra_satellite_m, ra_satellite_s],
                [dec_satellite_d, dec_satellite_m, dec_satellite_s],
            ] = self.get_satellite_ra_dec_from_azimuth_and_altitude(
                satellite_azimuth, satellite_altitude
            )
            ###################################################################
            lowest_altitude_satellite = self.constraints[
                "lowest_altitude_satellite"
            ]
            ###################################################################
            sun_zenith_angle = pyorbital.astronomy.sun_zenith_angle(
                date_time, self.observatory_data["longitude"], self.observatory_data["latitude"]
            )

            sun_zenith_highest = self.constraints["sun_zenith_highest"]
            sun_zenith_lowest = self.constraints["sun_zenith_lowest"]
            ###################################################################

            check_altitude = satellite_altitude > lowest_altitude_satellite
            check_sun_zenith = sun_zenith_lowest < sun_zenith_angle
            check_sun_zenith *= sun_zenith_angle < sun_zenith_highest
            # Add bool() to avoid having np.bool_ type. This way, I can have
            # if satellite_is_visible is True:
            satellite_visibility = bool(check_altitude and check_sun_zenith)

            if satellite_visibility is True:
                print(f"{satellite_name} is visible", end="\r")
                ###############################################################
                # compute the change in AZ and ALT of the satellite position
                # between current and previous observation
                # difference in azimuth arcsecs
                delta_azimuth = (
                    satellite_azimuth - previous_satellite_azimuth
                ) * 3600
                # difference in altitude in arcsecs
                delta_altitude = (
                    satellite_altitude - previous_satellite_altitude
                ) * 3600
                ###############################################################
                dtime = self.time_delta.total_seconds()
                angular_velocity = (
                    np.sqrt(delta_azimuth ** 2 + delta_altitude ** 2) / dtime
                )

                data_str, data_str_simple = output.data_formating(
                    date_time,
                    satellite_lon_lat_alt,
                    satellite_azimuth,
                    satellite_altitude,
                    ra_satellite_h,
                    ra_satellite_m,
                    ra_satellite_s,
                    dec_satellite_d,
                    dec_satellite_m,
                    dec_satellite_s,
                    sun_right_ascension,
                    sun_declination,
                    sun_zenith_angle,
                    angular_velocity,
                )
                ##############################################################
                visible_satellite_data.append([data_str, data_str_simple])
            ###################################################################
            # current position, time as the "previous" for next observation
            previous_satellite_azimuth = satellite_azimuth
            previous_satellite_altitude = satellite_altitude
            date_time += self.time_delta
        #######################################################################
        if len(visible_satellite_data) > 0:
            return [[satellite_name] + data for data in visible_satellite_data]

    @staticmethod
    def get_date_time_object(time_parameters: dict, time_zone: int) -> list:
        """
        INPUT
            time_parameters: check constructor
            tz: time zone of the observatory location
            constant_window: wheather the user defines a time window or if it
                is the "evening" or "morning" 12 hours slot
        OUTPUTS
            [
                start_date_time: datetime.datetime,
                finish_date_time: datetime.datetime
            ]
        """
        # define local time
        if time_parameters["window"] == "morning":
            hour = 0
        elif time_parameters["window"] == "evening":
            hour = 12
        else:
            print(f"window must be: 'morning' or 'evening'")
            sys.exit()

        start_date_time = datetime.datetime(
            year=time_parameters["year"],
            month=time_parameters["month"],
            day=time_parameters["day"],
            hour=hour,
            minute=0,
            second=0,
        )

        # convert to UTC
        start_date_time += time_zone

        finish_date_time = start_date_time + datetime.timedelta(hours=12)

        return start_date_time, finish_date_time
