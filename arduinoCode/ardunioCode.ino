#include <HX711.h>
#include <MobaTools.h>

// ## Define pin numbers

// Actuator pins
const int STEP_PIN_1 = 3;
const int DIR_PIN_1 = 4;
const int STEP_PIN_2 = 5;
const int DIR_PIN_2 = 6;
const int LOAD_CELL_DOUT_PIN = 10;
const int LOAD_CELL_SCK_PIN = 11;
const int MS1_PIN = 7;
const int MS2_PIN = 8;
const int MS3_PIN = 9;
// RoM pins
const int STEP_PIN_3 = 12;
const int DIR_PIN_3 = 13;

// ##

// Load cell calibration factor
const float CALIBRATION_FACTOR = -2350.0;

// ####################### EDIT THIS SECTION TO SET FORCES, ANGLES AND HOLD TIME #######################

// Target forces in Newtons
float MIN_TARGET_FORCE = 1.0;
float MAX_TARGET_FORCE = 10.0;

// Hold time in milliseconds
int HOLD_TIME_MIN = 1000;
int HOLD_TIME_MAX = 1000;

// Initialise loop functions
static bool findingMinForce = true;
static bool findingMaxForce = false;
static bool returntoMinForce = false;
static bool RampingUp = false;
static bool RampingDown = false;
static bool HoldingMax = false;
static bool HoldingMin = false;
static bool RomUp = false;
static bool RomDown = false;
//Initialise loop function saving variables
static bool findingMinForceSAVE = findingMinForce;
static bool findingMaxForceSAVE = findingMaxForce;
static bool returntoMinForceSAVE = returntoMinForce;
static bool RampingUpSAVE = RampingUp;
static bool RampingDownSAVE = RampingDown;
static bool HoldingMaxSAVE = HoldingMax;
static bool HoldingMinSAVE = HoldingMin;
static bool RomUpSAVE = RomUp;
static bool RomDownSAVE = RomDown;
//STATE INITIALISATION
static bool STOPPED = false;
static bool paused = false;
static bool wordCOMMAND = false;


// RoM in steps: 200 steps = 360deg
int StartAngle = 0;
int EndAngle = 50;

int cycle_count = 0;

const int debug = 0; //0=false, 1 = true

// #####################################################################################################
// if (debug == 0) {
  // Create instances for HX711
  HX711 loadCell;

  // Create Motor instances
  MoToStepper stepper1(1600 , STEPDIR);
  MoToStepper stepper2(1600 , STEPDIR);
  MoToStepper stepper3(800 , STEPDIR); // RoM motor
// }
void setup() {
  Serial.begin(115200);
  Serial.println("Serial begin");
  if ((debug == 1)||(debug == 0)) {
    // Setup microstepping pins for 1/8 microstepping
    Serial.println(" debug false ");
    pinMode(MS1_PIN, OUTPUT);
    pinMode(MS2_PIN, OUTPUT);
    pinMode(MS3_PIN, OUTPUT);
    digitalWrite(MS1_PIN, HIGH);
    digitalWrite(MS2_PIN, HIGH);
    digitalWrite(MS3_PIN, LOW);

    // Setup load cell
    loadCell.begin(LOAD_CELL_DOUT_PIN, LOAD_CELL_SCK_PIN);
    loadCell.set_scale(CALIBRATION_FACTOR);
    loadCell.tare();

    // Setup actuators
    stepper1.attach(STEP_PIN_1, DIR_PIN_1);
    stepper2.attach(STEP_PIN_2, DIR_PIN_2);
    stepper1.setSpeedSteps(5000); //4000
    stepper2.setSpeedSteps(5000); //4000
    stepper1.setRampLen(10); //50
    stepper2.setRampLen(10); //50
    stepper1.setZero();
    stepper2.setZero();
    // sertup RoM motor
    stepper3.attach(STEP_PIN_3, DIR_PIN_3);
    stepper3.setSpeedSteps(1000); //1500
    stepper3.setRampLen(50); //50
    stepper3.setZero();

    // Allow voltage levels to settle
    delay(5000);
  }
}

void loop() {
  SerChecker();

  // Create stepper position variables
  static long stepper1Position = 0;
  static long stepper2Position = 0;
  static float currentForce = 0.0;
  static long minForcePos1 = 0;
  static long minForcePos2 = 0;
  static long maxForcePos1 = 0;
  static long maxForcePos2 = 0;

  if ((findingMinForce) || (findingMaxForce) || (returntoMinForce)) {
  // Initial Force Position Point Finding.
    if (debug == 0) {
      // find minimum force location
      if (findingMinForce) {
        stepper1.move(1);
        stepper2.move(1);
        stepper1Position += 1;
        stepper2Position += 1; //ATTENTION positive? ***********************************************
        currentForce = -loadCell.get_units();
        Serial.print("Current force: ");
        Serial.print(currentForce);
        Serial.println(" N");
        SerChecker();
        if (currentForce >= MIN_TARGET_FORCE) {
          Serial.println("Target force reached. Stopping actuators.");
          Serial.print("Stepper 1 position: ");
          Serial.println(stepper1Position);
          Serial.print("Stepper 2 position: ");
          Serial.println(stepper2Position);
          // minForcePos1 = stepper1Position;
          // minForcePos2 = stepper2Position;
          minForcePos1 = stepper1.readSteps();
          minForcePos2 = stepper2.readSteps();
          findingMinForce = false;
          findingMaxForce = true;
        }
      }

      // Find maximum force location
      else if (findingMaxForce){
        stepper1.move(1);
        stepper2.move(1);
        stepper1Position += 1;
        stepper2Position += 1; //ATTENTION positive? ***********************************************
        currentForce = -loadCell.get_units();
        Serial.print("Current force: ");
        Serial.print(currentForce);
        Serial.println(" N");
        SerChecker();

        if (currentForce >= MAX_TARGET_FORCE) {
          Serial.println("Target force of reached. Stopping actuators.");
          Serial.print("Stepper 1 position: ");
          Serial.println(stepper1Position);
          Serial.print("Stepper 2 position: ");
          Serial.println(stepper2Position);
          // maxForcePos1 = stepper1Position;
          // maxForcePos2 = stepper2Position;
          maxForcePos1 = stepper1.readSteps();
          maxForcePos2 = stepper2.readSteps();
          findingMaxForce = false;
          returntoMinForce = true;
        }
      }

      // Move actuators back to min location for start of testing
      // else if (returntoMinForce){
      //     stepper1.moveTo(minForcePos1);
      //     stepper2.moveTo(minForcePos2);
      //     while (stepper1.moving() || stepper2.moving());
      //     Serial.println("Returned to min force");
      //     returntoMinForce = false;
      //     RomUp = true;
      // }
      else if (returntoMinForce){
        stepper1.moveTo(minForcePos1);
        stepper2.moveTo(minForcePos2);
        while (stepper1.moving() || stepper2.moving());
        currentForce = -loadCell.get_units();
        SerChecker();

        if (currentForce >= MIN_TARGET_FORCE){
          while (currentForce >= MIN_TARGET_FORCE){
            stepper1.move(-1);
            stepper2.move(-1);//ATTENTION negative? ***********************************************
            minForcePos1 -= 1;
            minForcePos2 -= 1;//ATTENTION negative? ***********************************************
            currentForce = -loadCell.get_units();
          }
          Serial.print("Returned to min force: ");
          Serial.println(currentForce);
          returntoMinForce = false;
          RomUp = true;
        }

        else if (currentForce <= MIN_TARGET_FORCE){
          while (currentForce <= MIN_TARGET_FORCE){
            stepper1.move(1);
            stepper2.move(1);//ATTENTION positive? ***********************************************
            minForcePos1 += 1;
            minForcePos2 += 1;//ATTENTION positive? ***********************************************
            currentForce = -loadCell.get_units();
          }
          Serial.print("Returned to min force: ");
          Serial.println(currentForce);
          returntoMinForce = false;
          RomUp = true;
        }
      }
    }
    if (debug == 1) {
      RomUp = true;
      Serial.println("debug true");
    }
  }
  SerChecker();
  // Rotate the joint the required angle
  if (RomUp) {
    if (debug == 0) {
      stepper3.moveTo(EndAngle);
      stepper3.moving(); // try changing/was to/was while (stepper3.moving())
    }
    Serial.print("RoM up: ");
    Serial.println(EndAngle); //was Serial.println("EndAngle");
    RomUp = false;
    RampingUp = true;
  }
  SerChecker();
  // Increase the force to the set level
  if (RampingUp){
    if (debug == 0) {
      stepper1.moveTo(maxForcePos1 - 5);
      stepper2.moveTo(maxForcePos2 - 5);
      while (stepper1.moving() || stepper2.moving());
      currentForce = -loadCell.get_units();

      if (currentForce >= MAX_TARGET_FORCE){
        while (currentForce >= MAX_TARGET_FORCE){
          stepper1.move(-1);
          stepper2.move(-1);//ATTENTION negative? ***********************************************
          maxForcePos1 -= 1;
          maxForcePos2 -= 1;//ATTENTION negative? ***********************************************
          currentForce = -loadCell.get_units();
        }
        Serial.print("Max force during ramp up: ");
        Serial.println(currentForce);
        Serial.print("Target force: ");
        Serial.println(MAX_TARGET_FORCE);
        RampingUp = false;
        HoldingMax = true;
      }

      else if (currentForce <= MAX_TARGET_FORCE){
        while (currentForce <= MAX_TARGET_FORCE){
          stepper1.move(1);
          stepper2.move(1);//ATTENTION positve? ***********************************************
          maxForcePos1 += 1;
          maxForcePos2 += 1;//ATTENTION positve? ***********************************************
          currentForce = -loadCell.get_units();
        }
        Serial.print("Max force during ramp up: ");
        Serial.println(currentForce);
        Serial.print("Target force: ");
        Serial.println(MAX_TARGET_FORCE);
        RampingUp = false;
        HoldingMax = true;
      }
    }
    if (debug == 1) {
      currentForce = MAX_TARGET_FORCE;
      Serial.print("Max force during ramp up: ");
      Serial.println(currentForce);
      Serial.print("Target force: ");
      Serial.println(MAX_TARGET_FORCE);
      RampingUp = false;
      HoldingMax = true;
    }
  }
  SerChecker();
  // Hold at Max Force
  if (HoldingMax){
    Serial.print("HoldingStart: ");
    Serial.println(HOLD_TIME_MAX);
    delay(HOLD_TIME_MAX);
    Serial.println("HoldingFinished.");
    HoldingMax = false;
    RampingDown = true;
  }
  SerChecker();
  // Reduce the force to the min set level
  if (RampingDown){
    if (debug == 0) {
      stepper1.moveTo(minForcePos1 + 5);
      stepper2.moveTo(minForcePos2 + 5);
      while (stepper1.moving() || stepper2.moving());
      currentForce = -loadCell.get_units();

      if (currentForce >= MIN_TARGET_FORCE){
        while (currentForce >= MIN_TARGET_FORCE){
          stepper1.move(-1);
          stepper2.move(-1);//ATTENTION negative? ***********************************************
          minForcePos1 -= 1;
          minForcePos2 -= 1;//ATTENTION negative? ***********************************************
          currentForce = -loadCell.get_units();
        }
        Serial.print("Min force during ramp down: ");
        Serial.println(currentForce);
        Serial.print("Target force: ");
        Serial.println(MIN_TARGET_FORCE);
        RampingDown = false;
        HoldingMin = true;
      }

      else if (currentForce <= MIN_TARGET_FORCE){
        while (currentForce <= MIN_TARGET_FORCE){
          stepper1.move(1);
          stepper2.move(1);//ATTENTION positve? ***********************************************
          minForcePos1 += 1;
          minForcePos2 += 1;//ATTENTION positve? ***********************************************
          currentForce = -loadCell.get_units();
        }
        Serial.print("Min force during ramp down: ");
        Serial.println(currentForce);
        Serial.print("Target force: ");
        Serial.println(MIN_TARGET_FORCE);
        RampingDown = false;
        HoldingMin = true;
      }
    }
    if (debug == 1) {
      currentForce = MIN_TARGET_FORCE;
      Serial.print("Min force during ramp down: ");
      Serial.println(currentForce);
      Serial.print("Target force: ");
      Serial.println(MIN_TARGET_FORCE);
      RampingDown = false;
      RomDown = true;
    }
  }
  SerChecker();
  // Rotate the joint back to initial angle
  if (RomDown) {
    if (debug == 0) {
      stepper3.moveTo(StartAngle);
      stepper3.moving();// was while (stepper3.moving());
    }
    Serial.print("RoM down: ");
    Serial.println(StartAngle);
    RomDown = false;
    HoldingMin = true;
  }
  SerChecker();
  // Hold at angle and min force for set time
  if (HoldingMin){
    Serial.print("HoldingStart: ");
    Serial.println(HOLD_TIME_MIN);
    delay(HOLD_TIME_MIN);
    Serial.println("HoldingFinsihed.");
    HoldingMin = false;
    RomUp = true;
    cycle_count += 1;
    Serial.print("Cycle count: ");
    Serial.println(cycle_count);
    // if (cycle_count >= 10) {
    //     Serial.println("Test complete.");
    //     cycle_count = 0; // Reset the cycle count for the next test
    // }
  }

}

void processInput(const char* input) {
  static float currentForce = 0.0; // ************* FOR USE WITHIN THIS SCOPE


  // Process the received string
  Serial.print("Received: ");
  Serial.println(input);

  // String wordIn = "NeW";

  // // sscanf(input, "%s", &wordIn);
  // wordIn = String(input);
  // wordIn = wordIn.trim();
  String myString = String(input);


  if (myString.equals("stop")) {
    findingMinForce = false;
    findingMaxForce = false;
    returntoMinForce = false;
    RampingUp = false;
    RampingDown = false;
    HoldingMax = false;
    HoldingMin = false;
    RomUp = false;
    RomDown = false;

    STOPPED = true;
    wordCOMMAND = true;
    Serial.println("stopped");
  } else if (myString.equals("pause")) {
    findingMinForceSAVE = findingMinForce;
    findingMaxForceSAVE = findingMaxForce;
    returntoMinForceSAVE = returntoMinForce;
    RampingUpSAVE = RampingUp;
    RampingDownSAVE = RampingDown;
    HoldingMaxSAVE = HoldingMax;
    HoldingMinSAVE = HoldingMin;
    RomUpSAVE = RomUp;
    RomDownSAVE = RomDown;

    findingMinForce = false;
    findingMaxForce = false;
    returntoMinForce = false;
    RampingUp = false;
    RampingDown = false;
    HoldingMax = false;
    HoldingMin = false;
    RomUp = false;
    RomDown = false;

    paused = true;

    wordCOMMAND = true;
    Serial.println("paused");
  } else if (myString.equals("resume")) {
    if (paused) {
      findingMinForce = findingMinForceSAVE;
      findingMaxForce = findingMaxForceSAVE;
      returntoMinForce = returntoMinForceSAVE;
      RampingUp = RampingUpSAVE;
      RampingDown = RampingDownSAVE;
      HoldingMax = HoldingMaxSAVE;
      HoldingMin = HoldingMinSAVE;
      RomUp = RomUpSAVE;
      RomDown = RomDownSAVE;
    } else {
      RampingUp = true;
    }
    Serial.println("resumed");
    paused = false;

    wordCOMMAND = true;
  } else if (myString.equals("moveUp")) {
    findingMinForce = false;
    findingMaxForce = false;
    returntoMinForce = false;
    RampingUp = false;
    RampingDown = false;
    HoldingMax = false;
    HoldingMin = false;
    RomUp = false;
    RomDown = false;

    stepper1.move(-400);
    stepper2.move(-400);
    Serial.println("movedUp 400");
    wordCOMMAND = true;
  } else if (myString.equals("moveDown")) {
    findingMinForce = false;
    findingMaxForce = false;
    returntoMinForce = false;
    RampingUp = false;
    RampingDown = false;
    HoldingMax = false;
    HoldingMin = false;
    RomUp = false;
    RomDown = false;

    if (debug == 0) {
      currentForce = -loadCell.get_units();
      if (currentForce > 200) {
        Serial.print("move Down Attempted, Force: ");
        Serial.println(currentForce);
      } else {
        stepper1.move(400);
        stepper2.move(400);
      Serial.println("movedDown 400");
      }
    }
    if (debug == 1) {
      stepper1.move(400);
      stepper2.move(400);
      Serial.println("movedDown 400");
    }
    wordCOMMAND = true;
  } else if (wordCOMMAND != true) {
    if (STOPPED) {
      STOPPED = false;
      RampingUp = true;
    }
    cycle_count = 0; // Reset the cycle count for the next test

    int floatValue1;
    int floatValue2;
    int floatValue3;
    int floatValue4;
    int intValue1;
    int intValue2;

    // Parse the input string and update variables
    sscanf(input, "%d %d %d %d %d %d", &floatValue1, &floatValue2, &floatValue3, &floatValue4, &intValue1, &intValue2);
    MIN_TARGET_FORCE = floatValue1;
    MAX_TARGET_FORCE = floatValue2;
    HOLD_TIME_MIN = floatValue3;
    HOLD_TIME_MAX = floatValue4;
    StartAngle = intValue1;
    EndAngle = intValue2;

    // Print updated values for verification
    Serial.println("###");
    Serial.print("MIN_TARGET_FORCE: ");
    Serial.println(MIN_TARGET_FORCE);
    Serial.print("MAX_TARGET_FORCE: ");
    Serial.println(MAX_TARGET_FORCE);
    Serial.print("HOLD_TIME_MIN: ");
    Serial.println(HOLD_TIME_MIN);
    Serial.print("HOLD_TIME_MAX: ");
    Serial.println(HOLD_TIME_MAX);
    Serial.print("StartAngle: ");
    Serial.println(StartAngle);
    Serial.print("EndAngle: ");
    Serial.println(EndAngle);
  }
  wordCOMMAND = false;
}

void SerChecker() {
  // Buffer to store incoming serial data
  static char inputBuffer[100];
  static byte bufferIndex = 0;
  // Check if data is available on the serial port
  while (Serial.available() > 0) {
    char incomingByte = Serial.read();

    // Check for end of line character
    if (incomingByte == '\n') {
      inputBuffer[bufferIndex] = '\0'; // Null-terminate the string
      if (inputBuffer[0] == '\xf0') {
        inputBuffer [100]= inputBuffer +1;
          if (inputBuffer[0] == '\xf0') {
            inputBuffer [100]= inputBuffer +1;
            if (inputBuffer[0] == '\xf0') {
              inputBuffer [100]= inputBuffer +1;
            }
            else {
              Serial.println(inputBuffer);
            }
          }
          else {
            Serial.println(inputBuffer);
          }
        Serial.println(inputBuffer);
      }
      else {
        Serial.println(inputBuffer);
      }
      processInput(inputBuffer); // Process the received string
      bufferIndex = 0; // Reset the buffer index for the next input
      Serial.println("###");
    } else {
      // Store the incoming byte in the buffer
      if (bufferIndex < sizeof(inputBuffer) - 1) {
        inputBuffer[bufferIndex++] = incomingByte;
      }
    }
  }
}