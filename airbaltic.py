"""
This module allows you to retrieve flight information from AirBaltic's API.
It provides functionality to check available destinations and flight prices.
"""
import logging
import json
import requests
from datetime import datetime, date
from typing import Union, Optional, List, Dict, Any

logger = logging.getLogger("airbaltic")
if not logger.handlers:
    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)s:%(message)s", datefmt="%Y-%m-%d %I:%M:%S"
    )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


class AirBalticException(Exception):
    def __init__(self, message):
        super().__init__(f"AirBaltic API: {message}")


class AirBaltic:
    """
    Class for interacting with the AirBaltic API to retrieve flight information.
    """
    BASE_API_URL = "https://api.airbaltic.com/schedule/any"

    def __init__(self, currency: Optional[str] = "EUR"):
        """
        Initialize the AirBaltic API client.
        
        Args:
            currency (str, optional): Currency for prices. Defaults to "EUR".
        """
        self.currency = currency
        self.session = requests.Session()
        self._num_queries = 0

    def get_available_destinations(
        self, 
        origin: str, 
        departure_date: Union[str, datetime, date], 
        return_date: Union[str, datetime, date]
    ) -> List[str]:
        """
        Get available destinations from a specific origin on given dates.
        
        Args:
            origin (str): Origin airport code (e.g., 'VNO')
            departure_date (Union[str, datetime, date]): Departure date
            return_date (Union[str, datetime, date]): Return date
            
        Returns:
            List[str]: List of available destination airport codes
        """
        departure_date_str = self._format_date(departure_date)
        return_date_str = self._format_date(return_date)
        
        url = f"{self.BASE_API_URL}/simple/{origin}/{departure_date_str}/{return_date_str}"
        params = {
            "origin": origin,
            "departureDate": departure_date_str,
            "returnDate": return_date_str
        }
        
        try:
            self._num_queries += 1
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching available destinations: {e}")
            raise AirBalticException(f"Failed to fetch available destinations: {e}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from AirBaltic API")
            raise AirBalticException("Invalid JSON response from API")

    def get_flight_price(
        self, 
        origin: str, 
        destination: str, 
        departure_date: Union[str, datetime, date], 
        return_date: Union[str, datetime, date]
    ) -> Dict[str, float]:
        """
        Get flight price for a specific route and dates.
        
        Args:
            origin (str): Origin airport code (e.g., 'VNO')
            destination (str): Destination airport code (e.g., 'RIX')
            departure_date (Union[str, datetime, date]): Departure date
            return_date (Union[str, datetime, date]): Return date
            
        Returns:
            Dict[str, float]: Dictionary with destination code as key and price as value
        """
        departure_date_str = self._format_date(departure_date)
        return_date_str = self._format_date(return_date)
        
        url = f"{self.BASE_API_URL}/prices/{origin}/{destination}/{departure_date_str}/{return_date_str}"
        
        try:
            self._num_queries += 1
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching flight price: {e}")
            raise AirBalticException(f"Failed to fetch flight price: {e}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from AirBaltic API")
            raise AirBalticException("Invalid JSON response from API")

    def search_flights(
        self, 
        origin: str, 
        departure_date: Union[str, datetime, date], 
        return_date: Union[str, datetime, date],
        max_price: Optional[float] = None,
        destinations: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for flights from an origin to multiple destinations.
        
        Args:
            origin (str): Origin airport code (e.g., 'VNO')
            departure_date (Union[str, datetime, date]): Departure date
            return_date (Union[str, datetime, date]): Return date
            max_price (Optional[float]): Maximum price filter
            destinations (Optional[List[str]]): List of destination codes to check
                                               (if None, checks all available destinations)
            
        Returns:
            List[Dict[str, Any]]: List of flight information dictionaries
        """
        # First get available destinations if not specified
        if not destinations:
            destinations = self.get_available_destinations(origin, departure_date, return_date)
        
        results = []
        
        # Check price for each destination
        for destination in destinations:
            try:
                price_data = self.get_flight_price(origin, destination, departure_date, return_date)
                
                # Extract price for the destination
                if destination in price_data:
                    price = price_data[destination]
                    
                    # Apply price filter if specified
                    if max_price is None or price <= max_price:
                        results.append({
                            "origin": origin,
                            "destination": destination,
                            "departure_date": self._format_date(departure_date),
                            "return_date": self._format_date(return_date),
                            "price": price,
                            "currency": self.currency
                        })
            except AirBalticException as e:
                logger.warning(f"Could not get price for {destination}: {e}")
                continue
                
        # Sort results by price
        results.sort(key=lambda x: x["price"])
        return results

    @staticmethod
    def _format_date(d: Union[str, datetime, date]) -> str:
        """
        Format date for API requests.
        
        Args:
            d (Union[str, datetime, date]): Date to format
            
        Returns:
            str: Formatted date string (YYYY-MM-DD)
        """
        if isinstance(d, str):
            return d
        elif isinstance(d, datetime):
            return d.date().isoformat()
        elif isinstance(d, date):
            return d.isoformat()
        else:
            raise ValueError(f"Unsupported date format: {type(d)}")

    @property
    def num_queries(self) -> int:
        """
        Get the number of API queries made.
        
        Returns:
            int: Number of queries
        """
        return self._num_queries


# Example usage
if __name__ == "__main__":
    api = AirBaltic()
    
    # Example: Get available destinations from VNO
    destinations = api.get_available_destinations("VNO", "2025-06-20", "2025-06-24")
    print(f"Available destinations from VNO: {destinations}")
    
    # Example: Get price for VNO to RIX
    price = api.get_flight_price("VNO", "RIX", "2025-06-20", "2025-06-24")
    print(f"Price for VNO to RIX: {price}")
    
    # Example: Search for flights
    flights = api.search_flights("VNO", "2025-06-20", "2025-06-24", max_price=150)
    for flight in flights:
        print(f"{flight['origin']} to {flight['destination']}: {flight['price']} {flight['currency']}") 