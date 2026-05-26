#!/usr/bin/env python3
"""
MQTT Metrics Publisher
Publishes system metrics to MQTT broker for monitoring
"""
import json
import time
import psutil
import paho.mqtt.client as mqtt
from datetime import datetime
from typing import Dict, Any

# MQTT Configuration
MQTT_BROKER = "fastapi-mosquitto"
MQTT_PORT = 1883
MQTT_TOPIC = "metrics/system"
MQTT_CLIENT_ID = "fastapi-metrics-publisher"
MQTT_USERNAME = None  # Set if authentication is required
MQTT_PASSWORD = None  # Set if authentication is required

# Metrics collection interval (seconds)
METRICS_INTERVAL = 30

class MetricsPublisher:
    """MQTT Metrics Publisher"""
    
    def __init__(self):
        self.client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
        
        if MQTT_USERNAME and MQTT_PASSWORD:
            self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            print(f"✅ Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        else:
            print(f"❌ Failed to connect to MQTT broker, return code: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        if rc != 0:
            print(f"⚠️ Unexpected disconnection from MQTT broker, return code: {rc}")
        else:
            print("ℹ️ Disconnected from MQTT broker")
    
    def on_publish(self, client, userdata, mid):
        """Callback when message is published"""
        print(f"📤 Message published with ID: {mid}")
    
    def connect(self):
        """Connect to MQTT broker"""
        try:
            print(f"🔌 Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"❌ Failed to connect to MQTT broker: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            print("🔌 Disconnected from MQTT broker")
        except Exception as e:
            print(f"❌ Error disconnecting from MQTT broker: {e}")
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            # Network metrics
            network = psutil.net_io_counters()
            
            # Process metrics
            process = psutil.Process()
            
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "hostname": psutil.gethostname(),
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": cpu_count,
                    "frequency_mhz": cpu_freq.current if cpu_freq else None,
                },
                "memory": {
                    "total_bytes": memory.total,
                    "available_bytes": memory.available,
                    "used_bytes": memory.used,
                    "usage_percent": memory.percent,
                },
                "disk": {
                    "total_bytes": disk.total,
                    "used_bytes": disk.used,
                    "free_bytes": disk.free,
                    "usage_percent": (disk.used / disk.total) * 100,
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv,
                },
                "process": {
                    "pid": process.pid,
                    "memory_info": {
                        "rss": process.memory_info().rss,
                        "vms": process.memory_info().vms,
                    },
                    "cpu_percent": process.cpu_percent(),
                    "num_threads": process.num_threads(),
                }
            }
            
            return metrics
            
        except Exception as e:
            print(f"❌ Error collecting system metrics: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    def publish_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Publish metrics to MQTT broker"""
        try:
            # Convert metrics to JSON
            payload = json.dumps(metrics, default=str)
            
            # Publish to MQTT
            result = self.client.publish(MQTT_TOPIC, payload, qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"📊 Published metrics to {MQTT_TOPIC}")
                return True
            else:
                print(f"❌ Failed to publish metrics: {result.rc}")
                return False
                
        except Exception as e:
            print(f"❌ Error publishing metrics: {e}")
            return False
    
    def run(self):
        """Main run loop"""
        print("🚀 Starting MQTT Metrics Publisher...")
        
        if not self.connect():
            print("❌ Failed to connect to MQTT broker. Exiting.")
            return
        
        try:
            print(f"📊 Publishing metrics every {METRICS_INTERVAL} seconds...")
            print(f"📡 MQTT Topic: {MQTT_TOPIC}")
            
            while True:
                # Collect and publish metrics
                metrics = self.collect_system_metrics()
                self.publish_metrics(metrics)
                
                # Wait for next interval
                time.sleep(METRICS_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n🛑 Received interrupt signal. Shutting down...")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        finally:
            self.disconnect()
            print("👋 MQTT Metrics Publisher stopped.")


def main():
    """Main function"""
    publisher = MetricsPublisher()
    publisher.run()


if __name__ == "__main__":
    main()
