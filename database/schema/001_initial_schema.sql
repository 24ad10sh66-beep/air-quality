-- Air Quality Intelligence initial schema.
-- Safe to run against a selected database: CREATE TABLE IF NOT EXISTS only.
-- This script does not create, drop, truncate, or alter databases.

CREATE TABLE IF NOT EXISTS air_quality_readings(
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    city VARCHAR(100) NOT NULL,
    observed_at DATETIME NULL,
    pm2_5 DOUBLE NULL,
    pm10 DOUBLE NULL,
    no_value DOUBLE NULL,
    no2 DOUBLE NULL,
    nox DOUBLE NULL,
    nh3 DOUBLE NULL,
    co DOUBLE NULL,
    so2 DOUBLE NULL,
    o3 DOUBLE NULL,
    benzene DOUBLE NULL,
    toluene DOUBLE NULL,
    xylene DOUBLE NULL,
    aqi DOUBLE NULL,
    aqi_bucket VARCHAR(32) NULL,
    source_date DATE NULL,
    station VARCHAR(100) NULL,
    source_row_number INT UNSIGNED NULL,
    import_batch_id CHAR(36) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX ix_readings_city_observed_at (city, observed_at),
    INDEX ix_readings_station_observed_at (station, observed_at),
    INDEX ix_readings_import_batch (import_batch_id)
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS import_batches (
    id CHAR(36) NOT NULL,
    source_path VARCHAR(500) NOT NULL,
    source_sha256 CHAR(64) NOT NULL,
    attempted_rows INT UNSIGNED NOT NULL,
    inserted_rows INT UNSIGNED NOT NULL,
    rejected_rows INT UNSIGNED NOT NULL,
    status VARCHAR(32) NOT NULL,
    started_at DATETIME NOT NULL,
    completed_at DATETIME NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_import_batches_checksum (source_sha256),
    INDEX ix_import_batches_status (status)
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS model_runs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(100) NULL,
    target_name VARCHAR(100) NOT NULL,
    horizon VARCHAR(50) NOT NULL,
    dataset_checksum CHAR(64) NOT NULL,
    train_start DATE NULL,
    train_end DATE NULL,
    validation_start DATE NULL,
    validation_end DATE NULL,
    test_start DATE NULL,
    test_end DATE NULL,
    parameters_json JSON NULL,
    metrics_json JSON NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX ix_model_runs_target_created (target_name, created_at)
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS forecasts (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    model_run_id BIGINT UNSIGNED NOT NULL,
    city VARCHAR(100) NOT NULL,
    station VARCHAR(100) NULL,
    target_name VARCHAR(100) NOT NULL,
    target_time DATETIME NOT NULL,
    generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    horizon VARCHAR(50) NOT NULL,
    prediction DOUBLE NOT NULL,
    PRIMARY KEY (id),
    INDEX ix_forecasts_lookup (city, station, target_time),
    CONSTRAINT fk_forecasts_model_run
        FOREIGN KEY (model_run_id) REFERENCES model_runs (id)
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS anomaly_events (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    reading_id BIGINT UNSIGNED NULL,
    method VARCHAR(100) NOT NULL,
    anomaly_score DOUBLE NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'potential',
    notes VARCHAR(500) NULL,
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX ix_anomalies_reading (reading_id),
    CONSTRAINT fk_anomalies_reading
        FOREIGN KEY (reading_id) REFERENCES air_quality_readings (id)
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS live_aqi_history(
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    location_name VARCHAR(150) NULL,
    latitude DOUBLE NOT NULL,
    longitude DOUBLE NOT NULL,
    observed_at DATETIME NULL,
    fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    aqi DOUBLE NULL,
    aqi_bucket VARCHAR(32) NULL,
    pollutants_json JSON NOT NULL,
    source VARCHAR(50) NOT NULL,
    PRIMARY KEY (id),
    INDEX ix_live_history_location (latitude, longitude, fetched_at)
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
