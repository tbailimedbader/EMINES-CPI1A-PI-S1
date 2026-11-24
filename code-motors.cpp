
#include <Arduino.h>
#include <stdlib.h>

// ======================================================
//                    CONFIGURATION
// ======================================================

namespace Config {
    constexpr uint8_t ENCODER_A = 2;
    constexpr uint8_t ENCODER_B = 3;

    constexpr uint8_t MOTOR_PWM = 5;
    constexpr uint8_t MOTOR_DIR = 7;

    constexpr float REDUCTION = 30.0f;
    constexpr uint16_t ENCODER_TICKS = 64;

    constexpr uint32_t SAMPLE_PERIOD = 50000UL;  // µs
    constexpr uint32_t BAUD_RATE = 115200;

    constexpr float RAD_PER_TICK =
        TWO_PI / (ENCODER_TICKS * REDUCTION);
}

// ======================================================
//                 VARIABLES DU SYSTEME
// ======================================================

volatile long encoderTicks = 0;
volatile uint8_t previousState = 0;

float position = 0.0f;
float omega = 0.0f;

int motorPWM = 0;
int requestedPWM = 0;

uint32_t lastMeasurement = 0;

enum class InputState {
    PWM,
    DIRECTION
};

InputState inputState = InputState::PWM;

// ======================================================
//                  CODEUR INCREMENTAL
// ======================================================

uint8_t readEncoder() {
    return (digitalRead(Config::ENCODER_A) << 1)
         | digitalRead(Config::ENCODER_B);
}

void encoderISR() {
    static const int8_t transitions[16] = {
         0,  1, -1,  0,
        -1,  0,  0,  1,
         1,  0,  0, -1,
         0, -1,  1,  0
    };

    const uint8_t currentState = readEncoder();

    encoderTicks += transitions[
        (previousState << 2) | currentState
    ];

    previousState = currentState;
}

long readAndResetTicks() {
    noInterrupts();

    const long ticks = encoderTicks;
    encoderTicks = 0;

    interrupts();

    return ticks;
}

// ======================================================
//                   COMMANDE MOTEUR
// ======================================================

void setMotor(int pwm) {
    pwm = constrain(pwm, -255, 255);

    if ((pwm < 0) != (motorPWM < 0)) {
        analogWrite(Config::MOTOR_PWM, 0);
    }

    digitalWrite(Config::MOTOR_DIR, pwm >= 0 ? HIGH : LOW);
    analogWrite(Config::MOTOR_PWM, abs(pwm));

    motorPWM = pwm;
}

// ======================================================
//                   MESURES PHYSIQUES
// ======================================================

void updateMeasurements() {
    const uint32_t now = micros();
    const uint32_t elapsed = now - lastMeasurement;

    if (elapsed < Config::SAMPLE_PERIOD)
        return;

    const long ticks = readAndResetTicks();

    lastMeasurement = now;

    const float dt = elapsed * 1e-6f;
    const float deltaTheta = ticks * Config::RAD_PER_TICK;

    position += deltaTheta;
    omega = deltaTheta / dt;

    if (motorPWM != 0 || ticks != 0) {
        Serial.print(F("Position: "));
        Serial.print(position, 3);

        Serial.print(F(" rad | Omega: "));
        Serial.print(omega, 3);

        Serial.print(F(" rad/s | Sens: "));

        if (ticks > 0)
            Serial.println(F("Positif"));
        else if (ticks < 0)
            Serial.println(F("Negatif"));
        else
            Serial.println(F("Immobilite"));
    }
}

// ======================================================
//                  COMMUNICATION SERIE
// ======================================================

void printPrompt() {
    if (inputState == InputState::PWM)
        Serial.println(F("Entrer le PWM [0-255] :"));
    else
        Serial.println(F("Sens [1 = Horaire, 0 = Anti-horaire] :"));
}

void processInput(long value) {
    switch (inputState) {

        case InputState::PWM:

            if (value < 0 || value > 255) {
                Serial.println(F("Erreur : PWM invalide."));
                break;
            }

            requestedPWM = static_cast<int>(value);

            if (requestedPWM == 0) {
                setMotor(0);
                Serial.println(F("Moteur arrete."));
            } else {
                inputState = InputState::DIRECTION;
            }

            break;

        case InputState::DIRECTION:

            if (value != 0 && value != 1) {
                Serial.println(F("Erreur : sens invalide."));
                break;
            }

            setMotor(value == 1 ? requestedPWM : -requestedPWM);

            Serial.print(F("Commande appliquee : "));
            Serial.println(motorPWM);

            inputState = InputState::PWM;

            break;
    }

    printPrompt();
}

void handleSerial() {
    static char buffer[12];
    static uint8_t index = 0;
    static bool overflow = false;

    while (Serial.available()) {
        const char c = Serial.read();

        if (c == '\n' || c == '\r') {

            if (overflow) {
                Serial.println(F("Erreur : saisie trop longue."));
                printPrompt();
            }
            else if (index > 0) {
                buffer[index] = '\0';

                char* end;
                const long value = strtol(buffer, &end, 10);

                if (end != buffer && *end == '\0')
                    processInput(value);
                else {
                    Serial.println(F("Erreur : saisie invalide."));
                    printPrompt();
                }
            }

            index = 0;
            overflow = false;
        }
        else if (!overflow) {
            if (index < sizeof(buffer) - 1)
                buffer[index++] = c;
            else
                overflow = true;
        }
    }
}

// ======================================================
//                      INITIALISATION
// ======================================================

void setup() {
    Serial.begin(Config::BAUD_RATE);

    pinMode(Config::MOTOR_PWM, OUTPUT);
    pinMode(Config::MOTOR_DIR, OUTPUT);

    pinMode(Config::ENCODER_A, INPUT);
    pinMode(Config::ENCODER_B, INPUT);

    setMotor(0);

    previousState = readEncoder();

    attachInterrupt(
        digitalPinToInterrupt(Config::ENCODER_A),
        encoderISR,
        CHANGE
    );

    attachInterrupt(
        digitalPinToInterrupt(Config::ENCODER_B),
        encoderISR,
        CHANGE
    );

    lastMeasurement = micros();

    Serial.println(F("================================"));
    Serial.println(F("       DC MOTOR CONTROLLER"));
    Serial.println(F("================================"));

    printPrompt();
}

// ======================================================
//                    BOUCLE PRINCIPALE
// ======================================================

void loop() {
    handleSerial();
    updateMeasurements();
}
