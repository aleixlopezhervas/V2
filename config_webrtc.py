"""
config_webrtc.py - Configuración centralizada de WebRTC para misma LAN
"""

import socket


def get_local_ip():
    """Obtener la IP local de la máquina en la LAN"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_config():
    """Obtener configuración de WebRTC"""
    return {
        'camera_service': {
            'host': '0.0.0.0',
            'port': 9999,
            'local_ip': get_local_ip(),
        },
        'dashboard_local': {
            'camera_server': get_local_ip(),
            'camera_port': 9999
        },
        'dashboard_global': {
            'camera_server': get_local_ip(),
            'camera_port': 9999
        }
    }


if __name__ == "__main__":
    import json
    config = get_config()
    print(json.dumps(config, indent=2))



def save_config_file():
    """Guardar la configuración en un archivo JSON para referencia"""
    try:
        config = get_config()
        config_file = os.path.join(os.path.dirname(__file__), 'webrtc_config.json')
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        return config_file
    except Exception as e:
        print(f"[CONFIG] Error guardando configuración: {e}")
        return None


# Configuración global disponible para todos los módulos
CONFIG = get_config()

if __name__ == "__main__":
    print("Configuración WebRTC para misma LAN:")
    print(json.dumps(CONFIG, indent=2))
    
    print("\n" + "="*50)
    print(f"IP local detectada: {CONFIG['camera_service']['local_ip']}")
    print(f"Puerto CameraService: {CONFIG['camera_service']['port']}")
    print("="*50)

