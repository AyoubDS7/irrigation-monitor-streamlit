CREATE DATABASE irrigation_db;

USE irrigation_db;

CREATE TABLE irrigation_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME,
    humidity FLOAT,
    temperature FLOAT,
    soil_moisture FLOAT,
    rain_level FLOAT,
    env_temperature FLOAT,
    precip_mm FLOAT,
    et0 FLOAT,
    soil_temperature FLOAT,
    soil_moisture_27_81cm FLOAT,
    prediction INT
);
SELECT * FROM irrigation_data;