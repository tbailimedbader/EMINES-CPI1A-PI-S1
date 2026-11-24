
#include <Arduino.h>
#include <stdlib.h>

constexpr uint8_t ENC_A = 2;
constexpr uint8_t ENC_B = 3;
constexpr uint8_t PWM   = 5;
constexpr uint8_t DIR   = 7;

constexpr float REDUCTION = 30.0f;
constexpr int TICKS_PER_REV = 64;

constexpr float RAD_PER_TICK = TWO_PI / (REDUCTION * TICKS_PER_REV);
constexpr unsigned long PERIOD = 50000UL;

volatile long ticks = 0;
volatile uint8_t previous = 0;

float theta = 0.0f;
float omega = 0.0f;

int command = 0;
unsigned long lastTime = 0;


uint8_t encoderState() {
    return (digitalRead(ENC_A) << 1) | digitalRead(ENC_B);
}


void encoderISR() {
    static const int8_t LUT[] = {
         0,  1, -1,  0,
        -1,  0,  0,  1,
         1,  0,  0, -1,
         0, -1,  1,  0
    };

    uint8_t current = encoderState();

    ticks += LUT[(previous << 2) | current];
    previous = current;
}


void drive(int pwm) {
    pwm = constrain(pwm, -255, 255);

    if ((pwm < 0) != (command < 0))
        analogWrite(PWM, 0);

    digitalWrite(DIR, pwm >= 0 ? HIGH : LOW);
    analogWrite(PWM, abs(pwm));

    command = pwm;
}


void communicate() {
    static char buffer[12];
    static uint8_t index = 0;
    static bool overflow = false;

    while (Serial.available()) {
        char c = Serial.read();

        if (c == '\n' || c == '\r') {
            if (index || overflow) {
                buffer[index] = '\0';

                char* end;
                long value = strtol(buffer, &end, 10);

                if (!overflow && end != buffer && 
                    *end == '\0' && value >= -255 && value <= 255) {
                    drive(static_cast<int>(value));
                } else {
                    Serial.println(F("Invalid command"));
                }
            }

            index = 0;
            overflow = false;
        }
        else if (index < sizeof(buffer) - 1) {
            buffer[index++] = c;
        }
        else {
            overflow = true;
        }
    }
}


void measure() {
    unsigned long now = micros();
    unsigned long elapsed = now - lastTime;

    if (elapsed < PERIOD) return;

    noInterrupts();
    long delta = ticks;
    ticks = 0;
    interrupts();

    lastTime = now;

    float dTheta = delta * RAD_PER_TICK;

    theta += dTheta;
    omega = dTheta / (elapsed * 1e-6f);

    Serial.print(F("PWM:"));
    Serial.print(command);

    Serial.print(F("\tTheta:"));
    Serial.print(theta, 4);

    Serial.print(F("\tOmega:"));
    Serial.println(omega, 4);
}


void setup() {
    Serial.begin(115200);

    pinMode(PWM, OUTPUT);
    pinMode(DIR, OUTPUT);
    pinMode(ENC_A, INPUT);
    pinMode(ENC_B, INPUT);

    drive(0);

    previous = encoderState();

    attachInterrupt(digitalPinToInterrupt(ENC_A), encoderISR, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ENC_B), encoderISR, CHANGE);

    lastTime = micros();
}


void loop() {
    communicate();
    measure();
}
