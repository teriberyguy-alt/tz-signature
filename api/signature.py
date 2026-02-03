import json  # Add this to imports if not there

# ... inside generate_signature():

    overlay_text = "TZ data unavailable"

    try:
        tz_url = 'https://d2runewizard.com/api/terror-zone'
        response = requests.get(tz_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()  # Parse as JSON
        
        # Extract current and next
        current = data.get('currentTerrorZone', {})
        next_tz = data.get('nextTerrorZone', {})
        
        current_zone = current.get('zone', 'Unknown')
        current_act = current.get('act', '')
        next_zone = next_tz.get('zone', 'Unknown')
        next_act = next_tz.get('act', '')
        
        # Format nicely (add act if present)
        current_str = f"{current_zone}, {current_act}" if current_act else current_zone
        next_str = f"{next_zone}, {next_act}" if next_act else next_zone
        
        overlay_text = f"Current: {current_str}\nNext: {next_str}"
        
    except requests.exceptions.RequestException as e:
        overlay_text = f"TZ fetch error: {str(e)[:50]}"
    except json.JSONDecodeError:
        overlay_text = "Invalid TZ data format"
    except Exception as e:
        overlay_text = f"Error: {str(e)[:50]}"

    # Then the rest (try: Image.open etc.) stays the same
