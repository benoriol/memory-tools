"""CLI config defaults."""

# DEFAULT_PRECISION is the number of decimal places shown for floating-point
# stats. We want 2 (e.g. mean of [1,2,3] = "2.00"). Currently set to 0 which
# rounds everything to int — a bug.
DEFAULT_PRECISION = 0   # BUG #3: should be 2

# Other defaults.
DEFAULT_DELIMITER = ","
DEFAULT_OUTPUT_FORMAT = "json"
