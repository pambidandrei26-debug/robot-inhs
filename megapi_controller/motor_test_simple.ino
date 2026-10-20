/*
 * MOTOR DIAGNOSTIC TEST
 * Tests each motor individually to find which one is not working
 * Upload this, open Serial Monitor (115200 baud)
 */

#include <MeMegaPi.h>

MeMegaPiDCMotor motorLeft(PORT1B);   // Left wheel on M1
MeMegaPiDCMotor motorRight(PORT2B);  // Right wheel on M2

void testMotor(String name, MeMegaPiDCMotor &motor, int speed, int duration) {
  Serial.print(">>> ");
  Serial.print(name);
  Serial.print(" at speed ");
  Serial.print(speed);
  Serial.println(" - watch which wheel moves!");
  delay(2000);
  motor.run(speed);
  delay(duration);
  motor.stop();
  delay(2000);
  Serial.println("    Done.");
}

void setup() {
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("========================================");
  Serial.println("INDIVIDUAL MOTOR DIAGNOSTIC TEST");
  Serial.println("========================================");
  Serial.println("Watch which wheel moves for each test!");
  Serial.println();
  delay(3000);

  // ── TEST LEFT MOTOR ONLY ─────────────────────────────
  Serial.println("=== LEFT MOTOR (PORT1B) TESTS ===");
  
  testMotor("LEFT motor (+100)", motorLeft, 100, 2000);
  testMotor("LEFT motor (-100)", motorLeft, -100, 2000);

  // ── TEST RIGHT MOTOR ONLY ────────────────────────────
  Serial.println("=== RIGHT MOTOR (PORT2B) TESTS ===");
  
  testMotor("RIGHT motor (+100)", motorRight, 100, 2000);
  testMotor("RIGHT motor (-100)", motorRight, -100, 2000);

  // ── SUMMARY ──────────────────────────────────────────
  Serial.println("========================================");
  Serial.println("RESULTS - Report back:");
  Serial.println("1. LEFT (+100): which wheel? which direction?");
  Serial.println("2. LEFT (-100): which wheel? which direction?");
  Serial.println("3. RIGHT (+100): which wheel? which direction?");
  Serial.println("4. RIGHT (-100): which wheel? which direction?");
  Serial.println("========================================");
  Serial.println("If a motor did NOT move = hardware issue!");
  Serial.println("Check wire connection on MegaPi board.");
}

void loop() {
  // Empty
}
