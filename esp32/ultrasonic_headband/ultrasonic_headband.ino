// --- PIN DEFINITIONS ---
const int trigPinL = 5;   const int echoPinL = 18;
const int trigPinC = 21;  const int echoPinC = 22; // NEW Center Pins
const int trigPinR = 19;  const int echoPinR = 23;

void setup() {
  Serial.begin(115200);
  pinMode(trigPinL, OUTPUT); pinMode(echoPinL, INPUT);
  pinMode(trigPinC, OUTPUT); pinMode(echoPinC, INPUT);
  pinMode(trigPinR, OUTPUT); pinMode(echoPinR, INPUT);
}

int readDistance(int trig, int echo) {
  digitalWrite(trig, LOW); delayMicroseconds(2);
  digitalWrite(trig, HIGH); delayMicroseconds(10);
  digitalWrite(trig, LOW);
  
  long duration = pulseIn(echo, HIGH, 30000); // 30ms timeout
  if (duration == 0) return 400; 
  return duration * 0.0343 / 2;
}

void loop() {
  // 1. Read LEFT
  int distL = readDistance(trigPinL, echoPinL);
  delay(15); // Wait for echoes to die down

  // 2. Read CENTER
  int distC = readDistance(trigPinC, echoPinC);
  delay(15);

  // 3. Read RIGHT
  int distR = readDistance(trigPinR, echoPinR);
  delay(15);

  // 4. Send: "L,C,R"
  Serial.print(distL);
  Serial.print(",");
  Serial.print(distC);
  Serial.print(",");
  Serial.println(distR);
}
