from air_quality.data.cleaning import normalize_value, standardize_column_name


def test_standardize_column_name() -> None:
    assert standardize_column_name("AQI_Bucket") == "aqi_bucket"
    assert standardize_column_name("PM2.5") == "pm2_5"


def test_normalize_configured_missing_tokens() -> None:
    assert normalize_value("  NA ") == ""
    assert normalize_value("  Delhi ") == "Delhi"
