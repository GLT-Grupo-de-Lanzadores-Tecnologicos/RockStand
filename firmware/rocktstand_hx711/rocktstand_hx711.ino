/*
 * RocktStand - Rocket Stand Test Software
 * HX711 load cell firmware (Grupo de Lanzadores Tecnologicos - UTN Haedo)
 *
 * Line-based ASCII protocol at 115200 baud, one reply per command:
 *   G           -> one measurement in kgf (average of 3 samples), e.g. "1.2345"
 *   F:<factor>  -> set the HX711 scale factor     -> "OK" / "ERROR:factor_invalido"
 *   R           -> recording started (LED blinks) -> "OK"
 *   S           -> recording stopped (LED off)    -> "OK"
 *   other       -> "ERROR:comando_desconocido"
 *
 * Wiring: HX711 DOUT = 2, CLK = 3, watchdog LED = A1, recording LED = A3.
 * The load cell is tared at power-up; the scale factor is kept in RAM only.
 * Full description: docs/serial_protocol.md
 *
 * Requires an HX711 Arduino library providing HX711.h (begin, set_scale,
 * tare, get_units).
 * MIT License - see LICENSE in the repository root.
 */

#include "HX711.h"

const int DOUT = 2;
const int CLK = 3;
const int LED_WATCHDOG = A1;
const int LED_RECORDING = A3;

const unsigned long WATCHDOG_BLINK_INTERVAL_MS = 500;
const unsigned long RECORDING_BLINK_INTERVAL_MS = 200;
const unsigned long COMM_ACTIVE_TIMEOUT_MS = 2000;

HX711 balanza;

float factorEscala = 43943.025;
bool recordingActive = false;
bool watchdogBlinkState = true;
bool recordingBlinkState = false;
unsigned long lastWatchdogToggleMs = 0;
unsigned long lastRecordingToggleMs = 0;
unsigned long lastCommMs = 0;

void updateLeds() {
  unsigned long now = millis();
  bool commActive = (now - lastCommMs) <= COMM_ACTIVE_TIMEOUT_MS;

  if (commActive) {
    if ((now - lastWatchdogToggleMs) >= WATCHDOG_BLINK_INTERVAL_MS) {
      lastWatchdogToggleMs = now;
      watchdogBlinkState = !watchdogBlinkState;
    }
  } else {
    watchdogBlinkState = true;
  }

  if (recordingActive) {
    if ((now - lastRecordingToggleMs) >= RECORDING_BLINK_INTERVAL_MS) {
      lastRecordingToggleMs = now;
      recordingBlinkState = !recordingBlinkState;
    }
  } else {
    recordingBlinkState = false;
  }

  digitalWrite(LED_WATCHDOG, watchdogBlinkState ? HIGH : LOW);
  digitalWrite(LED_RECORDING, recordingBlinkState ? HIGH : LOW);
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_WATCHDOG, OUTPUT);
  pinMode(LED_RECORDING, OUTPUT);
  digitalWrite(LED_WATCHDOG, HIGH);
  digitalWrite(LED_RECORDING, LOW);
  lastCommMs = millis();
  lastWatchdogToggleMs = lastCommMs;
  lastRecordingToggleMs = lastCommMs;
  balanza.begin(DOUT, CLK);
  balanza.set_scale(factorEscala);
  balanza.tare(20);
}

void loop() {
  updateLeds();

  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    lastCommMs = millis();

    if (cmd == "G" || cmd == "G\r") {
      float peso = balanza.get_units(3);
      Serial.println(peso, 4);
    } else if (cmd == "R" || cmd == "R\r") {
      recordingActive = true;
      lastRecordingToggleMs = millis();
      recordingBlinkState = true;
      Serial.println("OK");
    } else if (cmd == "S" || cmd == "S\r") {
      recordingActive = false;
      recordingBlinkState = false;
      Serial.println("OK");
    } else if (cmd.startsWith("F:")) {
      String valorStr = cmd.substring(2);
      float nuevoFactor = valorStr.toFloat();
      if (nuevoFactor != 0.0) {
        factorEscala = nuevoFactor;
        balanza.set_scale(factorEscala);
        Serial.println("OK");
      } else {
        Serial.println("ERROR:factor_invalido");
      }
    } else {
      Serial.println("ERROR:comando_desconocido");
    }
  }
}
