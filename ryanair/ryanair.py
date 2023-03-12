"""
This module allows you to retrieve either
1) the cheapest flights, with or without return flights, within a fixed set of dates.
or
2) all available flights between two locations, on a given date
This is done directly through Ryanair's API, and does not require an API key.
"""
import logging
from typing import Union

import backoff
import requests
from datetime import datetime, date, time
from time import sleep

from deprecated import deprecated

from ryanair.types import Flight, Trip

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s.%(msecs)03d %(levelname)s:%(message)s', datefmt="%m/%d/%Y %I:%M:%S")


# noinspection PyBroadException
class Ryanair:
    BASE_SERVICES_API_URL = "https://services-api.ryanair.com/farfnd/v4/"
    BASE_AVAILABILITY_API_URL = "https://www.ryanair.com/api/booking/v4/"

    def __init__(self, currency):
        self.currency = currency

        self._num_queries = 0

    @deprecated(version="2.0.0", reason="deprecated in favour of get_cheapest_flights", action="once")
    def get_flights(self, airport, date_from, date_to, destination_country=None):
        return self.get_cheapest_flights(airport, date_from, date_to, destination_country)

    @deprecated(version="2.0.0", reason="deprecated in favour of get_cheapest_return_flights", action="once")
    def get_return_flights(self, source_airport, date_from, date_to,
                           return_date_from, return_date_to,
                           destination_country=None):
        return self.get_cheapest_return_flights(source_airport, date_from, date_to,
                                                return_date_from, return_date_to, destination_country)

    def get_cheapest_flights(self, airport, date_from, date_to, destination_country=None,
                             custom_params=None,
                             departure_time_from: Union[str, time] = "00:00",
                             departure_time_to: Union[str, time] = "23:59",
                             max_price: int = None
                             ):
        query_url = ''.join((Ryanair.BASE_SERVICES_API_URL,
                             "oneWayFares"))

        params = {
            "departureAirportIataCode": airport,
            "outboundDepartureDateFrom": self._format_date_for_api(date_from),
            "outboundDepartureDateTo": self._format_date_for_api(date_to),
            "currency": self.currency,
            "outboundDepartureTimeFrom": self._format_time_for_api(departure_time_from),
            "outboundDepartureTimeTo": self._format_time_for_api(departure_time_to)
        }
        if destination_country:
            params['arrivalCountryCode'] = destination_country
        if max_price:
            params['priceValueTo'] = max_price
        if custom_params:
            params.update(custom_params)

        try:
            response = self._retryable_query(query_url, params)["fares"]
        except Exception:
            logging.exception(f"Failed to parse response when querying {query_url}")
            return []

        if response:
            return [self._parse_cheapest_flight(flight['outbound']) for flight in response]

        return []

    def get_cheapest_return_flights(self, source_airport, date_from, date_to,
                                    return_date_from, return_date_to,
                                    destination_country=None,
                                    custom_params=None,
                                    outbound_departure_time_from: Union[str, time] = "00:00",
                                    outbound_departure_time_to: Union[str, time] = "23:59",
                                    inbound_departure_time_from: Union[str, time] = "00:00",
                                    inbound_departure_time_to: Union[str, time] = "23:59",
                                    max_price: int = None
                                    ):
        query_url = ''.join((Ryanair.BASE_SERVICES_API_URL,
                             "roundTripFares"))

        params = {
            "departureAirportIataCode": source_airport,
            "outboundDepartureDateFrom": self._format_date_for_api(date_from),
            "outboundDepartureDateTo": self._format_date_for_api(date_to),
            "inboundDepartureDateFrom": self._format_date_for_api(return_date_from),
            "inboundDepartureDateTo": self._format_date_for_api(return_date_to),
            "currency": self.currency,
            "outboundDepartureTimeFrom": self._format_time_for_api(outbound_departure_time_from),
            "outboundDepartureTimeTo": self._format_time_for_api(outbound_departure_time_to),
            "inboundDepartureTimeFrom": self._format_time_for_api(inbound_departure_time_from),
            "inboundDepartureTimeTo": self._format_time_for_api(inbound_departure_time_to)
        }
        if destination_country:
            params['arrivalCountryCode'] = destination_country
        if max_price:
            params['priceValueTo'] = max_price
        if custom_params:
            params.update(custom_params)

        try:
            response = self._retryable_query(query_url, params)["fares"]
        except Exception as e:
            logging.exception(f"Failed to parse response when querying {query_url}")
            return []

        if response:
            return [self._parse_cheapest_return_flights_as_trip(trip["outbound"], trip["inbound"])
                    for trip in response]
        else:
            return []

    def get_all_flights(self, origin_airport, date_out, destination,
                        locale="en-ie", origin_is_mac=False, destination_is_mac=False,
                        custom_params=None):
        query_url = ''.join((Ryanair.BASE_AVAILABILITY_API_URL, f"{locale}/availability"))

        params = {
            # Assume single adult ticket only
            "ADT": 1,
            "TEEN": 0,
            "CHD": 0,
            "INF": 0,

            "DateOut": self._format_date_for_api(date_out),
            "DateIn": "",

            "Origin": origin_airport,
            "Destination": destination,
            "OriginIsMac": origin_is_mac,
            "DestinationIsMac": destination_is_mac,

            "IncludeConnectingFlights": False,  # What? You do that?
            "ToUs": "AGREED",

            # Presently unused, but these and others can be set by custom_params

            # "Disc": 0,
            # "promoCode": "",
            # "FlexDaysBeforeOut": 2,
            # "FlexDaysOut": 2,
            # "FlexDaysBeforeIn": 2,
            # "FlexDaysIn": 2,
            # "RoundTrip": false,
        }

        if custom_params:
            params.update(custom_params)

        try:
            response = self._retryable_query(query_url, params)["trips"][0]
            flights = response['dates'][0]['flights']
            if flights:
                return [self._parse_all_flights_availability_result_as_flight(flight,
                                                                              response['originName'],
                                                                              response['destinationName'])
                        for flight in flights]
        except Exception:
            logging.exception(f"Failed to parse response when querying {query_url}")
            return []

    @staticmethod
    def _on_query_error(e):
        logging.exception(f"Gave up retrying query, last exception was {e}")

    @backoff.on_exception(backoff.expo, Exception, max_tries=5, logger=logging.getLogger(), on_giveup=_on_query_error,
                          raise_on_giveup=False)
    def _retryable_query(self, url, params):
        self._num_queries += 1

        return requests.get(url, params=params).json()

    @staticmethod
    def _parse_cheapest_flight(flight):
        return Flight(
            origin=flight['departureAirport']['iataCode'],
            originFull=', '.join((flight['departureAirport']['name'], flight['departureAirport']['countryName'])),
            destination=flight['arrivalAirport']['iataCode'],
            destinationFull=', '.join((flight['arrivalAirport']['name'], flight['arrivalAirport']['countryName'])),
            departureTime=datetime.fromisoformat(flight['departureDate']),
            flightNumber=f"{flight['flightNumber'][:2]} {flight['flightNumber'][2:]}",
            price=flight['price']['value']
        )

    def _parse_cheapest_return_flights_as_trip(self, outbound, inbound):
        outbound = self._parse_cheapest_flight(outbound)
        inbound = self._parse_cheapest_flight(inbound)

        return Trip(
            outbound=outbound,
            inbound=inbound,
            totalPrice=inbound.price + outbound.price
        )

    @staticmethod
    def _parse_all_flights_availability_result_as_flight(response, origin_full, destination_full):
        return Flight(departureTime=datetime.fromisoformat(response['time'][0]),
                      flightNumber=response['flightNumber'],
                      price=response['regularFare']['fares'][0]['amount'] if response['faresLeft'] != 0 else float(
                          'inf'),
                      origin=response['segments'][0]['origin'],
                      originFull=origin_full,
                      destination=response['segments'][0]['destination'],
                      destinationFull=destination_full
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
    def _format_time_for_api(t):
        if isinstance(t, str):
            return t

        if isinstance(t, time):
            return t.strftime("%H:%M")

    @property
    def num_queries(self):
        return self._num_queries
