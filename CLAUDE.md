# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Communication and Environment

**IMPORTANT**: Always communicate with the user in Russian language. The user prefers Russian for all conversations, explanations, and documentation.

**Development Environment**:
- Operating System: Windows (MINGW64_NT)
- Arduino IDE: Russian language interface
- Use Windows-style paths (backslashes or forward slashes)
- PowerShell/CMD commands for terminal operations

## Project Overview

ESP32-S3 Cat-Following Robot - an autonomous robot that uses computer vision to detect and follow a cat. The system consists of:
- **ESP32-S3-DevKitC-1 N8R2** for motor control via WiFi (8MB Flash, 2MB PSRAM)
- **2x MX1508 motor drivers** (dual-channel) controlling two yellow DC motors
- **IP camera** (rotating WiFi camera) with RTSP stream for video input
- **Wooden platform** with two main wheels and one support wheel
- **PowerBank or 18650 battery** for power supply
- **Python script** running on PC for cat detection using OpenCV
- **Web-based control interface** for motor commands

## System Architecture

**Data Flow:**
1. IP Camera → WiFi → PC (RTSP stream)
2. PC Python script → Computer Vision (cat detection)
3. PC → WiFi → ESP32 (HTTP commands)
4. ESP32 → MX1508 drivers → Motors (PWM control)

## Hardware Configuration

### ESP32-S3 Model
- Board: ESP32-S3-DevKitC-1 N8R2
  - N8 = 8MB Flash
  - R2 = 2MB PSRAM (OPI PSRAM)

### Critical Pin Constraints
- **NEVER use GPIO 26-32**: Reserved for Flash/PSRAM
- **Safe pins**: GPIO 1-18, GPIO 33-48
- **Avoid GPIO 19-20**: Used for USB (if USB functionality needed)

### Current Pin Assignment (for esp32_cat_follower_simple.ino)
- **Left Motor**: GPIO1 (IN1), GPIO2 (IN2)
- **Right Motor**: GPIO42 (IN3), GPIO41 (IN4)
- **LED**: GPIO48 (WS2812 RGB LED - requires special handling)

### MX1508 Motor Driver Connections
Each MX1508 is a dual-channel H-bridge driver:
- **Channel A (Left Motor)**: IN1, IN2 → MOTOR-A outputs
- **Channel B (Right Motor)**: IN3, IN4 → MOTOR-B outputs
- **Power**: VCC (5V logic), VM (5V motor power), GND (common ground)
- **Important**: All GND must be connected together (ESP32, MX1508, PowerBank)

## Arduino IDE Setup

**Note**: Arduino IDE interface is in Russian. Menu paths:
- Tools = Инструменты
- Board = Плата
- Port = Порт
- Serial Monitor = Монитор порта

### Board Configuration
When uploading sketches, use these settings in Tools (Инструменты) menu:
- **Board**: ESP32S3 Dev Module
- **USB CDC On Boot**: Enabled (CRITICAL)
- **PSRAM**: OPI PSRAM
- **Flash Size**: 8MB
- **Partition Scheme**: 8M with spiffs (3.6MB APP/1.5MB SPIFFS)
- **Upload Speed**: 921600 (or 115200 if issues occur)
- **USB Mode**: Hardware CDC and JTAG

### Upload Process
If automatic upload fails:
1. Hold BOOT button
2. Press RST button
3. Release RST, then BOOT
4. Click Upload quickly

## Code Structure

### Arduino Sketches

**test_wifi_only/test_wifi_only.ino** - WiFi connectivity test (no motors)
- Tests WiFi connection
- Provides web interface with LED control
- Should be used FIRST before connecting motors
- LED control endpoints: `/led/on`, `/led/off`, `/led/blink`

**esp32_cat_follower_simple/esp32_cat_follower_simple.ino** - Main robot control (simplified)
- Simplified version with detailed comments
- Uses analogWrite() for PWM (simpler API)
- Motor control endpoints: `/forward`, `/backward`, `/left`, `/right`, `/stop`
- Speed control: `/speed?value=0-255`
- Unified API: `/command?action=forward&speed=150`

**files/esp32_cat_follower.ino** - Alternative implementation
- Uses LEDC (LED Controller) API for PWM
- More precise PWM control
- Different GPIO pins (GPIO12, 14, 27, 26)

### Motor Control Architecture

Both implementations use the same logic:
- Forward: Both motors forward (IN1/IN3 high, IN2/IN4 low)
- Backward: Both motors reverse (IN1/IN3 low, IN2/IN4 high)
- Left: Right motor only (left motor stopped)
- Right: Left motor only (right motor stopped)
- Stop: All pins low

### Python Vision System

Located in `files/cat_follower_robot.py`:
- Connects to IP camera RTSP stream
- Detects cat using OpenCV
- Sends HTTP commands to ESP32
- Real-time video display with detection overlay

## Development Workflow

### Initial Hardware Test
1. Upload `test_wifi_only/test_wifi_only.ino` first
2. Configure WiFi credentials (ssid/password)
3. Open Serial Monitor at 115200 baud
4. Note the IP address
5. Test web interface in browser
6. Verify LED control works

### Motor Integration
1. **Power off everything**
2. Wire motors according to WIRING_DIAGRAM.md
3. Verify all GND connections are common
4. Upload `esp32_cat_follower_simple/esp32_cat_follower_simple.ino`
5. Test motors with wheels off ground
6. If motor direction wrong, swap motor wires (not GPIO pins)

### Python Setup
```bash
python -m venv cat_env
cat_env\Scripts\activate  # Windows
pip install opencv-python opencv-contrib-python numpy requests
```

Configure in Python script:
- CAMERA_URL: RTSP stream URL
- ESP32_IP: IP from Serial Monitor

## WiFi Network Requirements

- ESP32-S3 only supports 2.4GHz WiFi (not 5GHz)
- All devices (ESP32, camera, PC) must be on same local network
- Router typically bridges 2.4GHz and 5GHz into same subnet
- PC can be on 5GHz and still communicate with ESP32 on 2.4GHz

## Troubleshooting

### LED Always On (GPIO48)
GPIO48 may be a WS2812 RGB LED requiring special library (NeoPixel/FastLED) instead of digitalWrite(). If simple HIGH/LOW doesn't work, this is likely the cause.

### Upload Failures
- Try different USB cable (must support data)
- Use manual boot mode (BOOT + RST)
- Lower upload speed to 115200
- Try other USB port on ESP32 (if two available)

### WiFi Connection Issues
- Verify SSID and password are correct
- Ensure router broadcasts 2.4GHz
- Check router allows new device connections
- Move ESP32 closer to router

### Motors Don't Move
- Check MX1508 has power (LED indicator)
- Verify GPIO connections
- Test with browser commands first
- Ensure PowerBank provides sufficient current (2A+)

## API Reference

### REST Endpoints

GET `/` - HTML control interface

GET `/forward` - Move forward
GET `/backward` - Move backward
GET `/left` - Turn left
GET `/right` - Turn right
GET `/stop` - Stop motors

GET `/speed?value=<0-255>` - Set motor speed

GET `/command?action=<action>&speed=<0-255>` - Unified command
- Actions: forward, backward, left, right, stop
- Returns JSON response

For test_wifi_only.ino only:
GET `/led/on` - Turn LED on
GET `/led/off` - Turn LED off
GET `/led/blink` - Blink LED pattern

## Serial Monitor Output

Expected at startup (115200 baud):
```
========================================
ESP32-S3 WiFi Test / Cat Follower Robot
========================================
Connecting to: <SSID>
CONNECTED!
IP address: 192.168.X.XXX
========================================
```

Note this IP address - required for Python script and browser control.

## Hardware Components Details

### Physical Components (from user's setup)
- **ESP32 Board**: ESP32-S3-DevKitC-1 N8R2 with two USB-C ports (labeled "COM" and "USB")
- **Motor Drivers**: 2x MX1508 red PCB boards (dual-channel H-bridge)
- **Motors**: 2x yellow DC motors with gear reduction
- **Platform**: Wooden chassis with mounting holes
- **Wheels**: 2x main drive wheels + 1x front support wheel (ball caster)
- **Camera**: White rotating IP camera with WiFi antenna
- **WiFi Setup**: Configure WiFi credentials in .env file (see .env.example for template)

### Known Issues from Testing
1. **LED GPIO48**: On this board, GPIO48 is a WS2812 RGB LED that does NOT respond to simple digitalWrite(). It stays permanently on after WiFi connection. Use NeoPixel/FastLED library if LED control needed.
2. **Test Sequence**: The `test_wifi_only.ino` was successfully tested, WiFi connects to IP 192.168.0.112
3. **Web Interface**: LED control buttons in web interface don't affect the physical LED (WS2812 issue)

## Important Notes

- **CRITICAL**: Always test WiFi-only code before connecting motors
- Never connect motors while USB programming (power separately during motor tests)
- Common GND is critical - all components must share ground
- Motor direction fixed by swapping motor wires, not changing code
- When modifying GPIO pins, respect ESP32-S3 constraints (avoid GPIO 26-32)
- This specific board has WS2812 RGB LED on GPIO48 (not simple LED)
