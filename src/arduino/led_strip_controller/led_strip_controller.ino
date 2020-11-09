/* Controls an RGB LED strip. */

const int RED_PIN   = 8;
const int GREEN_PIN = 7;
const int BLUE_PIN  = 9;
const char ACK = 'K';

void setup() {
  Serial.begin(115200);
}

void loop() {
  // Wait for serial to be available
  while (!Serial.available());

  set_led(RED_PIN);
  set_led(GREEN_PIN);
  set_led(BLUE_PIN);

  // Send ACK to computer
  while (!Serial.availableForWrite());
  Serial.write(ACK);
}

void set_led(const int led_pin) {
  const int value = min(max(0, Serial.parseInt()), 255);
  Serial.read();
  analogWrite(led_pin, value);
}
