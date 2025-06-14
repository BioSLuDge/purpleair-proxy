from flask import Flask, jsonify, request
import requests
import os
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get settings from environment variables
PURPLEAIR_SENSOR_IP = os.environ.get("PURPLEAIR_SENSOR_IP")
MY_API_KEY = os.environ.get("MY_API_KEY")  # Your custom API key for this proxy
AVERAGE_CHANNELS = os.environ.get("AVERAGE_CHANNELS", "True").lower() in ('true', '1', 't')
DEBUG_MODE = os.environ.get("DEBUG_MODE", "False").lower() in ('true', '1', 't')

if DEBUG_MODE:
    app.logger.setLevel(logging.DEBUG)
    app.logger.debug("Debug mode is enabled.")


@app.route('/api/purpleair', methods=['GET'])
def get_purpleair_data():
    app.logger.info(f"Received request from IP: {request.remote_addr}")

    # --- API Key Authentication (Optional but Recommended) ---
    if MY_API_KEY:
        client_api_key = request.headers.get('X-API-Key')
        if not client_api_key:
            app.logger.warning(f"Unauthorized: No X-API-Key header provided from {request.remote_addr}")
            return jsonify({"error": "Unauthorized: X-API-Key header required"}), 401
        if client_api_key != MY_API_KEY:
            app.logger.warning(f"Unauthorized: Invalid X-API-Key provided from {request.remote_addr}")
            return jsonify({"error": "Unauthorized: Invalid X-API-Key"}), 401
        app.logger.debug("API Key authenticated successfully.")
    else:
        app.logger.warning(
            "MY_API_KEY environment variable is not set. API endpoint is publicly accessible without a custom key.")

    if not PURPLEAIR_SENSOR_IP:
        app.logger.error("PURPLEAIR_SENSOR_IP environment variable is not set.")
        return jsonify({"error": "Server configuration error: PurpleAir sensor IP not set"}), 500

    purpleair_url = f"http://{PURPLEAIR_SENSOR_IP}/json?live=true"
    app.logger.debug(f"Attempting to fetch data from PurpleAir sensor at: {purpleair_url}")

    try:
        response = requests.get(purpleair_url, timeout=10)
        response.raise_for_status()
        sensor_data = response.json()
        app.logger.debug("Successfully fetched data from PurpleAir sensor.")

        # --- Extracting Data - Using your specific JSON structure ---
        pm25_aqi_a = sensor_data.get('pm2.5_aqi')
        pm25_aqi_b = sensor_data.get('pm2.5_aqi_b')

        pm25_atm_a = sensor_data.get('pm2_5_atm')
        pm25_atm_b = sensor_data.get('pm2_5_atm_b')

        pm25_aqi = None
        pm25_atm = None

        if AVERAGE_CHANNELS and pm25_aqi_a is not None and pm25_aqi_b is not None:
            pm25_aqi = (pm25_aqi_a + pm25_aqi_b) / 2
        else:
            pm25_aqi = pm25_aqi_a if pm25_aqi_a is not None else pm25_aqi_b

        if AVERAGE_CHANNELS and pm25_atm_a is not None and pm25_atm_b is not None:
            pm25_atm = (pm25_atm_a + pm25_atm_b) / 2
        else:
            pm25_atm = pm25_atm_a if pm25_atm_a is not None else pm25_atm_b

        # Get the timestamp
        last_update_datetime = sensor_data.get('DateTime')  # This is a string like "2025/06/14T01:21:34z"

        if pm25_aqi is not None and pm25_atm is not None:
            app.logger.info(f"Successfully retrieved AQI: {pm25_aqi}, PM2.5: {pm25_atm}")
            return jsonify({
                "pm2_5_aqi": pm25_aqi,
                "pm2_5_atm": pm25_atm,
                "sensor_last_update_datetime": last_update_datetime  # Use the string directly
            })
        else:
            # Log all available PM2.5 related keys if required data is missing for debugging
            available_keys = [k for k in sensor_data.keys() if 'pm2_5' in k or 'aqi' in k]
            app.logger.error(
                f"Required data (pm2_5_aqi or pm2_5_aqi_b, and pm2_5_atm or pm2_5_atm_b) not found in sensor response. Available relevant keys: {available_keys}")
            return jsonify({"error": "Required air quality data not found in sensor response"}), 500

    except requests.exceptions.Timeout:
        app.logger.error(f"Timeout occurred while fetching data from PurpleAir sensor at {purpleair_url}")
        return jsonify({"error": "Timeout connecting to PurpleAir sensor"}), 504  # Gateway Timeout
    except requests.exceptions.ConnectionError as e:
        app.logger.error(f"Connection error to PurpleAir sensor at {purpleair_url}: {e}")
        return jsonify(
            {"error": "Failed to connect to PurpleAir sensor. Check IP address and network."}), 502  # Bad Gateway
    except requests.exceptions.HTTPError as e:
        app.logger.error(f"HTTP error from PurpleAir sensor at {purpleair_url}: {e}")
        return jsonify({"error": f"Error response from PurpleAir sensor: {e.response.status_code}"}), 500
    except requests.exceptions.RequestException as e:
        app.logger.error(f"An unknown request error occurred: {e}")
        return jsonify({"error": "An error occurred while communicating with the sensor."}), 500
    except Exception as e:
        app.logger.error(f"An unexpected server error occurred: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=DEBUG_MODE)