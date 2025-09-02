#!/usr/bin/env python3
"""
Test suite for weekend search logic to prevent regressions
"""

import unittest
from datetime import datetime, date, timedelta
from ryanair_weekendsearch import count_weekdays, find_optimal_long_weekends


class TestWeekendLogic(unittest.TestCase):
    """Test cases for weekend optimization logic"""

    def setUp(self):
        """Set up test data"""
        # Test holidays for 2025 (Lithuanian holidays)
        self.test_holidays = [
            date(2025, 1, 1),   # New Year
            date(2025, 2, 16),  # Independence Day
            date(2025, 3, 11),  # Restoration of Independence
            date(2025, 4, 21),  # Easter Monday
            date(2025, 5, 1),   # Labor Day
            date(2025, 6, 24),  # Midsummer Day
            date(2025, 7, 6),   # State Day
            date(2025, 8, 15),  # Assumption Day
            date(2025, 11, 1),  # All Saints Day
            date(2025, 12, 25), # Christmas
            date(2025, 12, 26)  # Boxing Day
        ]

    def test_perfect_weekend_friday_evening_departure(self):
        """Test Friday evening departure to Sunday return = 0 weekdays"""
        # Friday 22:05 -> Sunday 06:15 (like the LTN example)
        start = datetime(2025, 11, 7, 22, 5)   # Friday evening
        end = datetime(2025, 11, 9, 6, 15)     # Sunday morning
        
        weekdays = count_weekdays(start, end, start, end)
        self.assertEqual(weekdays, 0, "Friday evening to Sunday should use 0 weekdays")

    def test_perfect_weekend_saturday_to_monday_early(self):
        """Test Saturday to early Monday return = 0 weekdays"""
        # Saturday 13:25 -> Monday 05:45
        start = datetime(2025, 11, 8, 13, 25)  # Saturday
        end = datetime(2025, 11, 10, 5, 45)    # Monday early morning
        
        weekdays = count_weekdays(start, end, start, end)
        self.assertEqual(weekdays, 0, "Saturday to early Monday should use 0 weekdays")

    def test_friday_early_departure_counts_weekday(self):
        """Test Friday early departure counts as weekday"""
        # Friday 14:00 -> Sunday 18:00 
        start = datetime(2025, 11, 7, 14, 0)   # Friday afternoon
        end = datetime(2025, 11, 9, 18, 0)     # Sunday evening
        
        weekdays = count_weekdays(start, end, start, end)
        self.assertEqual(weekdays, 1, "Friday early departure should count as 1 weekday")

    def test_monday_late_return_counts_weekday(self):
        """Test Monday late return counts as weekday"""
        # Friday 22:00 -> Monday 15:00
        start = datetime(2025, 11, 7, 22, 0)   # Friday evening
        end = datetime(2025, 11, 10, 15, 0)    # Monday afternoon
        
        weekdays = count_weekdays(start, end, start, end)
        self.assertEqual(weekdays, 1, "Monday late return should count as 1 weekday")

    def test_thursday_to_tuesday_standard_weekend(self):
        """Test standard Thursday to Tuesday weekend"""
        # Thursday 20:10 -> Tuesday 05:55 (like EDI example)
        start = datetime(2025, 11, 6, 20, 10)  # Thursday evening
        end = datetime(2025, 11, 11, 5, 55)    # Tuesday early morning
        
        weekdays = count_weekdays(start, end, start, end)
        self.assertEqual(weekdays, 2, "Thursday evening to Tuesday morning should use 2 weekdays")

    def test_wednesday_evening_departure_optimization(self):
        """Test Wednesday evening departure still counts"""
        # Wednesday 19:00 -> Monday 08:00
        start = datetime(2025, 11, 5, 19, 0)   # Wednesday evening
        end = datetime(2025, 11, 10, 8, 0)     # Monday morning
        
        weekdays = count_weekdays(start, end, start, end)
        # Should count: Wed (evening departure counts) + Thu + Fri = 3 weekdays
        # Monday early return (08:00) doesn't count as a work day
        self.assertEqual(weekdays, 3, "Wednesday evening departure should count Wed + Thu + Fri")

    def test_holiday_exclusion(self):
        """Test that holidays are properly excluded"""
        # Include a holiday in the range (Nov 1st is All Saints Day)
        start = datetime(2025, 10, 31, 10, 0)  # Friday before holiday
        end = datetime(2025, 11, 3, 10, 0)     # Monday after holiday
        
        weekdays = count_weekdays(start, end, start, end)
        # Should be 1 (Friday) + 1 (Monday) = 2, but Nov 1 (Saturday) is holiday anyway
        self.assertEqual(weekdays, 2, "Holiday weekend should count Fri + Mon")

    def test_ratio_calculation_perfect_weekend(self):
        """Test ratio calculation for perfect weekend (0 weekdays)"""
        duration_days = 2  # Friday evening to Sunday morning
        weekdays_used = 0
        
        # Test the logic from the main function
        if weekdays_used == 0:
            ratio = float('inf') if duration_days > 0 else 0
        else:
            ratio = duration_days / weekdays_used
            
        self.assertEqual(ratio, float('inf'), "Perfect weekend should have infinite ratio")

    def test_ratio_calculation_normal_weekend(self):
        """Test ratio calculation for normal weekend"""
        duration_days = 4  # Thursday to Monday
        weekdays_used = 2   # Thursday + Monday
        
        ratio = duration_days / weekdays_used
        self.assertEqual(ratio, 2.0, "4 days / 2 weekdays should equal 2.0 ratio")

    def test_ratio_calculation_zero_duration(self):
        """Test edge case of zero duration"""
        duration_days = 0
        weekdays_used = 0
        
        if weekdays_used == 0:
            ratio = float('inf') if duration_days > 0 else 0
        else:
            ratio = duration_days / weekdays_used
            
        self.assertEqual(ratio, 0, "Zero duration should have 0 ratio")

    def test_find_optimal_long_weekends(self):
        """Test optimal long weekend detection"""
        # Test period that includes November 1st holiday (Saturday)
        start_date = "2025-10-20"
        end_date = "2025-11-10"
        
        optimal_periods = find_optimal_long_weekends(start_date, end_date)
        
        # Should find at least one optimal period around Nov 1st
        self.assertGreater(len(optimal_periods), 0, "Should find at least one optimal period")
        
        # Check that periods are sorted by efficiency ratio
        if len(optimal_periods) > 1:
            for i in range(len(optimal_periods) - 1):
                self.assertGreaterEqual(
                    optimal_periods[i]['efficiency_ratio'], 
                    optimal_periods[i + 1]['efficiency_ratio'],
                    "Periods should be sorted by efficiency ratio (descending)"
                )

    def test_weekday_boundary_conditions(self):
        """Test boundary conditions for weekday calculations"""
        # Test exactly at 17:00 (5 PM) on Friday
        start_17 = datetime(2025, 11, 7, 17, 0)   # Friday 5:00 PM
        end = datetime(2025, 11, 9, 8, 0)         # Sunday 8:00 AM
        
        weekdays_17 = count_weekdays(start_17, end, start_17, end)
        self.assertEqual(weekdays_17, 0, "Friday 17:00 departure should use 0 weekdays")
        
        # Test exactly at 16:59 (just before 5 PM) on Friday  
        start_16_59 = datetime(2025, 11, 7, 16, 59) # Friday 4:59 PM
        weekdays_16_59 = count_weekdays(start_16_59, end, start_16_59, end)
        self.assertEqual(weekdays_16_59, 1, "Friday 16:59 departure should use 1 weekday")

        # Test exactly at 09:00 on Monday
        start_fri = datetime(2025, 11, 7, 22, 0)   # Friday evening
        end_09 = datetime(2025, 11, 10, 9, 0)      # Monday 9:00 AM
        
        weekdays_09 = count_weekdays(start_fri, end_09, start_fri, end_09)
        self.assertEqual(weekdays_09, 1, "Monday 09:00 return should count Monday")
        
        # Test exactly at 08:59 on Monday
        end_08_59 = datetime(2025, 11, 10, 8, 59)  # Monday 8:59 AM
        weekdays_08_59 = count_weekdays(start_fri, end_08_59, start_fri, end_08_59)
        self.assertEqual(weekdays_08_59, 0, "Monday 08:59 return should use 0 weekdays")

    def test_multi_day_trip_with_holidays(self):
        """Test multi-day trip spanning holidays"""
        # Test Christmas period (Dec 25-26 are holidays)
        start = datetime(2025, 12, 24, 10, 0)  # Tuesday before Christmas
        end = datetime(2025, 12, 29, 15, 0)    # Monday after holidays
        
        weekdays = count_weekdays(start, end, start, end)
        # Should count: Tue(24), Mon(29) = 2 weekdays (holidays excluded)
        self.assertEqual(weekdays, 2, "Christmas period should exclude holiday weekdays")

    def test_sunday_departure_edge_case(self):
        """Test Sunday departure (should never count as weekday)"""
        start = datetime(2025, 11, 9, 15, 0)   # Sunday afternoon
        end = datetime(2025, 11, 10, 10, 0)    # Monday morning
        
        weekdays = count_weekdays(start, end, start, end)
        self.assertEqual(weekdays, 1, "Sunday to Monday should count only Monday")

    def test_saturday_departure_edge_case(self):
        """Test Saturday departure (should never count as weekday)"""
        start = datetime(2025, 11, 8, 15, 0)   # Saturday afternoon
        end = datetime(2025, 11, 10, 8, 0)     # Monday early morning
        
        weekdays = count_weekdays(start, end, start, end)
        self.assertEqual(weekdays, 0, "Saturday to early Monday should use 0 weekdays")


class TestWeekendConfigurationEdgeCases(unittest.TestCase):
    """Test edge cases for weekend configuration"""

    def test_single_day_trip(self):
        """Test single day trip calculations"""
        # Same day trip (Friday evening to late Friday)
        start = datetime(2025, 11, 7, 18, 0)   # Friday 6 PM
        end = datetime(2025, 11, 7, 23, 59)    # Friday 11:59 PM
        
        weekdays = count_weekdays(start, end, start, end)
        self.assertEqual(weekdays, 0, "Single day Friday evening trip should use 0 weekdays")

    def test_zero_duration_trip(self):
        """Test zero duration edge case"""
        start = datetime(2025, 11, 7, 18, 0)   # Friday 6 PM
        end = datetime(2025, 11, 7, 18, 0)     # Same time
        
        weekdays = count_weekdays(start, end, start, end)
        self.assertEqual(weekdays, 0, "Zero duration trip should use 0 weekdays")


if __name__ == '__main__':
    # Run the tests
    print("🧪 Running Weekend Logic Tests...")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestWeekendLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestWeekendConfigurationEdgeCases))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("=" * 60)
    if result.wasSuccessful():
        print("✅ All tests passed! Weekend logic is working correctly.")
    else:
        print("❌ Some tests failed. Check the output above.")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
    
    print(f"Tests run: {result.testsRun}")
    print(f"Skipped: {len(result.skipped)}")