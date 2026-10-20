/*
 * MegaPi Serial Motor Controller with Arm, Claw, and Ultrasonic Sensor
 * For Autonomous Wall Crack Detection Robot
 * 
 * Receives commands from Raspberry Pi via USB Serial
 * Controls motors connected to MegaPi M1-M4 ports
 * Reads ultrasonic sensor distance
 * 
 * Motor Configuration:
 * M1 (PORT1B) - Left wheel motor
 * M2 (PORT2B) - Right wheel motor
 * M3 (PORT3B) - Arm motor (up/down)
 * M4 (PORT4B) - Claw motor (open/close)
 * 
 * Sensor Configuration:
 * PORT_6 - Ultrasonic sensor (Makeblock Me Ultrasonic)
 *          Connect via RJ25 port
 * 
 * Wheel Commands:
 * F,speed,duration - Move forward at speed for duration ms
 * B,speed,duration - Move backward at speed for duration ms
 * L,speed,duration - Turn left at speed for duration ms
 * R,speed,duration - Turn right at speed for duration ms
 * S - Stop all wheel motors
 * 
 * Arm Commands:
 * U - Arm up fully
 * D - Arm down fully
 * M - Arm to middle
 * AS - Stop arm motor
 * 
 * Claw Commands:
 * O - Open claw fully
 * X - Close claw fully
 * C - Claw to middle
 * CS - Stop claw motor
 * 
 * Ultrasonic Commands:
 * G - Get distance from ultrasonic sensor (returns DISTANCE:XX.XX)
 * 
 * Example: "F,80,1000" = Forward at speed 80 for 1000ms (1 second)
 * Example: "U" = Raise arm fully
 * Example: "O" = Open claw fully
 * Example: "G" = Get current distance reading
 */

#include <MeMegaPi.h>

// Motor definitions
MeMegaPiDCMotor motorLeft(PORT1B);    // Left wheel on M1
MeMegaPiDCMotor motorRight(PORT2B);   // Right wheel on M2
MeMegaPiDCMotor motorArm(PORT3B);     // Arm motor on M3
MeMegaPiDCMotor motorClaw(PORT4B);    // Claw motor on M4

// Ultrasonic sensor definition
MeUltrasonicSensor ultrasonic(PORT_6);

// Speed compensation to fix drift (adjust if robot doesn't go straight)
const float LEFT_SPEED_FACTOR = 1.0;   // Adjust if robot drifts
const float RIGHT_SPEED_FACTOR = 1.0;  // Adjust if robot drifts

// Arm and claw speeds
const int ARM_SPEED = 100;   // Adjust based on your arm motor
const int CLAW_SPEED = 100;  // Adjust based on your claw motor

// Predefined durations for arm/claw movements (in milliseconds)
const int ARM_FULL_DURATION = 2500;    // Time to move arm fully up/down
const int ARM_HALF_DURATION = 1250;    // Time to move arm to middle
const int CLAW_FULL_DURATION = 3000;   // Time to fully open/close claw
const int CLAW_HALF_DURATION = 1500;   // Time to half open/close claw

// Motor speed limits
const int MAX_SPEED = 255;
const int MIN_SPEED = 0;

// Command buffer
String commandBuffer = "";
boolean commandComplete = false;

void setup() {
  // Initialize serial communication with Raspberry Pi
  Serial.begin(115200);
  
  // Stop all motors on startup
  stopMotors();
  
  // Send ready signal
  Serial.println("MegaPi Ready - 2 Wheels + Arm + Claw + Ultrasonic");
  
  // Reserve buffer space
  commandBuffer.reserve(50);
}

void loop() {
  // Process incoming serial commands
  if (commandComplete) {
    processCommand(commandBuffer);
    commandBuffer = "";
    commandComplete = false;
  }
}

// Serial event handler - called when data arrives
void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    
    if (inChar == '\n') {
      commandComplete = true;
    } else {
      commandBuffer += inChar;
    }
  }
}

// Process received command
void processCommand(String command) {
  command.trim();
  command.toUpperCase();  // Convert entire command to uppercase
  
  // Check for single-letter commands first (no parameters)
  if (command == "S") {
    stopMotors();
    Serial.println("OK:STOP");
    return;
  }
  else if (command == "U") {
    armUpFull();
    return;
  }
  else if (command == "D") {
    armDownFull();
    return;
  }
  else if (command == "M") {
    armMiddle();
    return;
  }
  else if (command == "O") {
    openClawFull();
    return;
  }
  else if (command == "X") {
    closeClawFull();
    return;
  }
  else if (command == "C") {
    clawMiddle();
    return;
  }
  else if (command == "AS") {
    stopArm();
    return;
  }
  else if (command == "CS") {
    stopClaw();
    return;
  }
  else if (command == "G") {
    reportDistance();
    return;
  }
  
  // Parse commands with parameters: "CMD,param1,param2"
  int firstComma = command.indexOf(',');
  int secondComma = command.indexOf(',', firstComma + 1);
  
  if (firstComma < 0) {
    Serial.println("ERROR:UNKNOWN_COMMAND");
    return;
  }
  
  String cmd = command.substring(0, firstComma);
  cmd.trim();
  
  int speed = 150;  // Default speed
  int duration = 0; // Duration in milliseconds
  
  // Parse parameters
  if (secondComma > 0) {
    speed = command.substring(firstComma + 1, secondComma).toInt();
    duration = command.substring(secondComma + 1).toInt();
  } else {
    speed = command.substring(firstComma + 1).toInt();
  }
  
  // Constrain speed to valid range
  speed = constrain(speed, MIN_SPEED, MAX_SPEED);
  
  // Execute command with parameters
  if (cmd == "F") {
    moveForward(speed, duration);
  } 
  else if (cmd == "B") {
    moveBackward(speed, duration);
  } 
  else if (cmd == "L") {
    turnLeft(speed, duration);
  } 
  else if (cmd == "R") {
    turnRight(speed, duration);
  } 
  else {
    Serial.println("ERROR:UNKNOWN_COMMAND");
  }
}

// Motor control functions - 2-wheel differential drive
void moveForward(int speed, int duration) {
  // Apply speed compensation
  int leftSpeed = int(speed * LEFT_SPEED_FACTOR);
  int rightSpeed = int(speed * RIGHT_SPEED_FACTOR);
  
  // Both wheels forward - SWAPPED (was backwards)
  motorLeft.run(-leftSpeed);      // Negative for forward
  motorRight.run(rightSpeed);     // Positive for forward
  
  Serial.print("OK:FORWARD:");
  Serial.print(speed);
  Serial.print(":");
  Serial.println(duration);
  
  if (duration > 0) {
    // Move forward with obstacle detection
    unsigned long startTime = millis();
    while (millis() - startTime < duration) {
      // Check for obstacles every 100ms
      if (millis() - startTime > 100) {
        float distance = ultrasonic.distanceCm();
        if (distance > 0 && distance < 25.0) {  // Increased from 15cm to 25cm
          // Too close! Emergency stop
          stopMotors();
          Serial.println("WARN:OBSTACLE_DETECTED");
          return;
        }
      }
      delay(10);
    }
    stopMotors();
  }
}

void moveBackward(int speed, int duration) {
  // Both wheels backward - SWAPPED (was forwards)
  motorLeft.run(speed);        // Positive for backward
  motorRight.run(-speed);      // Negative for backward
  
  Serial.print("OK:BACKWARD:");
  Serial.print(speed);
  Serial.print(":");
  Serial.println(duration);
  
  if (duration > 0) {
    delay(duration);
    stopMotors();
  }
}

void turnLeft(int speed, int duration) {
  // Pivot LEFT: left forward (-), right backward (-) = both negative
  int leftSpeed  = int(speed * LEFT_SPEED_FACTOR);
  int rightSpeed = int(speed * RIGHT_SPEED_FACTOR);
  
  motorLeft.run(-leftSpeed);    // LEFT FORWARD (-)
  motorRight.run(-rightSpeed);  // RIGHT BACKWARD (-)
  
  Serial.print("OK:LEFT:");
  Serial.print(speed);
  Serial.print(":");
  Serial.println(duration);
  
  if (duration > 0) {
    delay(duration);
    stopMotors();
  }
}

void turnRight(int speed, int duration) {
  // Pivot RIGHT: left backward (+), right forward (+) = both positive
  int leftSpeed  = int(speed * LEFT_SPEED_FACTOR);
  int rightSpeed = int(speed * RIGHT_SPEED_FACTOR);
  
  motorLeft.run(leftSpeed);     // LEFT BACKWARD (+)
  motorRight.run(rightSpeed);   // RIGHT FORWARD (+)
  
  Serial.print("OK:RIGHT:");
  Serial.print(speed);
  Serial.print(":");
  Serial.println(duration);
  
  if (duration > 0) {
    delay(duration);
    stopMotors();
  }
}

void stopMotors() {
  motorLeft.stop();
  motorRight.stop();
}

void stopArm() {
  motorArm.stop();
  Serial.println("OK:ARM_STOP");
}

void stopClaw() {
  motorClaw.stop();
  Serial.println("OK:CLAW_STOP");
}

// Arm motor control functions
void armUpFull() {
  Serial.println("OK:ARM_UP_FULL");
  motorArm.run(ARM_SPEED);
  delay(ARM_FULL_DURATION);
  motorArm.stop();
}

void armDownFull() {
  Serial.println("OK:ARM_DOWN_FULL");
  motorArm.run(-ARM_SPEED);
  delay(ARM_FULL_DURATION);
  motorArm.stop();
}

void armMiddle() {
  Serial.println("OK:ARM_MIDDLE");
  // Assume starting from bottom, go up halfway
  motorArm.run(ARM_SPEED);
  delay(ARM_HALF_DURATION);
  motorArm.stop();
}

// Claw motor control functions
void openClawFull() {
  Serial.println("OK:CLAW_OPEN_FULL");
  motorClaw.run(-CLAW_SPEED);  // Negative = open (adjust if wrong direction)
  delay(CLAW_FULL_DURATION);
  motorClaw.stop();
}

void closeClawFull() {
  Serial.println("OK:CLAW_CLOSE_FULL");
  motorClaw.run(CLAW_SPEED);   // Positive = close
  delay(CLAW_FULL_DURATION);
  motorClaw.stop();
}

void clawMiddle() {
  Serial.println("OK:CLAW_MIDDLE");
  // Assume starting from closed, open halfway
  motorClaw.run(-CLAW_SPEED);
  delay(CLAW_HALF_DURATION);
  motorClaw.stop();
}

// Ultrasonic sensor functions - Enhanced with extended range and better handling
void reportDistance() {
  const int NUM_READINGS = 5;  // Take 5 readings
  const int MAX_RETRIES = 3;   // Retry up to 3 times if all readings fail
  float readings[NUM_READINGS];
  int validReadings = 0;
  
  // Try multiple times if needed
  for (int retry = 0; retry < MAX_RETRIES && validReadings == 0; retry++) {
    validReadings = 0;
    
    // Take multiple readings
    for (int i = 0; i < NUM_READINGS; i++) {
      delay(60);  // Wait between readings
      float distance = ultrasonic.distanceCm();
      
      // Accept wider range: 2cm to 500cm (extended from 400)
      // This allows for farther detection
      if (distance > 2.0 && distance <= 500.0) {
        readings[validReadings] = distance;
        validReadings++;
      } else if (distance > 500.0) {
        // If reading is beyond 500cm, treat it as max range
        readings[validReadings] = 500.0;
        validReadings++;
      }
    }
    
    // If no valid readings, wait before retry
    if (validReadings == 0 && retry < MAX_RETRIES - 1) {
      delay(150);
    }
  }
  
  // If we got at least one valid reading
  if (validReadings > 0) {
    // Calculate median (more robust than average)
    float finalDistance = calculateMedian(readings, validReadings);
    
    Serial.print("DISTANCE:");
    Serial.println(finalDistance, 2);  // 2 decimal places
  } else {
    // All readings failed - report as very far (999cm = no object detected)
    // This is better than ERROR - robot can still navigate
    Serial.println("DISTANCE:999.00");
  }
}

// Helper function to calculate median
float calculateMedian(float arr[], int n) {
  // Simple bubble sort
  for (int i = 0; i < n - 1; i++) {
    for (int j = 0; j < n - i - 1; j++) {
      if (arr[j] > arr[j + 1]) {
        float temp = arr[j];
        arr[j] = arr[j + 1];
        arr[j + 1] = temp;
      }
    }
  }
  
  // Return median value
  if (n % 2 == 0) {
    return (arr[n / 2 - 1] + arr[n / 2]) / 2.0;
  } else {
    return arr[n / 2];
  }
}
