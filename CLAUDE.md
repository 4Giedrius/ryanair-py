# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python library for interacting with the Ryanair API to search for flights. The project also includes extended functionality for multi-airline flight searches across Ryanair and AirBaltic with specialized weekend flight discovery tools.

## Key Commands

### Testing
- Run tests: `pytest` or `python -m pytest tests/`
- Run specific test: `pytest tests/test_ryanair.py::TestRyanair::test_get_cheapest_flights`
- Run with coverage: `pytest --cov=ryanair tests/`

### Development
- Install dependencies: `pip install -r requirements.txt`
- Install development dependencies: `pip install -r requirements.dev.txt`
- Code formatting: `black .` (formats all Python files)
- Install package in development mode: `pip install -e .`

### Package Management
- Build package: `python setup.py sdist bdist_wheel`
- Install from local: `pip install .`

## Architecture Overview

### Core Library Structure (`ryanair/`)
- **`ryanair.py`**: Main API client with `Ryanair` class containing flight search methods
- **`types.py`**: Data classes for `Flight` and `Trip` objects using dataclasses
- **`SessionManager.py`**: Handles HTTP session management and cookie handling for API requests
- **`airport_utils.py`**: Utilities for airport code handling and validation
- **`airports.csv`**: Static data file with airport information

### Key Design Patterns
- **Session Management**: Uses requests.Session with automatic cookie handling via SessionManager
- **Retry Logic**: Implements exponential backoff retry pattern with `@backoff.on_exception` decorator
- **Data Transfer Objects**: Uses dataclasses for Flight and Trip objects for type safety
- **Currency Handling**: Supports multiple currencies with warnings when API returns different currency than requested
- **Error Handling**: Comprehensive exception handling with logging and custom `RyanairException`

### Extended Flight Search Tools
- **`weekend_flight_search.py`**: Multi-airline weekend flight finder with SQLite caching
- **`airbaltic_weekendsearch.py`**: AirBaltic-specific weekend search functionality
- **`ryanair_weekendsearch.py`**: Ryanair-specific weekend search functionality

### Flight Search Architecture
The weekend flight search implements an adapter pattern:
- **`AirlineAPI`**: Base class defining common interface
- **`RyanairAPI`** and **`AirBalticAPI`**: Concrete adapters for each airline
- **Parallel Processing**: Uses ThreadPoolExecutor for concurrent API requests
- **Result Caching**: SQLite database for caching flight search results
- **Mixed Trip Logic**: Combines flights from different airlines for outbound/return

### Key Methods
- **`get_cheapest_flights()`**: One-way flight search
- **`get_cheapest_return_flights()`**: Round-trip flight search
- **`get_airports_by_country()`**: Static method returning airport codes by country
- **`search_weekend_flights()`**: Main weekend search function with date range iteration

### Testing Patterns
- Uses unittest framework with extensive mocking of HTTP requests
- Mock responses defined as module-level constants (`MOCKED_ONE_WAY_RESPONSE`, `MOCKED_RETURN_RESPONSE`)
- Tests cover success cases, error handling, retry logic, and parameter validation
- Session management is mocked using `@patch` decorators

### Weekend Logic Testing
- **`test_weekend_logic.py`**: Comprehensive test suite for weekend optimization logic
- Tests weekday counting logic for various departure/return scenarios
- Validates perfect weekend detection (Friday evening → Sunday returns = 0 weekdays)
- Tests ratio calculations including edge cases (infinite ratios for perfect weekends)
- Covers boundary conditions (17:00 departures, 09:00 returns)
- Tests holiday exclusion and optimal long weekend detection
- Run tests: `python test_weekend_logic.py`

## Important Notes

### API Integration
- **No API Key Required**: Uses Ryanair's public API endpoints
- **Rate Limiting**: Implements delays and retry logic to avoid overwhelming APIs
- **Session Cookies**: Requires session cookies from main Ryanair website for API access

### Data Handling
- **Date Formats**: Supports string (YYYY-MM-DD), datetime, and date objects
- **Time Formats**: Supports string (HH:MM) and time objects
- **Currency**: Defaults to EUR but supports other currencies with API limitations

### Weekend Search Features
- **Weekday Calculation**: Excludes public holidays and calculates vacation efficiency ratios
- **Date Range Logic**: Thursday/Friday departures with Sunday/Monday/Tuesday returns
- **Multi-airline Support**: Can search and combine flights from different airlines
- **Result Ranking**: Sorts by price and vacation efficiency (days off vs. weekdays used)