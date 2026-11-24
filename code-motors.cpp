#include <digitalWriteFast.h>
#include <FlexiTimer2.h>

// Broches du codeur incrémental
#define codeurPinA 2
#define codeurPinB 3

// Broches de commande du moteur
#define pinPwm 5
#define pinDir 7

// Paramètres mécaniques et codeur (64 ticks/tour en quadrature x4 = 16 PPR)
const float reduction = 30.0;
const int TICKS_PAR_TOUR_CODEUR = 64;
const float RAD_PAR_TICK = (2.0 * PI) / (TICKS_PAR_TOUR_CODEUR * reduction);

// Variables de mesure
float omega = 0.0;       // Vitesse angulaire en rad/s
float position = 0.0;    // Position angulaire en rad

// Commande moteur (-255 à 255)
int pwmValeur = 0;

// Machine à états pour la communication série
enum SerialState { WAITING_PWM, WAITING_DIR };
SerialState serialState = WAITING_PWM;
int saisiPwm = 0;

// Compteur d'impulsions et base de temps
volatile long ticksCodeur = 0;
#define delta_time_ms 50
const float delta_time_s = delta_time_ms / 1000.0;
volatile bool mesureDemandee = false;

// Prototypes
void declencherMesure();
void GestionInterruptionCodeurPinA();
void GestionInterruptionCodeurPinB();
void commandeVitesse(int pwm_mot);

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(20); // Évite un blocage de 1s si "Pas de fin de ligne" est sélectionné

  pinMode(pinPwm, OUTPUT);
  pinMode(pinDir, OUTPUT);
  pinMode(codeurPinA, INPUT);
  pinMode(codeurPinB, INPUT);

  // Arrêt initial garanti
  commandeVitesse(0);

  attachInterrupt(digitalPinToInterrupt(codeurPinA), GestionInterruptionCodeurPinA, CHANGE);
  attachInterrupt(digitalPinToInterrupt(codeurPinB), GestionInterruptionCodeurPinB, CHANGE);

  FlexiTimer2::set(delta_time_ms, declencherMesure);
  FlexiTimer2::start();

  Serial.println("=========================================");
  Serial.println("   CONTROLE MOTEUR - CODEUR INCREMENTAL  ");
  Serial.println("=========================================");
  Serial.println("Entrer la valeur du PWM (entre 0 et 255) :");
}

void loop() {
  // 1. Gestion robuste de la saisie série
  if (Serial.available() > 0) {
    String ligne = Serial.readStringUntil('\n');
    ligne.trim(); // Supprime \r, \n et espaces

    if (ligne.length() > 0) {
      if (serialState == WAITING_PWM) {
        saisiPwm = constrain(ligne.toInt(), 0, 255);

        Serial.print("-> PWM choisi : ");
        Serial.println(saisiPwm);
        Serial.println("Entrer le sens de rotation (1 pour Horaire, 0 pour Anti-horaire) :");
        serialState = WAITING_DIR;
      } 
      else if (serialState == WAITING_DIR) {
        int sens = ligne.toInt();
        pwmValeur = (sens == 0) ? -saisiPwm : saisiPwm;

        // Applique la nouvelle consigne une seule fois
        commandeVitesse(pwmValeur);

        Serial.print("-> Moteur en marche ! PWM = ");
        Serial.print(saisiPwm);
        Serial.println(pwmValeur >= 0 ? " | Sens : Horaire" : " | Sens : Anti-horaire");
        Serial.println("-----------------------------------------");
        Serial.println("Pour changer, entrer une nouvelle valeur PWM (0-255) :");
        serialState = WAITING_PWM;
      }
    }
  }

  // 2. Lecture atomique des ticks
  noInterrupts();
  bool calculer = mesureDemandee;
  long deltaTicks = 0;
  if (calculer) {
    mesureDemandee = false;
    deltaTicks = ticksCodeur;
    ticksCodeur = 0;
  }
  interrupts();

  // 3. Calcul et affichage (inclut la décélération jusqu'à l'arrêt complet)
  if (calculer && (pwmValeur != 0 || deltaTicks != 0)) {
    float deltaRad = deltaTicks * RAD_PAR_TICK;
    omega = deltaRad / delta_time_s;
    position += deltaRad;

    Serial.print("Position : ");
    Serial.print(position, 2);
    Serial.print(" rad | Omega : ");
    Serial.print(omega, 2);
    Serial.print(" rad/s | Sens reel : ");
    if (deltaTicks > 0) {
      Serial.println("Horaire");
    } else if (deltaTicks < 0) {
      Serial.println("Anti-horaire");
    } else {
      Serial.println("Arret");
    }
  }
}

void commandeVitesse(int pwm_mot) {
  pwm_mot = constrain(pwm_mot, -255, 255);
  if (pwm_mot >= 0) {
    digitalWrite(pinDir, HIGH);
    analogWrite(pinPwm, pwm_mot);
  } else {
    digitalWrite(pinDir, LOW);
    analogWrite(pinPwm, -pwm_mot);
  }
}

void GestionInterruptionCodeurPinA() {
  if (digitalReadFast2(codeurPinA) == digitalReadFast2(codeurPinB)) {
    ticksCodeur++;
  } else {
    ticksCodeur--;
  }
}

void GestionInterruptionCodeurPinB() {
  if (digitalReadFast2(codeurPinA) == digitalReadFast2(codeurPinB)) {
    ticksCodeur--;
  } else {
    ticksCodeur++;
  }
}

void declencherMesure() {
  mesureDemandee = true;
}
