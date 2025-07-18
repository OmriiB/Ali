from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import ipaddress

app = Flask(__name__)

# Enable CORS for all routes
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configuration
DATA_FILE = 'vlans.json'


def load_vlans():
    """Load VLANs from JSON file"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    return {}


def save_vlans(vlans):
    """Save VLANs to JSON file"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(vlans, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving VLANs: {e}")
        return False


def validate_vlan_data(data):
    """Validate VLAN data"""
    required_fields = ['vlan_id', 'name', 'subnet']

    # Check required fields
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"

    # Validate VLAN ID (1-4094)
    try:
        vlan_id = int(data['vlan_id'])
        if not (1 <= vlan_id <= 4094):
            return False, "VLAN ID must be between 1 and 4094"
    except (ValueError, TypeError):
        return False, "VLAN ID must be a valid integer"

    # Validate subnet
    try:
        ipaddress.ip_network(data['subnet'], strict=False)
    except ValueError:
        return False, "Invalid subnet format"

    return True, "Valid"


@app.route('/api/vlans', methods=['GET'])
def get_all_vlans():
    """Get all VLANs"""
    vlans = load_vlans()
    return jsonify({
        'status': 'success',
        'data': vlans,
        'count': len(vlans)
    })


@app.route('/api/vlans/<int:vlan_id>', methods=['GET'])
def get_vlan(vlan_id):
    """Get specific VLAN by ID"""
    vlans = load_vlans()
    vlan_key = str(vlan_id)

    if vlan_key not in vlans:
        return jsonify({
            'status': 'error',
            'message': f'VLAN {vlan_id} not found'
        }), 404

    return jsonify({
        'status': 'success',
        'data': vlans[vlan_key]
    })


@app.route('/api/vlans', methods=['POST'])
def create_vlan():
    """Create a new VLAN"""
    data = request.get_json()

    if not data:
        return jsonify({
            'status': 'error',
            'message': 'No JSON data provided'
        }), 400

    # Validate data
    is_valid, message = validate_vlan_data(data)
    if not is_valid:
        return jsonify({
            'status': 'error',
            'message': message
        }), 400

    vlans = load_vlans()
    vlan_key = str(data['vlan_id'])

    # Check if VLAN already exists
    if vlan_key in vlans:
        return jsonify({
            'status': 'error',
            'message': f'VLAN {data["vlan_id"]} already exists'
        }), 409

    # Create VLAN entry
    vlan_entry = {
        'vlan_id': int(data['vlan_id']),
        'name': data['name'],
        'subnet': data['subnet'],
        'description': data.get('description', ''),
        'gateway': data.get('gateway', ''),
        'status': data.get('status', 'active'),
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }

    vlans[vlan_key] = vlan_entry

    if save_vlans(vlans):
        return jsonify({
            'status': 'success',
            'message': f'VLAN {data["vlan_id"]} created successfully',
            'data': vlan_entry
        }), 201
    else:
        return jsonify({
            'status': 'error',
            'message': 'Failed to save VLAN'
        }), 500


@app.route('/api/vlans/<int:vlan_id>', methods=['PUT'])
def update_vlan(vlan_id):
    """Update existing VLAN"""
    data = request.get_json()

    if not data:
        return jsonify({
            'status': 'error',
            'message': 'No JSON data provided'
        }), 400

    vlans = load_vlans()
    vlan_key = str(vlan_id)

    if vlan_key not in vlans:
        return jsonify({
            'status': 'error',
            'message': f'VLAN {vlan_id} not found'
        }), 404

    # Get existing VLAN
    existing_vlan = vlans[vlan_key]

    # Update fields
    if 'name' in data:
        existing_vlan['name'] = data['name']
    if 'subnet' in data:
        try:
            ipaddress.ip_network(data['subnet'], strict=False)
            existing_vlan['subnet'] = data['subnet']
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid subnet format'
            }), 400
    if 'description' in data:
        existing_vlan['description'] = data['description']
    if 'gateway' in data:
        existing_vlan['gateway'] = data['gateway']
    if 'status' in data:
        existing_vlan['status'] = data['status']

    existing_vlan['updated_at'] = datetime.now().isoformat()

    if save_vlans(vlans):
        return jsonify({
            'status': 'success',
            'message': f'VLAN {vlan_id} updated successfully',
            'data': existing_vlan
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Failed to save VLAN'
        }), 500


@app.route('/api/vlans/<int:vlan_id>', methods=['DELETE'])
def delete_vlan(vlan_id):
    """Delete VLAN"""
    vlans = load_vlans()
    vlan_key = str(vlan_id)

    if vlan_key not in vlans:
        return jsonify({
            'status': 'error',
            'message': f'VLAN {vlan_id} not found'
        }), 404

    deleted_vlan = vlans.pop(vlan_key)

    if save_vlans(vlans):
        return jsonify({
            'status': 'success',
            'message': f'VLAN {vlan_id} deleted successfully',
            'data': deleted_vlan
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Failed to save changes'
        }), 500


@app.route('/api/vlans/search', methods=['GET'])
def search_vlans():
    """Search VLANs by name or subnet"""
    query = request.args.get('q', '').lower()
    status = request.args.get('status', '')

    if not query and not status:
        return jsonify({
            'status': 'error',
            'message': 'Please provide search query (q) or status parameter'
        }), 400

    vlans = load_vlans()
    results = {}

    for vlan_id, vlan_data in vlans.items():
        match = False

        if query:
            if (query in vlan_data['name'].lower() or
                    query in vlan_data.get('description', '').lower() or
                    query in vlan_data['subnet'].lower()):
                match = True

        if status and vlan_data.get('status', '').lower() == status.lower():
            match = True

        if match:
            results[vlan_id] = vlan_data

    return jsonify({
        'status': 'success',
        'data': results,
        'count': len(results)
    })


@app.route('/api/vlans/backup', methods=['GET'])
def backup_vlans():
    """Create backup of all VLANs"""
    vlans = load_vlans()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'vlans_backup_{timestamp}.json'

    try:
        with open(backup_filename, 'w') as f:
            json.dump(vlans, f, indent=2)

        return jsonify({
            'status': 'success',
            'message': f'Backup created successfully: {backup_filename}',
            'filename': backup_filename,
            'count': len(vlans)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to create backup: {str(e)}'
        }), 500


@app.route('/api/vlans/restore', methods=['POST'])
def restore_vlans():
    """Restore VLANs from backup file"""
    data = request.get_json()

    if not data or 'filename' not in data:
        return jsonify({
            'status': 'error',
            'message': 'Please provide backup filename'
        }), 400

    backup_file = data['filename']

    if not os.path.exists(backup_file):
        return jsonify({
            'status': 'error',
            'message': f'Backup file {backup_file} not found'
        }), 404

    try:
        with open(backup_file, 'r') as f:
            backup_vlans = json.load(f)

        if save_vlans(backup_vlans):
            return jsonify({
                'status': 'success',
                'message': f'VLANs restored successfully from {backup_file}',
                'count': len(backup_vlans)
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to restore VLANs'
            }), 500

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to restore from backup: {str(e)}'
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'success',
        'message': 'VLAN Management API is running',
        'timestamp': datetime.now().isoformat()
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'status': 'error',
        'message': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500


if __name__ == '__main__':
    print("Starting VLAN Management API...")
    print("Available endpoints:")
    print("  GET    /api/vlans - Get all VLANs")
    print("  POST   /api/vlans - Create new VLAN")
    print("  GET    /api/vlans/<id> - Get specific VLAN")
    print("  PUT    /api/vlans/<id> - Update VLAN")
    print("  DELETE /api/vlans/<id> - Delete VLAN")
    print("  GET    /api/vlans/search?q=<query>&status=<status> - Search VLANs")
    print("  GET    /api/vlans/backup - Create backup")
    print("  POST   /api/vlans/restore - Restore from backup")
    print("  GET    /api/health - Health check")

    app.run(debug=True, host='0.0.0.0', port=5000)
