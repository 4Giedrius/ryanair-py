"""
This module allows you to retrieve the cheapest flights, with or without return flights, within a fixed set of dates.
This is done directly through Ryanair's API, and does not require an API key.
"""
import logging
import sys
from datetime import datetime, date, time
from typing import Union, Optional

import backoff

from ryanair.SessionManager import SessionManager
from ryanair.types import Flight, Trip

logger = logging.getLogger("ryanair")
if not logger.handlers:
    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)s:%(message)s", datefmt="%Y-%m-%d %I:%M:%S"
    )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


class RyanairException(Exception):
    def __init__(self, message):
        super().__init__(f"Ryanair API: {message}")


# noinspection PyBroadException
class Ryanair:
    BASE_SERVICES_API_URL = "https://services-api.ryanair.com/farfnd/v4/"
    BASE_LOCATE_API_URL = "https://www.ryanair.com/api/locate/v1/"


    def __init__(self, currency: Optional[str] = None):
        self.currency = currency

        self._num_queries = 0
        self.session_manager = SessionManager()
        self.session = self.session_manager.get_session()

    def get_cheapest_flights(
        self,
        airport: str,
        date_from: Union[datetime, date, str],
        date_to: Union[datetime, date, str],
        destination_country: Optional[str] = None,
        custom_params: Optional[dict] = None,
        departure_time_from: Union[str, time] = "00:00",
        departure_time_to: Union[str, time] = "23:59",
        max_price: Optional[int] = None,
        destination_airport: Optional[str] = None,
    ):
        query_url = "".join((Ryanair.BASE_SERVICES_API_URL, "oneWayFares"))

        params = {
            "departureAirportIataCode": airport,
            "outboundDepartureDateFrom": self._format_date_for_api(date_from),
            "outboundDepartureDateTo": self._format_date_for_api(date_to),
            "outboundDepartureTimeFrom": self._format_time_for_api(departure_time_from),
            "outboundDepartureTimeTo": self._format_time_for_api(departure_time_to),
        }
        if self.currency:
            params["currency"] = self.currency
        if destination_country:
            params["arrivalCountryCode"] = destination_country
        if max_price:
            params["priceValueTo"] = max_price
        if destination_airport:
            params["arrivalAirportIataCode"] = destination_airport
        if custom_params:
            params.update(custom_params)

        response = self._retryable_query(query_url, params)["fares"]

        if response:
            return [
                self._parse_cheapest_flight(flight["outbound"]) for flight in response
            ]

        return []

    def get_cheapest_return_flights(
        self,
        source_airport: str,
        date_from: Union[datetime, date, str],
        date_to: Union[datetime, date, str],
        return_date_from: Union[datetime, date, str],
        return_date_to: Union[datetime, date, str],
        destination_country: Optional[str] = None,
        custom_params: Optional[dict] = None,
        outbound_departure_time_from: Union[str, time] = "00:00",
        outbound_departure_time_to: Union[str, time] = "23:59",
        inbound_departure_time_from: Union[str, time] = "00:00",
        inbound_departure_time_to: Union[str, time] = "23:59",
        max_price: Optional[int] = None,
        destination_airport: Optional[str] = None,
    ):
        query_url = "".join((Ryanair.BASE_SERVICES_API_URL, "roundTripFares"))

        params = {
            "departureAirportIataCode": source_airport,
            "outboundDepartureDateFrom": self._format_date_for_api(date_from),
            "outboundDepartureDateTo": self._format_date_for_api(date_to),
            "inboundDepartureDateFrom": self._format_date_for_api(return_date_from),
            "inboundDepartureDateTo": self._format_date_for_api(return_date_to),
            "outboundDepartureTimeFrom": self._format_time_for_api(
                outbound_departure_time_from
            ),
            "outboundDepartureTimeTo": self._format_time_for_api(
                outbound_departure_time_to
            ),
            "inboundDepartureTimeFrom": self._format_time_for_api(
                inbound_departure_time_from
            ),
            "inboundDepartureTimeTo": self._format_time_for_api(
                inbound_departure_time_to
            ),
        }
        if self.currency:
            params["currency"] = self.currency
        if destination_country:
            params["arrivalCountryCode"] = destination_country
        if max_price:
            params["priceValueTo"] = max_price
        if destination_airport:
            params["arrivalAirportIataCode"] = destination_airport
        if custom_params:
            params.update(custom_params)

        response = self._retryable_query(query_url, params)["fares"]

        if response:
            return [
                self._parse_cheapest_return_flights_as_trip(
                    trip["outbound"], trip["inbound"]
                )
                for trip in response
            ]
        else:
            return []
    
    @staticmethod
    def get_airports_by_country(country_code: str, exclude_airports: list = None) -> list:
        """
        Returns a list of airport codes for a specific country
        Args:
            country_code (str): Two-letter country code (e.g., 'LT' for Lithuania)
            exclude_airports (list): Optional list of airport codes to exclude from results
        Returns:
            list: List of airport codes in the specified country
        """
        airports_by_country = {
            'AT': ['VIE', 'SZG', 'INN', 'GRZ', 'LNZ', 'KLU'],  # Austria
            'BE': ['BRU', 'CRL', 'OST'],  # Belgium
            'BG': ['SOF', 'BOJ', 'VAR'],  # Bulgaria
            'HR': ['ZAG', 'DBV', 'SPU', 'ZAD', 'PUY', 'RJK'],  # Croatia
            'CY': ['LCA', 'PFO'],  # Cyprus
            'CZ': ['PRG', 'BRQ', 'OSR'],  # Czech Republic
            'DK': ['CPH', 'BLL', 'AAL', 'AAR'],  # Denmark
            'EE': ['TLL'],  # Estonia
            'FI': ['HEL', 'TMP', 'TKU', 'OUL'],  # Finland
            'FR': ['CDG', 'ORY', 'BVA', 'BOD', 'MRS', 'TLS', 'NCE', 'LYS', 'NTE', 'LIL'],  # France
            'DE': ['BER', 'CGN', 'DUS', 'FRA', 'HAM', 'MUC', 'STR', 'HAJ', 'NUE', 'DRS', 'LEJ', 'BRE'],  # Germany
            'GR': ['ATH', 'SKG', 'HER', 'RHO', 'CFU', 'CHQ', 'KLX', 'PVK', 'JMK', 'JTR'],  # Greece
            'HU': ['BUD', 'DEB'],  # Hungary
            'IS': ['KEF'],  # Iceland
            'IE': ['DUB', 'SNN', 'ORK', 'KIR', 'NOC', 'GWY'],  # Ireland
            'IT': ['FCO', 'CIA', 'MXP', 'BGY', 'VCE', 'TSF', 'BLQ', 'PSA', 'NAP', 'PMO', 'CAG', 'CTA', 'SUF', 'BRI', 'PSR', 'AOI', 'RMI', 'TRS', 'VRN', 'GOA', 'TRN'],  # Italy
            'LV': ['RIX'],  # Latvia
            'LT': ['VNO', 'KUN', 'PLQ'],  # Lithuania
            'LU': ['LUX'],  # Luxembourg
            'MT': ['MLA'],  # Malta
            'ME': ['TGD'],  # Montenegro
            'MA': ['RAK', 'FEZ', 'AGA', 'TNG', 'OUD'],  # Morocco
            'NL': ['AMS', 'EIN', 'RTM', 'MST', 'GRQ'],  # Netherlands
            'NO': ['OSL', 'TRF', 'BGO', 'SVG', 'TRD'],  # Norway
            'PL': ['WAW', 'WMI', 'GDN', 'KRK', 'KTW', 'POZ', 'WRO', 'RZE', 'LUZ', 'BZG', 'SZZ', 'LCJ'],  # Poland
            'PT': ['LIS', 'OPO', 'FAO', 'FNC', 'PDL'],  # Portugal
            'RO': ['OTP', 'CLJ', 'IAS', 'TSR', 'CRA', 'SBZ', 'SUJ'],  # Romania
            'SK': ['BTS', 'KSC'],  # Slovakia
            'SI': ['LJU'],  # Slovenia
            'ES': ['MAD', 'BCN', 'AGP', 'ALC', 'PMI', 'IBZ', 'VLC', 'SVQ', 'BIO', 'SCQ', 'SDR', 'VGO', 'OVD', 'LEI', 'GRX', 'REU', 'XRY', 'MJV', 'VLL'],  # Spain
            'SE': ['ARN', 'NYO', 'GOT', 'MMX', 'VST'],  # Sweden
            'CH': ['ZRH', 'BSL', 'GVA'],  # Switzerland
            'GB': ['LHR', 'LGW', 'STN', 'LTN', 'MAN', 'EDI', 'BHX', 'GLA', 'BRS', 'LPL', 'NCL', 'BFS', 'ABZ', 'CWL', 'EXT', 'BOH', 'SOU', 'BHD'],  # United Kingdom (Great Britain)
            'UA': ['KBP', 'LWO'],  # Ukraine
            'IL': ['TLV'],  # Israel
            'JO': ['AMM', 'AQJ'],  # Jordan
            'CY': ['LCA', 'PFO'],  # Cyprus
        }
        
        # Get airports for the country
        airports = airports_by_country.get(country_code.upper(), [])
        
        # If exclude_airports is provided, filter out those airports
        if exclude_airports:
            airports = [airport for airport in airports if airport not in exclude_airports]
        
        return airports

    @staticmethod
    def _get_backoff_type():
        if "unittest" in sys.modules.keys():
            return backoff.constant(interval=0)

        return backoff.expo()

    @staticmethod
    def _on_query_error(e):
        logger.exception(f"Gave up retrying query, last exception was {e}")

    @backoff.on_exception(
        _get_backoff_type,
        Exception,
        max_tries=5,
        logger=logger,
        raise_on_giveup=True,
        on_giveup=_on_query_error,
    )
    def _retryable_query(self, url, params=None):
        self._num_queries += 1
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def _parse_cheapest_flight(self, flight):
        currency = flight["price"]["currencyCode"]
        if self.currency and self.currency != currency:
            logger.warning(
                f"Requested cheapest flights in {self.currency} but API responded with fares in {currency}"
            )
        return Flight(
            origin=flight["departureAirport"]["iataCode"],
            originFull=", ".join(
                (
                    flight["departureAirport"]["name"],
                    flight["departureAirport"]["countryName"],
                )
            ),
            destination=flight["arrivalAirport"]["iataCode"],
            destinationFull=", ".join(
                (
                    flight["arrivalAirport"]["name"],
                    flight["arrivalAirport"]["countryName"],
                )
            ),
            departureTime=datetime.fromisoformat(flight["departureDate"]),
            flightNumber=f"{flight['flightNumber'][:2]} {flight['flightNumber'][2:]}",
            price=flight["price"]["value"],
            currency=currency,
        )

    def _parse_cheapest_return_flights_as_trip(self, outbound, inbound):
        outbound = self._parse_cheapest_flight(outbound)
        inbound = self._parse_cheapest_flight(inbound)

        return Trip(
            outbound=outbound,
            inbound=inbound,
            totalPrice=inbound.price + outbound.price,
        )

    @staticmethod
    def _format_date_for_api(d: Union[datetime, date, str]):
        if isinstance(d, str):
            return d

        if isinstance(d, datetime):
            return d.date().isoformat()

        if isinstance(d, date):
            return d.isoformat()

    @staticmethod
    def _format_time_for_api(t: Union[time, str]):
        if isinstance(t, str):
            return t

        if isinstance(t, time):
            return t.strftime("%H:%M")

    @property
    def num_queries(self) -> __init__:
        return self._num_queries

    def get_airport_info(self, iata_code: str):
        url = f"{Ryanair.BASE_LOCATE_API_URL}autocomplete/airports"
        params = {"phrase": iata_code, "market": "en-gb"}
        try:
            return self._retryable_query(url, params)
        except Exception as e:
            raise RyanairException(f"Failed to fetch airport info: {e}")

    def get_active_airports(self):
        url = "https://www.ryanair.com/api/views/locate/3/airports/en/active"
        try:
            return self._retryable_query(url)
        except Exception as e:
            raise RyanairException(f"Failed to fetch active airports: {e}")
 
    def get_countries(self):
        url = "https://www.ryanair.com/api/views/locate/3/countries/en"
        try:
            return self._retryable_query(url)
        except Exception as e:
            raise RyanairException(f"Failed to fetch countries: {e}")

    def get_available_flight_dates(self, departure_airport: str, arrival_airport: str):
        """
        Fetches available flight dates for one-way fares between two airports.

        Args:
            departure_airport (str): IATA code of the departure airport.
            arrival_airport (str): IATA code of the arrival airport.

        Returns:
            List[str]: A list of available dates in 'YYYY-MM-DD' format.
        """
        url = f"https://www.ryanair.com/api/farfnd/v4/oneWayFares/{departure_airport}/{arrival_airport}/availabilities"
        try:
            available_dates = self._retryable_query(url)
            return available_dates
        except Exception as e:
            raise RyanairException(f"Failed to fetch available flight dates: {e}")

