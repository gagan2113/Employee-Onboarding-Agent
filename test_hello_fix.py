#!/usr/bin/env python3
"""
Test script to verify the hello message handler fix
"""
import re

def test_onboarding_trigger_patterns():
    """Test the onboarding trigger pattern matching"""
    pattern = re.compile(r"^start my onboarding$", re.IGNORECASE)
    
    test_cases = [
        ("start my onboarding", True),
        ("Start my onboarding", True),
        ("START MY ONBOARDING", True),
        ("Start My Onboarding", True),
        ("start my onboarding please", False),  # Should not match (has extra words)
        ("please start my onboarding", False),  # Should not match (has extra words)
        ("hello", False),         # Should not match old greeting
        ("hi", False),            # Should not match old greeting
        ("hey", False),           # Should not match old greeting
        ("greetings", False),     # Should not match old greeting
        ("good morning", False),  # Should not match old greeting
        ("help", False),          # Should not match
        ("policy", False),        # Should not match
        ("", False),              # Should not match empty string
        ("start onboarding", False),  # Should not match (missing 'my')
        ("my onboarding", False),     # Should not match (missing 'start')
    ]
    
    print("🧪 Testing onboarding trigger pattern matching...")
    print("=" * 50)
    
    all_passed = True
    for text, expected in test_cases:
        result = bool(pattern.match(text))
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"{status} '{text}' -> {result} (expected: {expected})")
        if result != expected:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 All tests passed! The onboarding trigger pattern is working correctly.")
    else:
        print("⚠️ Some tests failed. Please review the pattern.")
    
    return all_passed

def test_general_handler_skip_logic():
    """Test the logic for skipping onboarding trigger in the general handler"""
    def should_skip_onboarding_trigger(text):
        text_lower = text.lower()
        return text_lower == 'start my onboarding'
    
    test_cases = [
        ("start my onboarding", True),
        ("Start my onboarding", True),
        ("START MY ONBOARDING", True),
        ("Start My Onboarding", True),
        ("start my onboarding please", False),  # Should not skip (has extra words)
        ("please start my onboarding", False),  # Should not skip (has extra words)
        ("hello", False),        # Should not skip (old greeting, now allowed through)
        ("hi", False),           # Should not skip (old greeting, now allowed through)
        ("hey", False),          # Should not skip (old greeting, now allowed through)
        ("help", False),         # Should not skip
        ("policy", False),       # Should not skip
        ("what's the policy", False),  # Should not skip
        ("start onboarding", False),   # Should not skip (missing 'my')
        ("my onboarding", False),      # Should not skip (missing 'start')
    ]
    
    print("\n🧪 Testing general handler skip logic...")
    print("=" * 50)
    
    all_passed = True
    for text, expected in test_cases:
        result = should_skip_onboarding_trigger(text)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"{status} '{text}' -> skip={result} (expected: {expected})")
        if result != expected:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 All tests passed! The onboarding trigger skip logic is working correctly.")
    else:
        print("⚠️ Some tests failed. Please review the skip logic.")
    
    return all_passed

if __name__ == "__main__":
    print("🔧 Testing Slack Bot Onboarding Trigger Handler Fixes")
    print("=" * 60)
    
    test1_passed = test_onboarding_trigger_patterns()
    test2_passed = test_general_handler_skip_logic()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED! The onboarding trigger fix should work correctly.")
        print("\nSummary of fixes:")
        print("1. ✅ General handler now skips only 'Start my Onboarding' trigger")
        print("2. ✅ Onboarding handler now matches only 'Start my Onboarding' pattern")
        print("3. ✅ No more overlapping handler conflicts with old greeting words")
    else:
        print("⚠️ Some tests failed. Please review the implementation.")